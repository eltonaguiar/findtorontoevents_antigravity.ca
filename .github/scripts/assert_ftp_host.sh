#!/usr/bin/env bash
# assert_ftp_host.sh — guard against root-relative FTP writes landing on the wrong host.
#
# Background (2026-04-17): a workflow uploaded `/audit/` and `/audit_dashboard/` to
# ftps2.50webs.com FTP root because a "GoDaddy-only" deploy step trusted the
# `FTPGODADDYHOST_TE_DOTNET` secret name implicitly. The 50webs FTP server hosts
# multiple sites by directory prefix (`/findtorontoevents.ca/`, `/tdotevent.ca/`,
# `/ejaguiar1.50webs.com/`); writing to root corrupts the layout.
#
# Usage in a workflow step:
#   - name: Refuse-if-50webs guard
#     run: bash .github/scripts/assert_ftp_host.sh "$FTP_SERVER" reject 50webs
#
#   - name: Require-godaddy guard
#     run: bash .github/scripts/assert_ftp_host.sh "$FTP_SERVER" require torontoevent.net
#
# Modes:
#   reject <substring>  — fail if host CONTAINS substring
#   require <substring> — fail if host does NOT contain substring
set -euo pipefail

HOST="${1:-}"
MODE="${2:-}"
NEEDLE="${3:-}"

if [ -z "$HOST" ] || [ -z "$MODE" ] || [ -z "$NEEDLE" ]; then
  echo "ERROR(assert_ftp_host): usage: $0 <host> <reject|require> <substring>" >&2
  exit 2
fi

case "$MODE" in
  reject)
    case "$HOST" in
      *"$NEEDLE"*)
        echo "ERROR(assert_ftp_host): host '$HOST' contains forbidden substring '$NEEDLE' — refusing root-relative deploy." >&2
        exit 1
        ;;
    esac
    ;;
  require)
    case "$HOST" in
      *"$NEEDLE"*) ;;
      *)
        echo "ERROR(assert_ftp_host): host '$HOST' does NOT contain required substring '$NEEDLE' — refusing deploy." >&2
        exit 1
        ;;
    esac
    ;;
  *)
    echo "ERROR(assert_ftp_host): unknown mode '$MODE' (must be reject|require)" >&2
    exit 2
    ;;
esac
echo "OK(assert_ftp_host): host '$HOST' satisfies $MODE='$NEEDLE'"
