#!/usr/bin/env bash
# Personal-data scan for the skill folders. Everything under <plugin>/skills reaches everyone who
# installs the plugin, so it scans EVERY file, the eval fixtures (plans and reports) included.
# Check 7 of check-layout.sh looks for e-mails only; this scan also looks for uuids.
#
# Usage: bash <plugin>/skills/mcp-plan/scripts/check-distribution.sh <folder>...
# CI runs it on <plugin>/skills/mcp-plan and <plugin>/skills/mcp-run (test_mcp_skills.py).
# Exit code 1 if anything was found, 2 on a usage error or when fixed-data.md lists no fictional
# value. Prints one line per hit, at most 40 per scan and kind.
#
# Two scans:
# - a pattern scan, case-insensitive:
#   - any e-mail outside the reserved example domains, plain or `%40`-encoded;
#   - any uuid in a fixture position that is not a fictional value: a game id argument or field
#     (`game_id`, `gameId`, `source_game_id`, `targetGameId`, `games: [...]`), a user or player id
#     (`user_id`, `player_id`, `test_player_ids`), a `kinoa-mcp://<kind>/<uuid>` URI, an admin role
#     API position (`scopeId`, `scope_id`, `company_id` and the `users/<uuid>/roles` path), and a
#     §0 fixture line: a table row whose first cell is `P1`/`P2`/`COMPANY`/`PLAYER1`/`PLAYER2`
#     (any text after the handle), a bullet that starts with one, or `<handle> = <uuid>` (the
#     handle itself, not a suffix such as `SEED_P2`);
#   - the same positions inside the base64 payload of every confirm token (`eyJ…`), decoded;
#   The fictional values are read from the "Fictional values" section of
#   <plugin>/skills/mcp-plan/references/fixed-data.md: each uuid written there in full, and each
#   backticked uuid prefix that ends in `…` (a family such as `7d3e1c2…`).
# - an exact scan: every line of the operator's own denylist file ($QA_PERSONAL_DENYLIST, default
#   ~/.config/kinoa-qa/personal-denylist.txt — e-mail, user id, game ids and names, player ids; one
#   value per line, optionally followed by a TAB and text that is ignored),
#   matched case-insensitively, a uuid also without its dashes, in the files and in the decoded
#   tokens. The file lives outside the plugin; without it only the patterns run.
# A uuid is taken from the matched text only, never from the file path.

set -u
[ $# -ge 1 ] || { echo "usage: $0 <folder>..."; exit 2; }
DENYLIST="${QA_PERSONAL_DENYLIST:-$HOME/.config/kinoa-qa/personal-denylist.txt}"
EMAIL='[A-Za-z0-9._%+-]+(@|%40)[A-Za-z0-9-]+\.[A-Za-z0-9.-]*[A-Za-z]{2,}'
UUID='[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}'
# Fictional values, from fixed-data.md: a full uuid matches itself only, a prefix its whole family.
FIXED_DATA="$(cd "$(dirname "$0")/.." && pwd)/references/fixed-data.md"
fictional_section="$(awk '/^## Fictional values/ { f = 1; next } f && /^## / { exit } f' "$FIXED_DATA" 2>/dev/null)"
FICTIONAL="$( {
    printf '%s\n' "$fictional_section" | grep -oE "$UUID" | sed 's/$/$/'
    printf '%s\n' "$fictional_section" | grep -oE '`[0-9a-fA-F-]+…`' | tr -d '`' | sed 's/…$//'
  } | sort -u | paste -sd '|' -)"
[ -n "$FICTIONAL" ] || { echo "PROBLEM: no fictional values in $FIXED_DATA (its ## Fictional values section); nothing scanned"; exit 2; }
FICTIONAL="^($FICTIONAL)"
HANDLE='`?(\*\*)?`?(P[12]|PLAYER[12]|COMPANY)`?(\*\*)?`?'
# Fixture positions. Case-insensitive ones first, then the §0 handle shapes (case-sensitive: `p1`
# in prose is not a handle).
POS_I="\"?(source_?|target_?)?game_?id\"? *[:=] *\"?$UUID|\"?games\"? *: *\[ *\"?$UUID|(user|player)_?ids?[^0-9a-f]{0,12}$UUID|test_player_ids[^0-9a-f]{0,12}$UUID|kinoa-mcp://[a-z-]+/$UUID|\"?(scope_?id|company_?id)\"? *[:=] *\"?$UUID|scope_?id=$UUID|users/$UUID/roles"
POS_H="^ *\| *$HANDLE[^|]*\|.*$UUID|^ *[-*] +$HANDLE.*$UUID|(^|[^A-Za-z0-9_])$HANDLE *= *\`?$UUID"
MAX=40
fail=0
hit() { echo "PERSONAL DATA: $*"; fail=1; }

