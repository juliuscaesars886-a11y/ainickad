#!/usr/bin/env bash
set -o errexit

# Force cache bust - v3
echo "=================================================================="
echo "Starting Ainick Backend Build Process"
echo "=================================================================="

echo ""
echo "[1/4] Upgrading pip..."
pip install --upgrade pip

echo ""
echo "[2/4] Installing Python dependencies..."
pip install -r requirements.txt

echo ""
echo "[3/4] Running database migrations..."
python manage.py migrate --no-input

echo ""
echo "[4/4] Collecting static files..."
python manage.py collectstatic --no-input --clear

echo ""
echo "=================================================================="
echo "Fixing Superuser Password"
echo "=================================================================="

# Run the fix_superuser_password.py script
echo "Running password fix script..."
python fix_superuser_password.py

echo ""
echo "=================================================================="
echo "Build Process Completed!"
echo "=================================================================="
