"""
Comando Django para migrar imágenes legacy (campo 'image' único)
al nuevo sistema de múltiples imágenes (modelo ProductImage).

Uso:
    python manage.py migrate_legacy_images

Opciones:
    --dry-run: Simular sin hacer cambios reales
    --force: Migrar incluso si el producto ya tiene imágenes nuevas
"""

from django.core.management.base import BaseCommand
from products.models import Product, ProductImage
import os


class Command(BaseCommand):
    help = 'Migra imágenes legacy (campo image) al sistema de múltiples imágenes'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simular migración sin hacer cambios',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Forzar migración incluso si ya tiene imágenes nuevas',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        force = options['force']

        self.stdout.write('=' * 70)
        self.stdout.write(self.style.SUCCESS('MIGRACION DE IMAGENES LEGACY'))
        self.stdout.write('=' * 70)

        if dry_run:
            self.stdout.write(self.style.WARNING('MODO DRY-RUN: No se harán cambios reales'))

        # Buscar productos con imagen legacy
        products_with_legacy = Product.objects.exclude(image='').exclude(image=None)
        total = products_with_legacy.count()

        self.stdout.write(f'\nProductos con imagen legacy: {total}\n')

        if total == 0:
            self.stdout.write(self.style.WARNING('No hay imágenes legacy para migrar'))
            return

        migrated = 0
        skipped = 0
        errors = 0

        for product in products_with_legacy:
            # Verificar si ya tiene imágenes en el nuevo sistema
            has_new_images = product.images.exists()

            if has_new_images and not force:
                self.stdout.write(
                    self.style.WARNING(
                        f'[SKIP] [{product.id}] {product.name} - OMITIDO (ya tiene imagenes nuevas)'
                    )
                )
                skipped += 1
                continue

            # Verificar que el archivo de imagen existe físicamente
            try:
                if not os.path.isfile(product.image.path):
                    self.stdout.write(
                        self.style.ERROR(
                            f'[ERROR] [{product.id}] {product.name} - Archivo no existe: {product.image.path}'
                        )
                    )
                    errors += 1
                    continue
            except (ValueError, AttributeError) as e:
                self.stdout.write(
                    self.style.ERROR(
                        f'[ERROR] [{product.id}] {product.name} - Error al verificar archivo: {e}'
                    )
                )
                errors += 1
                continue

            # Migrar imagen
            if not dry_run:
                try:
                    ProductImage.objects.create(
                        product=product,
                        image=product.image.name,  # Reusar el mismo archivo
                        order=0,
                        is_primary=True,
                        alt_text=f'{product.name} - Imagen principal'
                    )

                    self.stdout.write(
                        self.style.SUCCESS(
                            f'[OK] [{product.id}] {product.name} - Migrado: {product.image.name}'
                        )
                    )
                    migrated += 1

                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(
                            f'[ERROR] [{product.id}] {product.name} - Error al migrar: {e}'
                        )
                    )
                    errors += 1
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'[OK] [{product.id}] {product.name} - Se migraria: {product.image.name}'
                    )
                )
                migrated += 1

        # Resumen
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write(self.style.SUCCESS('RESUMEN DE MIGRACION'))
        self.stdout.write('=' * 70)
        self.stdout.write(f'Total de productos con imagen legacy: {total}')
        self.stdout.write(self.style.SUCCESS(f'[OK] Migrados: {migrated}'))
        self.stdout.write(self.style.WARNING(f'[SKIP] Omitidos: {skipped}'))
        self.stdout.write(self.style.ERROR(f'[ERROR] Errores: {errors}'))

        if dry_run:
            self.stdout.write('\n' + self.style.WARNING('Ejecuta sin --dry-run para aplicar los cambios'))
        else:
            self.stdout.write('\n' + self.style.SUCCESS('Migracion completada!'))

        self.stdout.write('=' * 70)
