from django.contrib.auth.models import User
from api.models import Profile

user = User.objects.get(username='admin')
profile, created = Profile.objects.get_or_create(user=user)
profile.role = 'ADMIN'
profile.save()
print('\n✅ ¡Perfil ADMIN asignado exitosamente!')
print('='*50)
print(f'   👤 Usuario:    admin')
print(f'   📧 Email:      {user.email}')
print(f'   🎖️  Rol:        {profile.role}')
print('='*50)
print('\n🚀 Ahora puedes iniciar sesión en:')
print('   http://localhost:3000/login')
print('')
