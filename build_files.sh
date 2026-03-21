#!/bin/bash
set -e
echo "BUILD START"

pip3 install -r requirements.txt
mkdir -p staticfiles
python3 manage.py collectstatic --noinput --clear
python3 manage.py migrate --noinput || true

echo "BUILD END"
