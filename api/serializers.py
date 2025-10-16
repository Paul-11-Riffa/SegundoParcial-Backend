# api/serializers.py
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Profile


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ('role',)


class UserSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer()

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'profile')


class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('username', 'password', 'email', 'first_name', 'last_name')
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = User.objects.create_user(
            validated_data['username'],
            validated_data['email'],
            validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', '')
        )
        return user


class AdminUserSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer()
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'is_active', 'password', 'profile')
        # Hacemos que el email sea requerido al crear
        extra_kwargs = {'email': {'required': True}}

    # --- MÉTODO create AÑADIDO ---
    def create(self, validated_data):
        profile_data = validated_data.pop('profile')
        # Usamos create_user para hashear la contraseña correctamente
        user = User.objects.create_user(**validated_data)

        # Asignamos el rol del perfil
        Profile.objects.filter(user=user).update(**profile_data)

        return user

    def update(self, instance, validated_data):
        profile_data = validated_data.pop('profile', None)
        password = validated_data.pop('password', None)

        if profile_data:
            profile_serializer = self.fields['profile']
            profile_instance = instance.profile
            profile_serializer.update(profile_instance, profile_data)

        super().update(instance, validated_data)

        if password:
            instance.set_password(password)
            instance.save()

        return instance