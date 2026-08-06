from django.contrib.auth import authenticate, login, logout
from django.middleware.csrf import get_token
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from .models import User

from .api_serializers import UserSerializer, RegisterSerializer
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import send_mail
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def csrf_view(request):
    """
    Visiting this sets the csrftoken cookie in the browser. React must
    call this once (e.g. on app load) before attempting any POST request,
    since DRF's SessionAuthentication enforces CSRF on unsafe methods.
    """
    return Response({'csrfToken': get_token(request)})


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def login_view(request):
    username = request.data.get('username')
    password = request.data.get('password')

    if not username or not password:
        return Response({'detail': 'Username and password are required.'}, status=status.HTTP_400_BAD_REQUEST)

    user = authenticate(request, username=username, password=password)
    if user is None:
        return Response({'detail': 'Invalid username or password.'}, status=status.HTTP_401_UNAUTHORIZED)

    login(request, user)
    return Response(UserSerializer(user).data)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def logout_view(request):
    logout(request)
    return Response({'detail': 'Logged out.'})


@api_view(['GET', 'PATCH'])
@permission_classes([permissions.IsAuthenticated])
def current_user_view(request):
    if request.method == 'PATCH':
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
    return Response(UserSerializer(request.user).data)
@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def register_view(request):
    serializer = RegisterSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.save()

    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    domain = get_current_site(request).domain
    link = f'http://{domain}/accounts/verify/{uid}/{token}/'

    send_mail(
        'Verify your Househunt account',
        f'Hi {user.username}, click the link to verify your account: {link}',
        None,
        [user.email],
    )

    return Response(
        {'detail': 'Registration successful. Check your email to verify your account.'},
        status=status.HTTP_201_CREATED,
    ) 
   

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def google_login_view(request):
    token = request.data.get('credential')
    if not token:
        return Response({'detail': 'Missing credential.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        idinfo = id_token.verify_oauth2_token(
            token, google_requests.Request(), settings.GOOGLE_OAUTH_CLIENT_ID
        )
    except ValueError:
        return Response({'detail': 'Invalid Google token.'}, status=status.HTTP_401_UNAUTHORIZED)

    email = idinfo.get('email')
    if not email:
        return Response({'detail': 'Google account has no email.'}, status=status.HTTP_400_BAD_REQUEST)

    user, created = User.objects.get_or_create(
        email=email,
        defaults={
            'username': email.split('@')[0],
            'is_active': True,
        },
    )
    if created:
        user.set_unusable_password()
        user.save()

    login(request, user)
    return Response(UserSerializer(user).data)
