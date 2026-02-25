"""
Serializers for the Users app.

All serializers use camelCase field names to match the Flutter mobile client.
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for User objects.
    Outputs camelCase field names for Flutter compatibility.
    """
    firstName = serializers.CharField(source='first_name', read_only=True)
    lastName = serializers.CharField(source='last_name', read_only=True)
    avatarUrl = serializers.URLField(source='avatar', read_only=True, allow_null=True)
    preferredCurrency = serializers.CharField(source='preferred_currency', read_only=True)
    isPremium = serializers.BooleanField(source='is_premium', read_only=True)

    class Meta:
        model = User
        fields = [
            'id',
            'email',
            'firstName',
            'lastName',
            'phone',
            'avatarUrl',
            'preferredCurrency',
            'isPremium',
        ]
        read_only_fields = ['id', 'email', 'isPremium']


class UserRegistrationSerializer(serializers.Serializer):
    """
    Serializer for user registration.
    Accepts camelCase from Flutter, auto-generates username from email.
    """
    firstName = serializers.CharField(max_length=150)
    lastName = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(
        write_only=True,
        validators=[validate_password],
        style={'input_type': 'password'},
    )
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True)

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('A user with this email already exists.')
        return value.lower()

    def create(self, validated_data):
        email = validated_data['email']
        # Auto-generate username from email prefix
        base_username = email.split('@')[0][:30]
        username = base_username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f'{base_username}{counter}'
            counter += 1

        user = User(
            email=email,
            username=username,
            first_name=validated_data['firstName'],
            last_name=validated_data['lastName'],
            phone=validated_data.get('phone', ''),
        )
        user.set_password(validated_data['password'])
        user.save()
        return user


class UserUpdateSerializer(serializers.Serializer):
    """
    Serializer for updating user profile.
    Accepts camelCase field names from Flutter.
    """
    firstName = serializers.CharField(max_length=150, required=False)
    lastName = serializers.CharField(max_length=150, required=False)
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    avatarUrl = serializers.URLField(max_length=500, required=False, allow_null=True)
    preferredCurrency = serializers.CharField(max_length=3, required=False)

    def update(self, instance, validated_data):
        if 'firstName' in validated_data:
            instance.first_name = validated_data['firstName']
        if 'lastName' in validated_data:
            instance.last_name = validated_data['lastName']
        if 'phone' in validated_data:
            instance.phone = validated_data['phone']
        if 'avatarUrl' in validated_data:
            instance.avatar = validated_data['avatarUrl']
        if 'preferredCurrency' in validated_data:
            instance.preferred_currency = validated_data['preferredCurrency']
        instance.save()
        return instance


class FirebaseTokenSerializer(serializers.Serializer):
    """
    Serializer for Firebase token exchange.
    """
    firebase_token = serializers.CharField(
        required=True,
        help_text='Firebase ID token to exchange for JWT.',
    )


class ChangePasswordSerializer(serializers.Serializer):
    """
    Serializer for password change.
    """
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(
        required=True,
        validators=[validate_password],
    )

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Old password is incorrect.')
        return value
