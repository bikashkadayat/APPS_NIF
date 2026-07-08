import secrets
import uuid

from django.contrib.auth import get_user_model
from rest_framework import serializers

from .services import generate_employee_id

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Current-user / general profile serializer (used by /auth/user/)."""
    full_name = serializers.SerializerMethodField()
    department_name = serializers.ReadOnlyField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'employee_id', 'first_name', 'last_name', 'email',
            'role', 'full_name', 'department', 'department_ref', 'department_name',
            'designation', 'phone', 'date_of_joining', 'is_active',
            'must_change_password', 'last_login', 'date_joined', 'profile_photo',
        ]
        read_only_fields = ['id', 'employee_id', 'must_change_password', 'last_login', 'date_joined']

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate(self, attrs):
        if attrs['current_password'] == attrs['new_password']:
            raise serializers.ValidationError({'new_password': 'Must differ from the current password.'})
        return attrs


class AdminUserCreateSerializer(serializers.ModelSerializer):
    # Password is optional; if omitted an initial one is generated and returned.
    password = serializers.CharField(write_only=True, min_length=8, required=False)
    generated_password = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'employee_id', 'email', 'first_name', 'last_name', 'username',
            'password', 'generated_password', 'role', 'department', 'department_ref',
            'designation', 'phone', 'date_of_joining', 'is_active',
        ]
        read_only_fields = ['id', 'employee_id', 'username', 'generated_password']

    def get_generated_password(self, obj):
        # Surfaced once (on create) so the admin can share initial credentials.
        return getattr(obj, '_generated_password', None)

    def create(self, validated_data):
        request = self.context.get('request')
        password = validated_data.pop('password', None) or secrets.token_urlsafe(9)
        email = validated_data['email']
        username = validated_data.get('username') or (email.split('@')[0] + '_' + str(uuid.uuid4())[:6])
        validated_data['username'] = username

        user = User(**validated_data)
        user.employee_id = generate_employee_id()
        user.must_change_password = True  # forced on first login
        if request is not None and getattr(request.user, 'is_authenticated', False):
            user.created_by = request.user
        user.set_password(password)
        user.save()
        user._generated_password = password
        return user
