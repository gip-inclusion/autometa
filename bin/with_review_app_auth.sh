#!/usr/bin/env bash
# Second mode d'entrée du proxy, sur les seules review apps : un secret technique connu du seul
# runner de CI, qui laisse passer un navigateur piloté — lequel n'a pas de compte Google. Un
# visiteur humain n'a toujours que l'écran de connexion.
# Voir docs/paved-road/l3-e2e.md § « Accès aux review apps ».
set -euo pipefail

if [ "${AUTOMETA_ENV:-}" = "review" ] && [ -n "${REVIEW_APP_HTPASSWD:-}" ]; then
    htpasswd_file="$(mktemp "${TMPDIR:-/tmp}/review_app_htpasswd.XXXXXX")"
    chmod 600 "$htpasswd_file"
    printf '%s\n' "$REVIEW_APP_HTPASSWD" > "$htpasswd_file"
    export OAUTH2_PROXY_HTPASSWD_FILE="$htpasswd_file"
fi

exec "$@"
