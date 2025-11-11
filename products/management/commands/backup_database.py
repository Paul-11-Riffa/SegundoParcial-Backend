"""
Comando para hacer backup de la base de datos antes de realizar cambios.
Funciona con PostgreSQL y SQLite.
"""
from django.core.management.base import BaseCommand
from django.conf import settings
import os
import subprocess
from datetime import datetime
from decouple import config


class Command(BaseCommand):
    help = 'Crea una copia de seguridad de la base de datos'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('\n' + '='*70))
        self.stdout.write(self.style.WARNING('💾 BACKUP DE BASE DE DATOS'))
        self.stdout.write(self.style.WARNING('='*70 + '\n'))

        db_settings = settings.DATABASES['default']
        db_engine = db_settings['ENGINE']

        # Crear timestamp para el backup
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        if 'postgresql' in db_engine:
            # Backup de PostgreSQL
            self.stdout.write('📊 Base de datos: PostgreSQL\n')
            
            db_name = config('DB_NAME')
            db_user = config('DB_USER')
            db_password = config('DB_PASSWORD')
            db_host = config('DB_HOST', default='localhost')
            db_port = config('DB_PORT', default='5432')
            
            backup_file = f'backup_postgres_{timestamp}.sql'
            
            try:
                self.stdout.write(f'📁 Creando backup: {backup_file}...')
                
                # Configurar variable de entorno para la contraseña
                env = os.environ.copy()
                env['PGPASSWORD'] = db_password
                
                # Ejecutar pg_dump
                cmd = [
                    'pg_dump',
                    '-h', db_host,
                    '-p', db_port,
                    '-U', db_user,
                    '-F', 'c',  # Formato custom (comprimido)
                    '-f', backup_file,
                    db_name
                ]
                
                result = subprocess.run(cmd, env=env, capture_output=True, text=True)
                
                if result.returncode == 0:
                    file_size = os.path.getsize(backup_file) / (1024 * 1024)  # MB
                    self.stdout.write(self.style.SUCCESS(f'\n✅ Backup creado exitosamente!'))
                    self.stdout.write(f'   Archivo: {backup_file}')
                    self.stdout.write(f'   Tamaño: {file_size:.2f} MB')
                    
                    self.stdout.write(self.style.SUCCESS('\n💡 Para restaurar el backup:'))
                    self.stdout.write(f'   pg_restore -h {db_host} -p {db_port} -U {db_user} -d {db_name} -c {backup_file}')
                    self.stdout.write('\n')
                else:
                    self.stdout.write(self.style.WARNING('\n⚠️  pg_dump no disponible o error al crear backup'))
                    self.stdout.write(self.style.WARNING('   Continuando sin backup...'))
                    self.stdout.write(self.style.WARNING('   NOTA: Los datos se eliminarán con transacciones (se puede revertir si hay error)\n'))

            except FileNotFoundError:
                self.stdout.write(self.style.WARNING('\n⚠️  pg_dump no encontrado en el sistema'))
                self.stdout.write(self.style.WARNING('   Para hacer backup manual, consulta a tu DBA'))
                self.stdout.write(self.style.WARNING('   Continuando sin backup...\n'))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'\n⚠️  No se pudo crear backup: {str(e)}'))
                self.stdout.write(self.style.WARNING('   Continuando sin backup...\n'))

        elif 'sqlite' in db_engine:
            # Backup de SQLite
            import shutil
            
            db_file = db_settings['NAME']
            
            if not os.path.exists(db_file):
                self.stdout.write(self.style.ERROR(f'❌ No se encontró el archivo {db_file}'))
                return

            backup_file = f'{db_file}.backup_{timestamp}'

            try:
                self.stdout.write(f'📁 Creando backup: {backup_file}...')
                shutil.copy2(db_file, backup_file)
                
                original_size = os.path.getsize(db_file) / (1024 * 1024)  # MB
                backup_size = os.path.getsize(backup_file) / (1024 * 1024)  # MB
                
                self.stdout.write(self.style.SUCCESS(f'\n✅ Backup creado exitosamente!'))
                self.stdout.write(f'   Archivo original: {db_file} ({original_size:.2f} MB)')
                self.stdout.write(f'   Backup: {backup_file} ({backup_size:.2f} MB)')
                
                self.stdout.write(self.style.SUCCESS('\n💡 Para restaurar el backup:'))
                self.stdout.write(f'   copy {backup_file} {db_file}')
                self.stdout.write('\n')

            except Exception as e:
                self.stdout.write(self.style.ERROR(f'\n❌ Error al crear backup: {str(e)}'))
                raise
        
        else:
            self.stdout.write(self.style.WARNING('\n⚠️  Motor de base de datos no soportado para backup automático'))
            self.stdout.write(self.style.WARNING('   Por favor, realiza el backup manualmente'))
            self.stdout.write(self.style.WARNING('   Continuando sin backup...\n'))
