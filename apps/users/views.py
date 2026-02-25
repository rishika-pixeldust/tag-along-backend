"""
Views for the Users app.

All auth responses use camelCase and flat token structure to match Flutter client.
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
from rest_framework_simplejwt.exceptions import TokenError

from apps.users.serializers import (
    ChangePasswordSerializer,
    FirebaseTokenSerializer,
    UserRegistrationSerializer,
    UserSerializer,
    UserUpdateSerializer,
)

logger = logging.getLogger(__name__)
User = get_user_model()


def _build_auth_response(user, refresh_token, http_status=status.HTTP_200_OK):
    """Helper to build a consistent auth response with camelCase tokens."""
    return Response(
        {
            'success': True,
            'user': UserSerializer(user).data,
            'accessToken': str(refresh_token.access_token),
            'refreshToken': str(refresh_token),
        },
        status=http_status,
    )


class RegisterView(APIView):
    """
    Register a new user account.

    POST /api/v1/auth/register/
    Body: {"firstName": "...", "lastName": "...", "email": "...", "password": "..."}
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        refresh = RefreshToken.for_user(user)
        return _build_auth_response(user, refresh, status.HTTP_201_CREATED)


class LoginView(APIView):
    """
    Login with email and password to obtain JWT tokens.

    POST /api/v1/auth/login/
    Body: {"email": "...", "password": "..."}
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
        return _build_auth_response(user, refresh, status.HTTP_200_OK)


class CustomTokenRefreshView(APIView):
    """
    Refresh JWT tokens using camelCase field names for Flutter compatibility.

    POST /api/v1/auth/refresh/
    Body: {"refreshToken": "..."}
    Response: {"accessToken": "...", "refreshToken": "..."}
    """
    permission_classes = [AllowAny]

    def post(self, request):
        refresh_token_str = request.data.get('refreshToken') or request.data.get('refresh')
        if not refresh_token_str:
            return Response(
                {
                    'success': False,
                    'error': {
                        'code': 'validation_error',
                        'message': 'refreshToken is required.',
                    },
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            old_refresh = RefreshToken(refresh_token_str)
            # Get the user for the response
            user_id = old_refresh.payload.get('user_id')
            user = User.objects.get(id=user_id)

            # Create new access token
            access_token = str(old_refresh.access_token)

            # If rotation is enabled, blacklist old and create new refresh
            response_data = {
                'success': True,
                'accessToken': access_token,
                'refreshToken': str(old_refresh),
                'user': UserSerializer(user).data,
            }

            if settings.SIMPLE_JWT.get('ROTATE_REFRESH_TOKENS', False):
                old_refresh.blacklist()
                new_refresh = RefreshToken.for_user(user)
                response_data['accessToken'] = str(new_refresh.access_token)
                response_data['refreshToken'] = str(new_refresh)

            return Response(response_data, status=status.HTTP_200_OK)

        except TokenError:
            return Response(
                {
                    'success': False,
                    'error': {
                        'code': 'token_invalid',
                        'message': 'Token is invalid or expired.',
                    },
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )
        except User.DoesNotExist:
            return Response(
                {
                    'success': False,
                    'error': {
                        'code': 'user_not_found',
                        'message': 'User not found.',
                    },
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )


class UserProfileView(APIView):
    """
    Retrieve or update the authenticated user's profile.

    GET   /api/v1/auth/profile/
    PATCH /api/v1/auth/profile/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response({'success': True, 'data': serializer.data})

    def patch(self, request):
        serializer = UserUpdateSerializer(
            request.user,
            data=request.data,
            partial=True,
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
            import firebase_admin
            from firebase_admin import auth as firebase_auth

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
        http_status = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return _build_auth_response(user, refresh, http_status)


class LogoutView(APIView):
    """
    Logout by blacklisting the refresh token.

    POST /api/v1/auth/logout/
    Body: {"refreshToken": "<refresh_token>"}
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Accept both camelCase and snake_case
        refresh_token = (
            request.data.get('refreshToken')
            or request.data.get('refresh')
        )
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

    POST /api/v1/auth/change-password/
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

    GET /api/v1/auth/search/?q=<query>
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
