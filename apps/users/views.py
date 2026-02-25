"""
Views for the Users app.
"""
import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Q
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.serializers import (
    ChangePasswordSerializer,
    FirebaseTokenSerializer,
    UserRegistrationSerializer,
    UserSerializer,
    UserUpdateSerializer,
)

logger = logging.getLogger(__name__)
User = get_user_model()


class RegisterView(generics.CreateAPIView):
    """
    Register a new user account.

    POST /api/v1/auth/register/
    """
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)

        return Response(
            {
                'success': True,
                'user': UserSerializer(user).data,
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                },
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    """
    Login with email and password to obtain JWT tokens.

    POST /api/v1/auth/login/
    """
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')

        if not email or not password:
            return Response(
                {
                    'success': False,
                    'error': {
                        'code': 'validation_error',
                        'message': 'Both email and password are required.',
                    },
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {
                    'success': False,
                    'error': {
                        'code': 'authentication_failed',
                        'message': 'Invalid email or password.',
                    },
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not user.check_password(password):
            return Response(
                {
                    'success': False,
                    'error': {
                        'code': 'authentication_failed',
                        'message': 'Invalid email or password.',
                    },
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not user.is_active:
            return Response(
                {
                    'success': False,
                    'error': {
                        'code': 'account_disabled',
                        'message': 'This account has been disabled.',
                    },
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        refresh = RefreshToken.for_user(user)
        return Response(
            {
                'success': True,
                'user': UserSerializer(user).data,
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                },
            },
            status=status.HTTP_200_OK,
        )


class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    Retrieve or update the authenticated user's profile.

    GET  /api/v1/users/me/
    PATCH /api/v1/users/me/
    """
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

    def get_serializer_class(self):
        if self.request.method in ('PATCH', 'PUT'):
            return UserUpdateSerializer
        return UserSerializer

    def retrieve(self, request, *args, **kwargs):
        serializer = UserSerializer(request.user)
        return Response({'success': True, 'data': serializer.data})

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', True)
        serializer = UserUpdateSerializer(
            request.user,
            data=request.data,
            partial=partial,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {
                'success': True,
                'data': UserSerializer(request.user).data,
            }
        )


class FirebaseTokenExchangeView(APIView):
    """
    Exchange a Firebase ID token for JWT tokens.

    POST /api/v1/auth/firebase/
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = FirebaseTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        firebase_token = serializer.validated_data['firebase_token']

        try:
            # Verify the Firebase token
            import firebase_admin
            from firebase_admin import auth as firebase_auth

            # Initialize Firebase app if not already initialized
            if not firebase_admin._apps:
                cred_path = settings.FIREBASE_CREDENTIALS_PATH
                if cred_path:
                    cred = firebase_admin.credentials.Certificate(cred_path)
                    firebase_admin.initialize_app(cred)
                else:
                    firebase_admin.initialize_app()

            decoded_token = firebase_auth.verify_id_token(firebase_token)
            firebase_uid = decoded_token['uid']
            email = decoded_token.get('email', '')
            name = decoded_token.get('name', '')

        except Exception as e:
            logger.warning('Firebase token verification failed: %s', str(e))
            return Response(
                {
                    'success': False,
                    'error': {
                        'code': 'firebase_auth_failed',
                        'message': 'Invalid Firebase token.',
                    },
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Get or create user by firebase_uid
        user, created = User.objects.get_or_create(
            firebase_uid=firebase_uid,
            defaults={
                'email': email,
                'username': email.split('@')[0] if email else firebase_uid[:30],
                'first_name': name.split(' ')[0] if name else '',
                'last_name': ' '.join(name.split(' ')[1:]) if name else '',
            },
        )

        if not created and not user.email and email:
            user.email = email
            user.save(update_fields=['email'])

        refresh = RefreshToken.for_user(user)
        return Response(
            {
                'success': True,
                'user': UserSerializer(user).data,
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                },
                'created': created,
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class LogoutView(APIView):
    """
    Logout by blacklisting the refresh token.

    POST /api/v1/auth/logout/
    Body: {"refresh": "<refresh_token>"}
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response(
                {
                    'success': False,
                    'error': {
                        'code': 'validation_error',
                        'message': 'Refresh token is required.',
                    },
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except Exception:
            # Token may already be blacklisted or invalid — still log out
            pass

        return Response(
            {
                'success': True,
                'message': 'Successfully logged out.',
            },
            status=status.HTTP_200_OK,
        )


class ChangePasswordView(APIView):
    """
    Change the authenticated user's password.

    POST /api/v1/users/change-password/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)

        request.user.set_password(serializer.validated_data['new_password'])
        request.user.save()

        return Response(
            {
                'success': True,
                'message': 'Password changed successfully.',
            },
            status=status.HTTP_200_OK,
        )


class UserSearchView(generics.ListAPIView):
    """
    Search for users by email or name.

    GET /api/v1/users/search/?q=<query>
    """
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        query = self.request.query_params.get('q', '').strip()
        if not query or len(query) < 2:
            return User.objects.none()
        return User.objects.filter(
            Q(email__icontains=query)
            | Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(username__icontains=query)
        ).exclude(id=self.request.user.id)[:20]
