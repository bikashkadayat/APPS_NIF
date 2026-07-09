from rest_framework import serializers, status
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.settings import api_settings as jwt_settings
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone

from audit.models import AuditLog
from audit.services import log_action

User = get_user_model()


class SafeTokenRefreshView(TokenRefreshView):
    """
    Token refresh that returns 401 (not 500) when the refresh token references a
    user who no longer exists or has been deactivated.

    Discovered in Phase 1: SimpleJWT looks the user up with an unguarded
    User.objects.get(); a stale token (e.g. after a DB swap, or a deleted user)
    raised an uncaught DoesNotExist -> 500. We pre-validate the token's user so
    the frontend receives a clean 401 and can redirect to login.
    """

    permission_classes = [AllowAny]  # H6: explicitly public (token is the credential)

    def post(self, request, *args, **kwargs):
        refresh = request.data.get("refresh")
        if refresh:
            try:
                token = RefreshToken(refresh)  # verifies signature + expiry
            except TokenError as exc:
                raise InvalidToken(exc.args[0])
            user_id = token.get(jwt_settings.USER_ID_CLAIM)
            user = User.objects.filter(**{jwt_settings.USER_ID_FIELD: user_id}).first()
            if user is None or not user.is_active:
                raise AuthenticationFailed(
                    "Account for this session is no longer valid. Please sign in again.",
                    code="user_invalid",
                )
        try:
            return super().post(request, *args, **kwargs)
        except ObjectDoesNotExist:
            raise AuthenticationFailed("Token user no longer exists.", code="user_not_found")


class EmailLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        if not email or not password:
            raise serializers.ValidationError('Email and password are required.')

        try:
            user = User.objects.select_related('department_ref').get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError('Invalid email or password.')

        if not user.check_password(password):
            raise serializers.ValidationError('Invalid email or password.')

        # is_active is deliberately NOT checked here; the view returns a 403 with
        # a clear message (and audits it) for deactivated accounts.
        attrs['user'] = user
        return attrs


class EmailLoginView(APIView):
    """
    UNIFIED login for all roles (Phase 2.5). Returns JWT tokens plus a `user`
    block (including role + must_change_password) so the frontend can enforce a
    first-login password change and redirect by role. URL is unchanged:
    POST /api/v1/auth/login/
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = EmailLoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.validated_data['user']

        if not user.is_active:
            log_action(None, AuditLog.Action.OTHER, instance=user,
                       changes={'event': 'LOGIN_BLOCKED_INACTIVE'}, request=request)
            return Response(
                {'detail': 'Account is deactivated. Please contact administrator.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        refresh = RefreshToken.for_user(user)

        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])
        log_action(user, AuditLog.Action.LOGIN, instance=user,
                   changes={'event': 'LOGIN_SUCCESS'}, request=request)

        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': {
                'id': str(user.id),
                'employee_id': user.employee_id,
                'full_name': user.full_name,
                'username': user.username,
                'email': user.email,
                'role': user.role,
                'department': user.department_name,
                'designation': user.designation,
                'must_change_password': user.must_change_password,
                'profile_photo': user.profile_photo.url if user.profile_photo else None,
            },
        })
