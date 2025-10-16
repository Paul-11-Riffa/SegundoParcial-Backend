# api/views/auth.py
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from ..serializers import UserSerializer, RegisterSerializer

@api_view(['POST'])
@permission_classes([AllowAny])
def register_view(request):
    """Vista de registro"""
    serializer = RegisterSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        token, _ = Token.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'user_id': user.pk,
            'email': user.email,
            'username': user.username
        }, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# segundoparcial-backend/api/views/auth.py

@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """Vista de login mejorada (acepta username o email)"""
    # Aquí definimos la variable 'identifier'
    identifier = request.data.get('username')
    password = request.data.get('password')

    if not identifier or not password:
        return Response(
            {'error': 'Por favor proporciona un usuario/email y contraseña'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # La usamos aquí
    user = authenticate(username=identifier, password=password)

    if user is None:
        try:
            # Y la usamos aquí también
            user_by_email = User.objects.get(email=identifier)
            user = authenticate(username=user_by_email.username, password=password)
        except User.DoesNotExist:
            user = None

    if user:
        token, created = Token.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'user_id': user.pk,
            'email': user.email,
            'username': user.username
        })

    return Response({'error': 'Credenciales inválidas'}, status=status.HTTP_401_UNAUTHORIZED)

class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            request.user.auth_token.delete()
        except (AttributeError, Token.DoesNotExist):
            pass # El usuario ya no tiene token, no hay nada que hacer
        return Response(status=status.HTTP_204_NO_CONTENT)

class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)