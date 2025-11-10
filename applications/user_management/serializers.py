from rest_framework import serializers


# Request Serializers
class LoginRequestSerializer(serializers.Serializer):
    # Legacy - kept for compatibility, not used in Mongo login
    username = serializers.CharField(required=True)
    password = serializers.CharField(write_only=True, required=True)


class RegisterRequestSerializer(serializers.Serializer):
    # Legacy - kept for compatibility, not used in Mongo register
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=6)
    confirm_password = serializers.CharField(write_only=True)
    first_name = serializers.CharField(max_length=30)
    last_name = serializers.CharField(max_length=30)
    role = serializers.ChoiceField(choices=[('admin','admin'),('teacher','teacher'),('student','student')])
    phone = serializers.CharField(max_length=15, required=False, allow_blank=True)

    def validate(self, attrs):
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError('Mật khẩu xác nhận không khớp')
        return attrs


class ChangePasswordRequestSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=6)
    confirm_new_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_new_password']:
            raise serializers.ValidationError('Mật khẩu mới xác nhận không khớp')
        return attrs


# Response Serializers
class UserResponseSerializer(serializers.Serializer):
    id = serializers.CharField()
    username = serializers.CharField(allow_blank=True, required=False)
    email = serializers.EmailField(allow_blank=True, required=False)
    first_name = serializers.CharField(allow_blank=True, required=False)
    last_name = serializers.CharField(allow_blank=True, required=False)
    full_name = serializers.CharField(allow_blank=True, required=False)
    role = serializers.CharField()
    phone = serializers.CharField(allow_blank=True, required=False)
    is_active = serializers.BooleanField(required=False)
    created_at = serializers.CharField(allow_blank=True, required=False)


class LoginResponseSerializer(serializers.Serializer):
    access_token = serializers.CharField()
    refresh_token = serializers.CharField()
    user = UserResponseSerializer()


class RegisterResponseSerializer(serializers.Serializer):
    access_token = serializers.CharField()
    refresh_token = serializers.CharField()
    user = UserResponseSerializer()


class ChangePasswordResponseSerializer(serializers.Serializer):
    message = serializers.CharField() 