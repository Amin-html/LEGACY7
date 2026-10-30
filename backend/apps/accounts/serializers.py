from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .services import send_verification_email

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True, min_length=8, style={"input_type": "password"}
    )
    role = serializers.ChoiceField(
        choices=[(r.value, r.label) for r in User.SELF_ASSIGNABLE_ROLES],
        default=User.Role.PARTICIPANT,
    )

    class Meta:
        model = User
        fields = ("id", "email", "username", "password", "role")
        read_only_fields = ("id",)
        extra_kwargs = {"email": {"validators": []}}

    def validate_email(self, value):
        value = value.lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Пользователь с таким email уже существует.")
        return value

    def validate(self, attrs):
        user = User(email=attrs.get("email"), username=attrs.get("username"))
        validate_password(attrs["password"], user=user)
        return attrs

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        send_verification_email(user)
        return user


class UserSerializer(serializers.ModelSerializer):
    bio = serializers.CharField(source="profile.bio", required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ("id", "email", "username", "role", "is_email_verified", "avatar", "bio")
        read_only_fields = ("id", "email", "role", "is_email_verified", "avatar")

    def update(self, instance, validated_data):
        profile_data = validated_data.pop("profile", {})
        instance = super().update(instance, validated_data)
        if "bio" in profile_data:
            instance.profile.bio = profile_data["bio"]
            instance.profile.save(update_fields=["bio"])
        return instance