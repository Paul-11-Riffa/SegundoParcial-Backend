#!/usr/bin/env bash
# exit on error
set -o errexit

# Instalar dependencias
pip install --upgrade pip
pip install -r requirements.txt

# Ejecutar migraciones
python manage.py migrate --no-input

# Recolectar archivos estáticos
python manage.py collectstatic --no-input --clear
