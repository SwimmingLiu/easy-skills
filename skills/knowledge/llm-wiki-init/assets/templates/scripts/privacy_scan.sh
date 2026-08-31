#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "$0")" && pwd)"
vault_root="$(cd "$script_dir/.." && pwd)"
findings=0

printf 'Privacy scan: %s\n' "$vault_root"

check_content_dir() {
  content_dir="$1"
  [ -d "$vault_root/$content_dir" ] || return 0
  unexpected="$(find "$vault_root/$content_dir" -type f ! -name '.gitkeep' ! -name 'README.md' -print)"
  if [ -n "$unexpected" ]; then
    printf '\n[REVIEW] Non-placeholder files in %s/:\n%s\n' "$content_dir" "$unexpected"
    findings=$((findings + 1))
  fi
}

check_content_dir raw
check_content_dir outputs
check_content_dir assets

allowed_wiki_pattern='^(wiki/index\.md|wiki/overview\.md|wiki/log\.md|wiki/(sources|topics|entities|analyses|decisions)/(README\.md|\.gitkeep)|wiki/indexes/(raw-status|wiki-catalog|tag-index|output-status)\.md)$'
unexpected_wiki="$(find "$vault_root/wiki" -type f -print | sed "s#^$vault_root/##" | rg -v "$allowed_wiki_pattern" || true)"
if [ -n "$unexpected_wiki" ]; then
  printf '\n[REVIEW] Wiki contains non-template pages:\n%s\n' "$unexpected_wiki"
  findings=$((findings + 1))
fi

secret_files="$(find "$vault_root" -path "$vault_root/.git" -prune -o -type f \( -name '.env' -o -name '.env.*' -o -name '*.pem' -o -name '*.key' -o -name '*.p12' -o -name '*.pfx' -o -iname 'cookies*.txt' \) -print)"
if [ -n "$secret_files" ]; then
  printf '\n[BLOCK] Secret-like files found:\n%s\n' "$secret_files"
  findings=$((findings + 1))
fi

sensitive_pattern='(/Users/[^/[:space:]]+/|/home/[^/[:space:]]+/|-----BEGIN [A-Z ]*PRIVATE KEY-----|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}|(api[_-]?key|access[_-]?token|refresh[_-]?token|client[_-]?secret|password)[[:space:]]*[:=][[:space:]]*[^[:space:]]+)'
scan_output="$(rg -n -i --hidden -g '!.git/**' -g '!**/privacy_scan.sh' -g '!*.png' -g '!*.jpg' -g '!*.jpeg' -g '!*.webp' -g '!*.gif' -g '!*.pdf' -g '!*.mp3' -g '!*.m4a' -g '!*.wav' -g '!*.mp4' "$sensitive_pattern" "$vault_root" || true)"
if [ -n "$scan_output" ]; then
  printf '\n[BLOCK] Possible personal path, email, private key, or inline secret:\n%s\n' "$scan_output"
  findings=$((findings + 1))
fi

if [ -n "${PRIVACY_EXTRA_PATTERN:-}" ]; then
  extra_output="$(rg -n -i --hidden -g '!.git/**' -g '!**/privacy_scan.sh' "$PRIVACY_EXTRA_PATTERN" "$vault_root" || true)"
  if [ -n "$extra_output" ]; then
    printf '\n[BLOCK] Matches for PRIVACY_EXTRA_PATTERN:\n%s\n' "$extra_output"
    findings=$((findings + 1))
  fi
fi

if [ "$findings" -ne 0 ]; then
  printf '\nPrivacy scan needs review: findings=%s\n' "$findings"
  exit 1
fi

printf 'Privacy scan passed: no obvious private content or secret files found.\n'
