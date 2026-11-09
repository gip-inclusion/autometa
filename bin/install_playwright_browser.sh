#!/bin/bash
# Navigateur du skill verify_dashboard sur Scalingo, appelé par bin/post_compile.
#
# Scalingo déploie par buildpacks : la ligne `playwright install` du Dockerfile n'y tourne jamais.
# Les bibliothèques système de Chromium viennent de l'Aptfile (apt-buildpack, cf. .buildpacks) :
# `--with-deps` exige apt en root, indisponible pendant le build.
#
# $HOME est le dossier de build, qui devient /app à l'exécution ; .profile.d/ est sourcé au démarrage.
set -euo pipefail

export PLAYWRIGHT_BROWSERS_PATH="$HOME/.playwright"
BROWSERS_CACHE="${CACHE_DIR:+$CACHE_DIR/playwright}"

if [ -n "$BROWSERS_CACHE" ] && [ -d "$BROWSERS_CACHE" ]; then
    echo "-----> Using cached Playwright browsers"
    cp -r "$BROWSERS_CACHE" "$PLAYWRIGHT_BROWSERS_PATH"
fi

echo "-----> Installing Playwright Chromium headless shell"
python -m playwright install --only-shell chromium

if [ -n "$BROWSERS_CACHE" ]; then
    rm -rf "$BROWSERS_CACHE"
    cp -r "$PLAYWRIGHT_BROWSERS_PATH" "$BROWSERS_CACHE"
fi

mkdir -p "$HOME/.profile.d"
echo 'export PLAYWRIGHT_BROWSERS_PATH="$HOME/.playwright"' > "$HOME/.profile.d/playwright.sh"
echo "-----> Playwright browsers in \$HOME/.playwright"
