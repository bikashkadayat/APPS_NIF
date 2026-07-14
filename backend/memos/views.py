from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle


class MemoDirectoryThrottle(UserRateThrottle):
    """Per-user scoped rate limit for the assignee-directory search (H5)."""
    scope = "memo_directory"

from audit.models import AuditLog
from users.models import User
from users.permissions import IsCheckerOrApprover
from . import services
from .models import Memo, MemoTemplate
from .sanitizers import sanitize_memo_html
from .permissions import (
    SENSITIVE_MEMO_TYPES,
    CanViewMemo,
    IsMemoApprover,
    IsMemoChecker,
)
from .serializers import (
    MemoActionSerializer,
    MemoAssigneeSerializer,
    MemoCreateSerializer,
    MemoDetailSerializer,
    MemoListSerializer,
    MemoTemplateSerializer,
)

# Assignee directory: require a search term and cap results so the endpoint
# cannot be used to enumerate the whole staff roster (H5).
DIRECTORY_MIN_QUERY = 2
DIRECTORY_LIMIT = 20


class MemoViewSet(viewsets.ModelViewSet):
    """
    Memo CRUD plus workflow action endpoints. All state transitions are
    delegated to memos.services so this class stays thin.
    """
    permission_classes = [IsAuthenticated, CanViewMemo]

    def get_queryset(self):
        user = self.request.user
        qs = Memo.objects.select_related(
            "created_by", "current_reviewer", "current_approver"
        ).prefetch_related("approval_steps__actor")

        if user.role == User.Roles.ADMIN:
            return qs

        if user.role == User.Roles.MAKER:
            return qs.filter(created_by=user)

        if user.role == User.Roles.CHECKER:
            base = Q(created_by=user) | Q(current_reviewer=user)
            return qs.filter(
                base | self._pool_q(
                    user, [Memo.Status.SUBMITTED, Memo.Status.UNDER_REVIEW])
            ).distinct()

        if user.role == User.Roles.APPROVER:
            base = Q(created_by=user) | Q(current_approver=user)
            return qs.filter(
                base | self._pool_q(user, [
                    Memo.Status.UNDER_REVIEW,
                    Memo.Status.APPROVED,
                    Memo.Status.REJECTED,
                ])
            ).distinct()

        return qs.none()

    @staticmethod
    def _pool_q(user, statuses):
        """
        Same-department, non-sensitive pool for a checker/approver (M1). If the
        user has no department, the pool is empty (returns a never-match Q) so
        null departments do not collapse into "see everything".
        """
        if not getattr(user, "department", None):
            return Q(pk__in=[])
        return (
            Q(status__in=statuses)
            & Q(created_by__department=user.department)
            & ~Q(memo_type__in=SENSITIVE_MEMO_TYPES)
        )

    def get_serializer_class(self):
        if self.action == "list":
            return MemoListSerializer
        if self.action == "create":
            return MemoCreateSerializer
        return MemoDetailSerializer

    def perform_create(self, serializer):
        # Employee / Department Head / HR may create memos. Admin is an
        # oversight/approval role and does not author personal memo requests.
        user = self.request.user
        if user.role == User.Roles.ADMIN:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Admins oversee and approve memos; they do not create memo requests.")
        # H2: memo_number is assigned by Memo.save() via the single canonical
        # generator; do not mint it here (that was a second, divergent path).
        memo = serializer.save(
            created_by=user,
            status=Memo.Status.DRAFT,
        )
        services.create_audit_log(
            user, AuditLog.Action.CREATE, instance=memo, request=self.request
        )

    @action(detail=False, methods=["post"], url_path="create-and-submit",
            permission_classes=[IsAuthenticated])
    def create_and_submit(self, request):
        """
        Create a memo and submit it for review in one atomic step (M2). If the
        submit fails (e.g. no active checker, invalid override), the whole thing
        rolls back so no orphaned draft is left behind.
        """
        from django.db import transaction

        if request.user.role == User.Roles.ADMIN:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Admins oversee and approve memos; they do not create memo requests.")

        serializer = MemoCreateSerializer(data=request.data, context=self.get_serializer_context())
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            memo = serializer.save(created_by=request.user, status=Memo.Status.DRAFT)
            services.create_audit_log(
                request.user, AuditLog.Action.CREATE, instance=memo, request=request)
            memo = services.submit_memo(
                memo, request.user,
                override_reviewer_id=request.data.get("override_reviewer_id"),
                request=request,
            )
        return Response(
            MemoDetailSerializer(memo, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED,
        )

    def _detail_response(self, memo):
        serializer = MemoDetailSerializer(memo, context=self.get_serializer_context())
        return Response(serializer.data)

    def _action_comment(self, request):
        serializer = MemoActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data.get("comment", "")

    @action(detail=True, methods=["post"], url_path="submit",
            permission_classes=[IsAuthenticated])
    def submit(self, request, pk=None):
        # Any authenticated author may submit their own memo (the service
        # enforces created_by == actor); optional override_reviewer_id lets the
        # author pick a specific checker, else it auto-resolves by department.
        memo = self.get_object()
        result = services.submit_memo(
            memo, request.user,
            override_reviewer_id=request.data.get("override_reviewer_id"),
            request=request,
        )
        return self._detail_response(result)

    @action(detail=True, methods=["post"], url_path="review",
            permission_classes=[IsAuthenticated, IsMemoChecker])
    def review(self, request, pk=None):
        comment = self._action_comment(request)
        memo = self.get_object()
        result = services.review_memo(
            memo, request.user, comment,
            override_approver_id=request.data.get("override_approver_id"),
            request=request,
        )
        return self._detail_response(result)

    @action(detail=True, methods=["post"], url_path="approve",
            permission_classes=[IsAuthenticated, IsMemoApprover])
    def approve(self, request, pk=None):
        comment = self._action_comment(request)
        memo = self.get_object()
        result = services.approve_memo(memo, request.user, comment, request=request)
        return self._detail_response(result)

    @action(detail=True, methods=["post"], url_path="reject",
            permission_classes=[IsAuthenticated, IsCheckerOrApprover])
    def reject(self, request, pk=None):
        comment = self._action_comment(request)
        memo = self.get_object()
        result = services.reject_memo(memo, request.user, comment, request=request)
        return self._detail_response(result)

    @action(detail=True, methods=["post"], url_path="return",
            permission_classes=[IsAuthenticated, IsMemoChecker])
    def return_to_maker(self, request, pk=None):
        comment = self._action_comment(request)
        memo = self.get_object()
        result = services.return_memo(memo, request.user, comment, request=request)
        return self._detail_response(result)

    @action(detail=True, methods=["post"], url_path="cancel",
            permission_classes=[IsAuthenticated])
    def cancel(self, request, pk=None):
        # Author-only (enforced by the service); any role may cancel own draft.
        comment = self._action_comment(request)
        memo = self.get_object()
        result = services.cancel_memo(memo, request.user, comment, request=request)
        return self._detail_response(result)

    def _directory(self, request, roles):
        """
        Search-gated, capped assignee lookup (H5). Returns [] until at least
        DIRECTORY_MIN_QUERY chars are supplied, matches on name/username only
        (never email), and returns at most DIRECTORY_LIMIT rows. `roles` is the
        set of memo-approval-eligible roles to include.
        """
        query = (request.query_params.get("search") or "").strip()
        if len(query) < DIRECTORY_MIN_QUERY:
            return Response([])
        qs = (
            User.objects.filter(role__in=roles, is_active=True)
            .filter(
                Q(first_name__icontains=query)
                | Q(last_name__icontains=query)
                | Q(username__icontains=query)
            )
            .order_by("first_name", "username")[:DIRECTORY_LIMIT]
        )
        return Response(MemoAssigneeSerializer(qs, many=True).data)

    @action(detail=False, methods=["get"], url_path="available-checkers",
            permission_classes=[IsAuthenticated], throttle_classes=[MemoDirectoryThrottle])
    def available_checkers(self, request):
        """Memo-approval-eligible reviewers for the maker's 'assign checker'
        dropdown: Department Head, HR, and Admin (active). HR + Admin are org-wide
        approvers, so they appear even when the maker's department has no Dept Head."""
        return self._directory(request, [User.Roles.CHECKER, User.Roles.APPROVER, User.Roles.ADMIN])

    @action(detail=False, methods=["get"], url_path="available-approvers",
            permission_classes=[IsAuthenticated], throttle_classes=[MemoDirectoryThrottle])
    def available_approvers(self, request):
        """Final approvers for the checker's 'assign approver' dropdown: HR + Admin."""
        return self._directory(request, [User.Roles.APPROVER, User.Roles.ADMIN])

    @action(detail=True, methods=["get"], url_path="attachment")
    def attachment(self, request, pk=None):
        """
        Stream the memo's attachment behind authorization.

        get_object() runs CanViewMemo, so only users entitled to the memo can
        download its file (closes the unauthenticated-media hole). The file is
        always served as an attachment (never inline) so an uploaded
        HTML/SVG cannot execute in the app origin.
        """
        from django.http import FileResponse, Http404

        memo = self.get_object()
        if not memo.attachment:
            raise Http404("This memo has no attachment.")
        response = FileResponse(
            memo.attachment.open("rb"),
            as_attachment=True,
            filename=memo.attachment.name.rsplit("/", 1)[-1],
            # Force a generic type so the browser never renders an uploaded
            # HTML/SVG inline in the app origin; nosniff blocks type-guessing.
            content_type="application/octet-stream",
        )
        response["X-Content-Type-Options"] = "nosniff"
        return response

    @action(detail=True, methods=["get"], url_path="pdf")
    def pdf(self, request, pk=None):
        """Approved-memo PDF with letterhead, approval trail and verification QR."""
        from django.http import HttpResponse
        from django.utils.html import linebreaks
        from documents.models import IssuedDocument
        from documents.pdf import common_context, render_pdf
        from documents.services import issue_document

        memo = self.get_object()
        if memo.status != Memo.Status.APPROVED:
            return Response({"detail": "PDF is available only for approved memos."},
                            status=status.HTTP_409_CONFLICT)

        steps = list(memo.approval_steps.select_related("actor").all())
        approver = memo.current_approver
        author = memo.created_by

        def _name(u):
            return (u.get_full_name() or u.username) if u else "—"

        doc = issue_document(
            IssuedDocument.DocType.MEMO, "memo", memo, subject=memo.subject,
            issued_by=request.user, actors=[_name(s.actor) for s in steps if s.actor],
        )
        ctx = common_context(doc.document_number)
        ctx.update({
            "memo": memo,
            "to_name": _name(approver),
            "from_name": _name(author),
            "cc_name": "",
            # Defense in depth: body is sanitized on write, but re-sanitize
            # right before rendering untrusted HTML into the PDF.
            "body_html": linebreaks(sanitize_memo_html(memo.body)),
            "approver_name": _name(approver),
            "steps": [{
                "step_order": s.step_order,
                "get_action_display": s.get_action_display(),
                "actor_name": _name(s.actor),
                "acted_at": s.acted_at,
                "comment": s.comment,
            } for s in steps],
        })
        pdf_bytes = render_pdf("pdf/memo.html", ctx)
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{doc.document_number}.pdf"'
        return response


class MemoTemplateViewSet(viewsets.ModelViewSet):
    """
    Memo templates. Any authenticated user may read active templates to prefill
    a new memo; create/update/delete are admin-only (L1).
    """
    serializer_class = MemoTemplateSerializer

    def get_permissions(self):
        from users.admin_views import IsAdminOrSuperuser
        if self.action in ("list", "retrieve"):
            return [IsAuthenticated()]
        return [IsAdminOrSuperuser()]

    def get_queryset(self):
        # Admins manage all templates (incl. inactive); everyone else sees only
        # active ones for the prefill dropdown.
        user = self.request.user
        if getattr(user, "role", None) == User.Roles.ADMIN or user.is_staff or user.is_superuser:
            return MemoTemplate.objects.all()
        return MemoTemplate.objects.filter(is_active=True)
