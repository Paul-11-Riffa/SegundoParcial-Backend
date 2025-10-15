# api/views/users.py
from rest_framework import generics, status
from rest_framework.response import Response
from django.contrib.auth.models import User
from ..serializers import AdminUserSerializer
from ..permissions import IsAdminUser

class UserListView(generics.ListAPIView):
    """
    Vista para listar todos los usuarios.
    Solo accesible por administradores.
    """
    queryset = User.objects.all()
    serializer_class = AdminUserSerializer
    permission_classes = [IsAdminUser]

class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Vista para ver, actualizar y eliminar un usuario específico.
    Solo accesible por administradores.
    """
    queryset = User.objects.all()
    serializer_class = AdminUserSerializer
    permission_classes = [IsAdminUser]

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        # Evitar que un admin se elimine a sí mismo
        if instance == request.user:
            return Response({"error": "No puedes eliminar tu propia cuenta de administrador."}, status=status.HTTP_400_BAD_REQUEST)
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)