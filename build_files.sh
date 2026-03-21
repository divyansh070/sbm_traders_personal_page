#!/bin/bash
set -e
echo "BUILD START"

# Vercel's static-build environment doesn't have pip installed by default
echo "Bootstrapping pip..."
curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
python3 get-pip.py --user
export PATH="$HOME/.local/bin:$PATH"

python3 -m pip install -r requirements.txt
mkdir -p staticfiles
python3 manage.py collectstatic --noinput --clear
python3 manage.py migrate --noinput || true

echo "BUILD END"
