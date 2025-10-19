from django.contrib.auth.models import User
from api.models import Profile

# Mostrar todos los usuarios admin
print('\n📋 Usuarios encontrados:')
print('='*60)
users = User.objects.filter(username__icontains='admin') | User.objects.filter(email__icontains='admin')
for i, u in enumerate(users, 1):
    profile_info = f"Perfil: {u.profile.role}" if hasattr(u, 'profile') else "Sin perfil"
    print(f'{i}. Username: {u.username}, Email: {u.email}, {profile_info}')
print('='*60)

# Eliminar usuarios duplicados, dejar solo el último con perfil ADMIN
if users.count() > 1:
    print('\n🔧 Limpiando usuarios duplicados...')
    
    # Buscar el usuario con perfil ADMIN
    admin_user = None
    for u in users:
        if hasattr(u, 'profile') and u.profile.role == 'ADMIN':
            admin_user = u
            break
    
    # Si no hay usuario con perfil ADMIN, usar el último
    if not admin_user:
        admin_user = users.last()
        profile, created = Profile.objects.get_or_create(user=admin_user)
        profile.role = 'ADMIN'
        profile.save()
    
    # Eliminar los demás
    for u in users:
        if u.id != admin_user.id:
            print(f'   🗑️  Eliminando usuario duplicado: {u.username} ({u.email})')
            u.delete()
    
    print('\n✅ ¡Limpieza completada!')
    print('='*60)
    print(f'   👤 Usuario único:    {admin_user.username}')
    print(f'   📧 Email:            {admin_user.email}')
    print(f'   🎖️  Rol:              {admin_user.profile.role}')
    print('='*60)
else:
    print('\n✅ Solo hay un usuario admin, todo está correcto.')
    user = users.first()
    if not hasattr(user, 'profile'):
        Profile.objects.create(user=user, role='ADMIN')
        print('   ✅ Perfil ADMIN creado')
    elif user.profile.role != 'ADMIN':
        user.profile.role = 'ADMIN'
        user.profile.save()
        print('   ✅ Usuario actualizado a ADMIN')

print('\n🚀 Ahora puedes iniciar sesión en:')
print('   http://localhost:3000/login')
print('   Username: admin')
print('   Password: admin123 (o la que configuraste)')
print('')
