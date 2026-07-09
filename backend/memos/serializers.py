from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Memo, MemoApprovalStep, MemoTemplate
from .sanitizers import sanitize_memo_html

User = get_user_model()

# Attachment upload constraints (kept here so serializers stay the single source
# of truth for what the API will accept).
MAX_ATTACHMENT_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_ATTACHMENT_EXTENSIONS = {"pdf", "docx", "xlsx", "png", "jpg", "jpeg"}


class UserMiniSerializer(serializers.ModelSerializer):
    """
    Lightweight user representation embedded inside memo payloads so clients
    do not have to make a second round trip to resolve names/roles.
    """
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "full_name", "email", "role", "department"]

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username


class MemoApprovalStepSerializer(serializers.ModelSerializer):
    """Read-only history entry for one action in the memo workflow."""
    actor = UserMiniSerializer(read_only=True)

    class Meta:
        model = MemoApprovalStep
        fields = ["id", "step_order", "actor", "action", "comment", "acted_at"]
        read_only_fields = fields


class MemoListSerializer(serializers.ModelSerializer):
    """Slim serializer for list endpoints - deliberately omits body/attachment."""
    created_by = UserMiniSerializer(read_only=True)
    current_reviewer = UserMiniSerializer(read_only=True)
    current_approver = UserMiniSerializer(read_only=True)

    class Meta:
        model = Memo
        fields = [
            "id", "memo_number", "title", "memo_type", "priority", "status",
            "created_by", "current_reviewer", "current_approver",
            "created_at", "submitted_at",
        ]
        read_only_fields = fields


class MemoDetailSerializer(serializers.ModelSerializer):
    """Full memo payload including workflow history and per-user capabilities."""
    created_by = UserMiniSerializer(read_only=True)
    current_reviewer = UserMiniSerializer(read_only=True)
    current_approver = UserMiniSerializer(read_only=True)
    approval_steps = MemoApprovalStepSerializer(many=True, read_only=True)
    attachment_url = serializers.SerializerMethodField()

    can_edit = serializers.SerializerMethodField()
    can_submit = serializers.SerializerMethodField()
    can_review = serializers.SerializerMethodField()
    can_approve = serializers.SerializerMethodField()
    can_reject = serializers.SerializerMethodField()

    class Meta:
        model = Memo
        fields = [
            "id", "memo_number", "title", "subject", "body",
            "memo_type", "priority", "status",
            "created_by", "current_reviewer", "current_approver",
            "attachment_url",
            "created_at", "updated_at", "submitted_at", "finalized_at",
            "approval_steps",
            "can_edit", "can_submit", "can_review", "can_approve", "can_reject",
        ]
        read_only_fields = fields

    def _request_user(self):
        request = self.context.get("request")
        if request is None or not getattr(request, "user", None):
            return None
        user = request.user
        return user if getattr(user, "is_authenticated", False) else None

    def get_attachment_url(self, obj):
        # Never expose the raw MEDIA path. Point at the authenticated download
        # endpoint, which enforces CanViewMemo and forces a download (C2).
        if not obj.attachment:
            return None
        path = f"/api/v1/memos/{obj.id}/attachment/"
        request = self.context.get("request")
        return request.build_absolute_uri(path) if request is not None else path

    def _is_admin(self, user):
        return user is not None and user.role == User.Roles.ADMIN

    def get_can_edit(self, obj):
        user = self._request_user()
        if user is None:
            return False
        if self._is_admin(user):
            return obj.status == Memo.Status.DRAFT
        return obj.created_by_id == user.id and obj.status == Memo.Status.DRAFT

    def get_can_submit(self, obj):
        user = self._request_user()
        if user is None:
            return False
        if self._is_admin(user):
            return obj.status == Memo.Status.DRAFT
        return obj.created_by_id == user.id and obj.status == Memo.Status.DRAFT

    def get_can_review(self, obj):
        user = self._request_user()
        if user is None:
            return False
        if obj.status != Memo.Status.SUBMITTED:
            return False
        return self._is_admin(user) or obj.current_reviewer_id == user.id

    def get_can_approve(self, obj):
        user = self._request_user()
        if user is None:
            return False
        if obj.status != Memo.Status.UNDER_REVIEW:
            return False
        return self._is_admin(user) or obj.current_approver_id == user.id

    def get_can_reject(self, obj):
        user = self._request_user()
        if user is None:
            return False
        if obj.status == Memo.Status.SUBMITTED:
            return self._is_admin(user) or obj.current_reviewer_id == user.id
        if obj.status == Memo.Status.UNDER_REVIEW:
            return self._is_admin(user) or obj.current_approver_id == user.id
        return False


class MemoCreateSerializer(serializers.ModelSerializer):
    """
    Write serializer used to create a draft memo (any authenticated user).

    created_by / status / memo_number are injected by the view layer
    (thin-serializer, fat-service convention) - see MemoViewSet.perform_create.
    id / memo_number / status are returned read-only so the client can navigate
    to the new memo and show its number after creation.
    """
    class Meta:
        model = Memo
        fields = ["id", "memo_number", "status", "title", "subject", "body",
                  "memo_type", "priority", "attachment"]
        read_only_fields = ["id", "memo_number", "status"]
        # Accept the upload but never echo the raw MEDIA path back (C2/L4);
        # clients read the gated attachment_url from the detail endpoint.
        extra_kwargs = {"attachment": {"write_only": True}}

    def validate_body(self, value):
        # Sanitize the rich-text HTML on write: the body is authored by any
        # authenticated user and later rendered to reviewers/approvers/admins
        # and into the PDF, so it is untrusted input (stored-XSS surface).
        return sanitize_memo_html(value)

    def validate_attachment(self, value):
        if value is None:
            return value
        if value.size > MAX_ATTACHMENT_SIZE:
            raise serializers.ValidationError(
                f"Attachment exceeds the {MAX_ATTACHMENT_SIZE // (1024 * 1024)}MB limit."
            )
        name = getattr(value, "name", "") or ""
        ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
        if ext not in ALLOWED_ATTACHMENT_EXTENSIONS:
            allowed = ", ".join(sorted(ALLOWED_ATTACHMENT_EXTENSIONS))
            raise serializers.ValidationError(
                f"Unsupported file type '.{ext}'. Allowed types: {allowed}."
            )
        return value


class MemoActionSerializer(serializers.Serializer):
    """
    Validates the body of workflow action endpoints
    (review / approve / reject / return).

    A comment of at least 10 characters is mandatory for reject and return so
    the person receiving the memo back always has an actionable reason.
    """
    COMMENT_REQUIRED_ACTIONS = {
        MemoApprovalStep.Action.REJECTED,
        MemoApprovalStep.Action.RETURNED,
    }
    MIN_COMMENT_LENGTH = 10

    action = serializers.ChoiceField(
        choices=MemoApprovalStep.Action.choices, required=False
    )
    comment = serializers.CharField(required=False, allow_blank=True, default="")

    def validate(self, attrs):
        action = attrs.get("action")
        comment = (attrs.get("comment") or "").strip()
        if action in self.COMMENT_REQUIRED_ACTIONS and len(comment) < self.MIN_COMMENT_LENGTH:
            raise serializers.ValidationError(
                {"comment": f"A comment of at least {self.MIN_COMMENT_LENGTH} characters is required for this action."}
            )
        return attrs


class MemoTemplateSerializer(serializers.ModelSerializer):
    """CRUD serializer for admin-editable memo templates."""
    class Meta:
        model = MemoTemplate
        fields = [
            "id", "name", "memo_type", "subject_template", "body_template",
            "is_active", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
