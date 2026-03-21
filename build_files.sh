#!/bin/bash
set -e
echo "BUILD START"

# Create a virtual environment to bypass PEP 668 externally-managed errors
python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
mkdir -p staticfiles
python manage.py collectstatic --noinput --clear
python manage.py migrate --noinput || true

echo "BUILD END"
