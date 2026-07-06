#!/usr/bin/env bash
set -euo pipefail

APP_NAME="py-rizmi"
VERSION="1.0.0"

if command -v nuitka &>/dev/null; then
  NUITKA=nuitka
else
  NUITKA="uv run nuitka"
fi

echo "==> Building $APP_NAME $VERSION with Nuitka ..."

# --standalone : creates a folder with the executable + all deps
# --onefile    : creates a single executable (experimental, larger)
# Pick ONE mode below.

MODE="${1:-standalone}"  # pass "onefile" as first arg to switch

case "$MODE" in
  standalone)
    echo "    Mode: standalone (dist/$APP_NAME/)"
    $NUITKA --standalone \
      --enable-plugin=pyqt6 \
      --include-data-dir=media=media \
      --include-data-file=README.md=README.md \
      --output-dir=dist \
      --product-name="$APP_NAME" \
      --file-version="$VERSION" \
      --product-version="$VERSION" \
      --file-description="Offline RSA-signed license management" \
      --copyright="MIT" \
      main.py
    # Rename output folder
    mv dist/main.dist "dist/$APP_NAME"
    mv dist/main.build "dist/${APP_NAME}.build" 2>/dev/null || true
    echo "==> Done! Executable at dist/$APP_NAME/main"
    ;;
  onefile)
    echo "    Mode: onefile (dist/$APP_NAME)"
    $NUITKA --onefile \
      --enable-plugin=pyqt6 \
      --include-data-dir=media=media \
      --include-data-file=README.md=README.md \
      --output-dir=dist \
      --product-name="$APP_NAME" \
      --file-version="$VERSION" \
      --product-version="$VERSION" \
      --file-description="Offline RSA-signed license management" \
      --copyright="MIT" \
      main.py
    mv dist/main "dist/$APP_NAME" 2>/dev/null || true
    echo "==> Done! Executable at dist/$APP_NAME"
    ;;
  *)
    echo "Usage: $0 [standalone|onefile]"
    exit 1
    ;;
esac
