from io import BytesIO

from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from django.core.files.base import ContentFile
from django.utils import timezone

from audit.models import AuditLog
from audit.services import log_action
from .serializers import UserSerializer, ChangePasswordSerializer, SelfProfileSerializer
from .models import User

# Registration removed in Phase 2.5. Users are created by Admin via
# User Management (POST /api/v1/users/admin/users/).


class CurrentUserView(generics.RetrieveAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class ChangePasswordView(APIView):
    """First-login (and general) password change. Clears must_change_password."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        if not user.check_password(serializer.validated_data["current_password"]):
            raise ValidationError({"current_password": "Incorrect."})

        user.set_password(serializer.validated_data["new_password"])
        user.must_change_password = False
        user.last_password_change = timezone.now()
        user.save(update_fields=["password", "must_change_password", "last_password_change"])

        log_action(user, AuditLog.Action.UPDATE, instance=user,
                   changes={"event": "PASSWORD_CHANGED"}, request=request)
        return Response({"detail": "Password changed successfully."})


class ProfileMeView(APIView):
    """
    GET   /api/v1/profile/me/  - the caller's own full profile.
    PATCH /api/v1/profile/me/  - edit own editable fields ONLY (self-scoped).

    Always operates on request.user; there is no user_id override, and the write
    goes through SelfProfileSerializer, whose field list is the allowlist — so a
    payload carrying role/department/email/etc. cannot change protected fields.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user, context={'request': request}).data)

    def patch(self, request):
        serializer = SelfProfileSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        log_action(request.user, AuditLog.Action.UPDATE, instance=request.user,
                   changes={'event': 'PROFILE_UPDATED', 'fields': sorted(serializer.validated_data.keys())},
                   request=request)
        return Response(UserSerializer(request.user, context={'request': request}).data)


class ProfilePhotoView(APIView):
    """
    POST   /api/v1/profile/me/photo/  (multipart 'photo') - upload/replace.
    DELETE /api/v1/profile/me/photo/                      - remove.

    Validates type (jpeg/png/webp) + size (<=2 MB), then centre-crops to a square
    and resizes to 256x256 (stored as JPEG). Self-only.
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    MAX_BYTES = 2 * 1024 * 1024
    ALLOWED_TYPES = {'image/jpeg', 'image/png', 'image/webp'}

    def post(self, request):
        upload = request.FILES.get('photo')
        if upload is None:
            return Response({'detail': 'No photo file provided (field "photo").'},
                            status=status.HTTP_400_BAD_REQUEST)
        if (upload.content_type or '') not in self.ALLOWED_TYPES:
            return Response({'detail': 'Unsupported image type. Use JPG, PNG or WEBP.'},
                            status=status.HTTP_400_BAD_REQUEST)
        if upload.size > self.MAX_BYTES:
            return Response({'detail': 'Image too large (max 2 MB).'},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            from PIL import Image, ImageOps
            img = Image.open(upload)
            img = ImageOps.exif_transpose(img).convert('RGB')
            w, h = img.size
            side = min(w, h)
            left, top = (w - side) // 2, (h - side) // 2
            img = img.crop((left, top, left + side, top + side)).resize((256, 256), Image.LANCZOS)
        except Exception:
            return Response({'detail': 'Invalid or corrupt image file.'},
                            status=status.HTTP_400_BAD_REQUEST)

        buffer = BytesIO()
        img.save(buffer, format='JPEG', quality=85)
        user = request.user
        if user.profile_photo:
            user.profile_photo.delete(save=False)  # avoid orphaned old file
        user.profile_photo.save(f'user_{user.id}.jpg', ContentFile(buffer.getvalue()), save=True)
        log_action(user, AuditLog.Action.UPDATE, instance=user,
                   changes={'event': 'PROFILE_PHOTO_UPDATED'}, request=request)
        return Response(UserSerializer(user, context={'request': request}).data)

    def delete(self, request):
        user = request.user
        if user.profile_photo:
            user.profile_photo.delete(save=True)
            log_action(user, AuditLog.Action.UPDATE, instance=user,
                       changes={'event': 'PROFILE_PHOTO_REMOVED'}, request=request)
        return Response(UserSerializer(user, context={'request': request}).data)


class UserListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        users = User.objects.filter(is_active=True)
        user_list = []
        for user in users:
            user_list.append({
                'id': str(user.id),
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'role': user.role,
            })
        return Response(user_list)
