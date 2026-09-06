#!/usr/bin/env bash
# Build the tode Linux bundle with PyInstaller and tar it.
#
#   bash packaging/build_linux.sh
#
# Output: dist/tode/  (one-dir bundle) and dist/tode-linux-x86_64.tar.gz
set -euo pipefail

cd "$(dirname "$0")/.."

python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller

rm -rf build dist
pyinstaller packaging/tode.spec --noconfirm

cd dist
tar -czf tode-linux-x86_64.tar.gz tode
echo "Built: dist/tode-linux-x86_64.tar.gz"
