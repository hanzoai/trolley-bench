#!/bin/sh
# Cloudflare Clef-flash 9B on the v2 grid; see clef_release.sh
exec "$(dirname "$0")/clef_release.sh" clef-flash "$@"
