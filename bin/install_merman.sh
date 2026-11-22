#!/bin/bash
# Rendu des graphiques Mermaid en image pour les cartes Slack (SLACK_CHART_IMAGES) : merman-cli et la police qu'il
# mesure et peint, posés dans $HOME/.merman. Appelé par bin/post_compile sur Scalingo, à la main en local.
#
# Version et empreintes épinglées : une archive qui n'a pas l'empreinte attendue est refusée, rien n'est installé.
# La police est fournie plutôt que cherchée sur le système, pour un même dessin sur toutes les machines.
set -euo pipefail

VERSION=0.11.0
case "$(uname -s)-$(uname -m)" in
    Linux-x86_64)
        TARGET=x86_64-unknown-linux-gnu
        SHA=cb51eae6818fb1e6f14ef469ea0b2a67b560c345bf3065513d24f640fa3334b2 ;;
    Linux-aarch64)
        TARGET=aarch64-unknown-linux-gnu
        SHA=5bdbdedd91e8aafd4127ea996bccb5d25052e8a49098d8fca903e00f1d60781f ;;
    Darwin-arm64)
        TARGET=aarch64-apple-darwin
        SHA=fb22df8fd8f39431bd217d80d42ad73c5e95190609ecd0a80604b11b195f1701 ;;
    Darwin-x86_64)
        TARGET=x86_64-apple-darwin
        SHA=727519471b409266d76d24fb985b57e31bedebece3ca2185615c212f999d5bcd ;;
    *)
        echo "-----> merman-cli : pas d'archive pour $(uname -s)-$(uname -m)" >&2
        exit 1 ;;
esac
FONTS_SHA=fa9ca4d13871dd122f61258a80d01751d603b4d3ee14095d65453b4e846e17d7

DEST="$HOME/.merman"
if [ "$("$DEST/merman-cli" --version 2>/dev/null)" = "merman-cli $VERSION" ] && [ -f "$DEST/DejaVuSans-Bold.ttf" ]; then
    echo "-----> merman-cli $VERSION already in \$HOME/.merman"
    exit 0
fi

PYTHON=$(command -v python3 || command -v python)
WORK=$(mktemp -d)
trap 'rm -rf "${WORK:?}"' EXIT

# Why: Python vérifie et décompresse, les images de build n'ayant pas toutes xz ni sha256sum.
fetch() {
    curl -fsSL --max-time 180 -o "$WORK/$2" "$1"
    "$PYTHON" - "$WORK/$2" "$3" "$WORK/$2.d" <<'PY'
import hashlib
import sys
import tarfile

archive, expected, target = sys.argv[1:]
if hashlib.sha256(open(archive, "rb").read()).hexdigest() != expected:
    sys.exit(f"-----> {archive} : empreinte inattendue, archive refusée")
tarfile.open(archive).extractall(target, filter="data")
PY
}

echo "-----> Installing merman-cli $VERSION ($TARGET)"
fetch "https://github.com/Latias94/merman/releases/download/v$VERSION/merman-cli-$TARGET.tar.xz" merman.tar.xz "$SHA"
fetch "https://github.com/dejavu-fonts/dejavu-fonts/releases/download/version_2_37/dejavu-fonts-ttf-2.37.tar.bz2" \
    dejavu.tar.bz2 "$FONTS_SHA"

mkdir -p "$DEST"
cp "$WORK/merman.tar.xz.d/merman-cli-$TARGET"/{merman-cli,LICENSE-MIT,LICENSE-APACHE,THIRD_PARTY_NOTICES.md} "$DEST/"
cp "$WORK/dejavu.tar.bz2.d/dejavu-fonts-ttf-2.37/ttf"/{DejaVuSans.ttf,DejaVuSans-Bold.ttf} "$DEST/"
cp "$WORK/dejavu.tar.bz2.d/dejavu-fonts-ttf-2.37/LICENSE" "$DEST/LICENSE-DejaVu"
chmod +x "$DEST/merman-cli"
"$DEST/merman-cli" --version
