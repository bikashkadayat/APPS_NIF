from rest_framework import generics
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from django.utils import timezone

from audit.models import AuditLog
from audit.services import log_action
from .serializers import UserSerializer, ChangePasswordSerializer
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