# Prints the hits it is fed, at most $MAX, then a count of the rest. Every hit sets fail=1.
capped() {  # $1 = message prefix
  local n=0 line
  while IFS= read -r line; do
    n=$((n+1)); fail=1
    [ "$n" -le "$MAX" ] && echo "PERSONAL DATA: $1 $line"
  done
  [ "$n" -gt "$MAX" ] && echo "PERSONAL DATA: $1 … and $((n-MAX)) more"
  return 0
}

# Keeps a `path:line:match` hit only when its match part holds a uuid that is not fictional.
real_uuid_hits() {
  local line m
  while IFS= read -r line; do
    m="${line#*:}"; m="${m#*:}"
    # Every uuid in the match counts: a fictional one next to a real one does not excuse the row.
    echo "$m" | grep -oE "$UUID" | grep -viqE "$FICTIONAL" && echo "$line"
  done
  return 0
}

# Decodes every confirm-token run (`eyJ…`) of the folder: one `path:line<TAB>decoded` per token.
# The filters below look at the decoded part only: the path may hold anything (a user name, a uuid).
decoded_tokens() {  # $1 = folder
  local where tok p
  grep -rnoE 'eyJ[A-Za-z0-9_-]{8,}' "$1" 2>/dev/null | while IFS= read -r where; do
    tok="${where##*:}"; where="${where%:*}"
    p="$(printf '%s' "$tok" | tr '_-' '/+')"
    while [ $(( ${#p} % 4 )) -ne 0 ]; do p="$p="; done
    printf '%s\t%s\n' "$where" "$(printf '%s' "$p" | base64 -d 2>/dev/null | tr -d '\n\r\t' | LC_ALL=C tr -c '[:print:]' '?')"
  done
}
# Keeps the `path:line` of each decoded token whose decoded part matches the grep arguments.
tokens_matching() {  # $1 = decoded tokens, rest = grep options and pattern
  local tokens="$1" where text; shift
  printf '%s\n' "$tokens" | while IFS=$'\t' read -r where text; do
    [ -n "$where" ] && printf '%s\n' "$text" | grep -q "$@" && echo "$where"
  done
  return 0
}
# Keeps the `path:line` of each decoded token that holds a non-fictional uuid in a fixture position.
tokens_with_real_uuid() {  # $1 = decoded tokens
  local where text
  printf '%s\n' "$1" | while IFS=$'\t' read -r where text; do
    [ -n "$where" ] || continue
    printf '%s\n' "$text" | grep -oiE "$POS_I|\"user\" *: *\"$UUID" | grep -oE "$UUID" | grep -viqE "$FICTIONAL" && echo "$where"
  done
  return 0
}

scan() {  # $1 = folder to scan, $2 = label printed in front of each path
  local dir="$1" label="$2" value
  capped "e-mail in" < <(grep -rnoiE "$EMAIL" "$dir" 2>/dev/null | grep -viE '(@|%40)example\.(com|org|net)$' \
    | sed "s#^$dir#$label#")
  capped "uuid in a fixture position in" < <( {
      grep -rnoiE "$POS_I" "$dir" 2>/dev/null
      grep -rnoE "$POS_H" "$dir" 2>/dev/null
    } | real_uuid_hits | sed "s#^$dir#$label#" | sort -u)
  local tokens; tokens="$(decoded_tokens "$dir")"
  capped "uuid in a decoded confirm token in" < <(tokens_with_real_uuid "$tokens" | sed "s#^$dir#$label#" | sort -u)
  if [ -f "$DENYLIST" ]; then
    while IFS= read -r value; do
      value="${value%$'\r'}"
      value="${value%%$'\t'*}"           # a line may carry `<TAB><text>`, which is ignored
      [ -z "$value" ] && continue
      case "$value" in \#*) continue;; esac
      # Print the file and line only: the hit itself is the personal value.
      capped "denylisted value in" < <( {
          grep -rniF -- "$value" "$dir" 2>/dev/null | cut -d: -f1,2
          tokens_matching "$tokens" -iF -- "$value"
          if echo "$value" | grep -qxE "$UUID"; then
            grep -rniF -- "$(echo "$value" | tr -d -)" "$dir" 2>/dev/null | cut -d: -f1,2
          fi
        } | sed "s#^$dir#$label#" | sort -u)
    done < "$DENYLIST"
  fi
}

for target in "$@"; do
  if [ -d "$target" ]; then
    target="${target%/}"
    scan "$target" "$(basename "$target")"
  else
    echo "PROBLEM: $target is not a folder"; fail=1
  fi
done
[ -f "$DENYLIST" ] || echo "NOTE: no denylist at $DENYLIST — exact values not scanned, patterns only"
[ "$fail" = 0 ] && echo "OK: no personal data found in: $*"
exit $fail
