"""
Script para crear un usuario administrador en SmartSales365
EJECUTAR CON: python manage.py shell < create_admin.py
"""

from django.contrib.auth.models import User
from accounts.models import Profile

# Datos del administrador
admin_data = {
    'username': 'admin',
    'email': 'admin@smartsales365.com',
    'password': 'admin123',
    'first_name': 'Admin',
    'last_name': 'SmartSales365'
}

# Verificar si el usuario ya existe
if User.objects.filter(username=admin_data['username']).exists():
    print(f"\n❌ El usuario '{admin_data['username']}' ya existe.")
    user = User.objects.get(username=admin_data['username'])
    print(f"   Username: {user.username}")
    print(f"   Email: {user.email}")
    if hasattr(user, 'profile'):
        print(f"   Rol: {user.profile.role}")
        # Actualizar a ADMIN si no lo es
        if user.profile.role != 'ADMIN':
            user.profile.role = 'ADMIN'
            user.profile.save()
            print(f"   ✅ Usuario actualizado a ADMIN")
    else:
        print("   ⚠️  Sin perfil - creando...")
        profile = Profile.objects.create(user=user, role='ADMIN')
        print(f"   ✅ Perfil ADMIN creado")
else:
    # Crear el usuario
    user = User.objects.create_user(
        username=admin_data['username'],
        email=admin_data['email'],
        password=admin_data['password'],
        first_name=admin_data['first_name'],
        last_name=admin_data['last_name']
    )
    
    # Crear el perfil como ADMIN
    profile = Profile.objects.create(user=user, role='ADMIN')
    
    print("\n✅ ¡Usuario administrador creado exitosamente!")
    print("\n" + "="*50)
    print("   CREDENCIALES DE ADMINISTRADOR")
    print("="*50)
    print(f"   👤 Usuario:    {admin_data['username']}")
    print(f"   📧 Email:      {admin_data['email']}")
    print(f"   🔑 Contraseña: {admin_data['password']}")
    print(f"   🎖️  Rol:        ADMIN")
    print("="*50)

print("\n🚀 Ahora puedes iniciar sesión en:")
print("   http://localhost:3000/login")
print("\n💡 Tendrás acceso a:")
print("   ✓ Gestión de Usuarios")
print("   ✓ Gestión de Productos")
print("   ✓ Historial de Ventas")
print("   ✓ Reportes Dinámicos")
print("   ✓ Panel de Administrador")
print("")
