#!/bin/bash
set -e
echo "BUILD START"

python3.9 -m pip install -r requirements.txt
mkdir -p staticfiles
python3.9 manage.py collectstatic --noinput --clear
python3.9 manage.py migrate --noinput || true

echo "BUILD END"
