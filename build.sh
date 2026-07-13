#!/usr/bin/env bash
set -euo pipefail

APP_NAME="py-rizmi"
VERSION="1.0.0"

if command -v nuitka >/dev/null 2>&1; then
    NUITKA="nuitka"
else
    NUITKA="uv run nuitka"
fi

echo "==> Building $APP_NAME $VERSION with Nuitka ..."

MODE="${1:-standalone}"

case "$MODE" in
    standalone)
        echo "    Mode: standalone (dist/$APP_NAME/)"

        rm -rf dist/main.dist dist/main.build "dist/$APP_NAME" \
               "dist/${APP_NAME}.build" 2>/dev/null || true

        $NUITKA \
            --standalone \
            --enable-plugin=pyqt6 \
            --include-package=py_rizmi \
            --include-package=pygments \
            --include-data-dir=media=media \
            --include-data-file=README.md=README.md \
            --output-dir=dist \
            --product-name="$APP_NAME" \
            --file-version="$VERSION" \
            --product-version="$VERSION" \
            --file-description="Offline RSA-signed license management" \
            --copyright="MIT" \
            main.py

        mv dist/main.dist "dist/$APP_NAME"

        if [ -d dist/main.build ]; then
            mv dist/main.build "dist/${APP_NAME}.build"
        fi

        echo "==> Done!"
        echo "    Executable: dist/$APP_NAME/main.bin"
        ;;

    onefile)
        echo "    Mode: onefile (dist/$APP_NAME)"

        rm -f "dist/$APP_NAME" dist/main.bin dist/main 2>/dev/null || true

        $NUITKA \
            --onefile \
            --enable-plugin=pyqt6 \
            --include-package=py_rizmi \
            --include-package=pygments \
            --include-data-dir=media=media \
            --include-data-file=README.md=README.md \
            --output-dir=dist \
            --product-name="$APP_NAME" \
            --file-version="$VERSION" \
            --product-version="$VERSION" \
            --file-description="Offline RSA-signed license management" \
            --copyright="MIT" \
            main.py

        if [ -f dist/main.bin ]; then
            mv dist/main.bin "dist/$APP_NAME"
        elif [ -f dist/main ]; then
            mv dist/main "dist/$APP_NAME"
        fi

        echo "==> Done!"
        echo "    Executable: dist/$APP_NAME"
        ;;

    *)
        echo "Usage: $0 [standalone|onefile]"
        exit 1
        ;;
esac