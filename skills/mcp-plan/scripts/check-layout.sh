#!/usr/bin/env bash
# Mechanical checks for the mcp-plan / mcp-run skills and their data folder.
# Run from anywhere: bash <plugin>/skills/mcp-plan/scripts/check-layout.sh [<data folder>]
#                or: bash <plugin>/skills/mcp-plan/scripts/check-layout.sh status <report file>
#                or: bash <plugin>/skills/mcp-plan/scripts/check-layout.sh grades <report file> [<previous report file>]
# (<plugin>/skills = the folder holding both skill folders; the script locates them from its own path.)
# <data folder> holds plans/ and reports/ and defaults to ~/.kinoa-qa/mcp; CI passes the eval
# fixture tree, <plugin>/skills/mcp-run/evals.
# Exit code 1 if any check fails, 2 on a usage error. Prints one line per problem.
# `status <report file>` is not a check: it reads one report and prints its counts, last row, the plan
# cases with no row, the highest finding and note ids and the recorded handles (S. status mode below);
# it exits 0, or 2 when the report is missing or unreadable.
# `grades <report file> [<previous report file>]` is not a check either: it lists the case rows of one
# report that a check agent re-grades (G. grades mode below); it exits 0, or 2 on a usage error.

set -u
usage() { echo "usage: bash check-layout.sh [<data folder>] | bash check-layout.sh status <report file> | bash check-layout.sh grades <report file> [<previous report file>]"; exit 2; }
# Every table row is split on `|` through these two: hold_pipes turns each escaped `\|` into the
# byte $PIPE_HOLD so it stays inside its cell, give_pipes turns it back on the way out.
# Usage: hold_pipes [<file>] | awk -F'|' '…' | give_pipes
PIPE_HOLD="$(printf '\037')"
hold_pipes() { sed "s/\\\\|/$PIPE_HOLD/g" "$@"; }
give_pipes() { sed "s/$PIPE_HOLD/\\\\|/g"; }
# The case status table of section 3, one line per row: <id> TAB <status> TAB <third cell>, with the
# row cells split with escaped `\|` held back (a `\|` in any cell would shift the split; only these
# three cells are read, and a `\|` is given back in the third cell). A fenced block counts for none of it.
case_rows() {  # $1 = report
  hold_pipes "$1" | awk -F'|' '
    /^[ \t]*```/ { f = !f; next }
    f { next }
    /^## / { s = ($0 ~ /^## 3\./); t = 0; next }
    s && /^\| *Case *\| *Status *\|/ { t = 1; next }
    s && t && /^\|[-: |]*\|$/ { next }
    s && t && /^\|/ { id = $2; st = $3; gsub(/[ `]/, "", id); gsub(/[ `]/, "", st); print id "\t" st "\t" $4; next }
    t { t = 0; s = 0 }' | give_pipes
}
# S. status mode: `status <report file>` reads one report and prints, in this order and nothing else:
#    `PASS <n> · FAIL <n> · OBSERVED <n> · BLOCKED <n> · rows <n> of <N>` (the counts of the section 3
#    case status table, N = the case rows of the plan, `?` when the plan is not found), `last row: <id>`,
#    `no row: <plan case ids with no table row, in plan order>`, `highest finding: F<n>`,
#    `highest note: N<n>` (`none` where there is no such row, id or heading), then one `record: …` line
#    per `Record:` handle of section 3, with its line number in the file. The plan is the
#    `*-test-plan*.md` named on the first `Plan file:` line of section 1, at `<report folder>/../plans/`.
#    A fenced block counts for none of it. A pause or a run in progress still prints everything it has.
status_mode() {  # $1 = report
  local rep="$1" rows plan_name plan_path ids_plan ids_rep missing total hf hn
  rows="$(case_rows "$rep" | cut -f1,2)"
  plan_name="$(awk '/^## 1\./ { f = 1; next } f && /^## / { exit } f && /Plan file:/ { print; exit }' "$rep" \
    | grep -oE '[A-Za-z0-9._-]*-test-plan[A-Za-z0-9._-]*\.md' | head -1)"
  plan_path="$(dirname "$rep")/../plans/$plan_name"
  ids_rep="$(printf '%s\n' "$rows" | awk -F'\t' 'NF { print $1 }')"
  if [ -n "$plan_name" ] && [ -f "$plan_path" ]; then
    ids_plan="$(grep -oE '^\| `[a-z0-9-]+` \|' "$plan_path" | tr -d '|` ')"
    missing="$(awk 'NR == FNR { seen[$0]; next } NF && !($0 in seen) { printf "%s%s", (m++ ? " " : ""), $0 }' \
      <(printf '%s\n' "$ids_rep") <(printf '%s\n' "$ids_plan"))"
    total="$(printf '%s\n' "$ids_plan" | awk 'NF { n++ } END { print n + 0 }')"
    [ -n "$missing" ] || missing="none"
  else
    total="?"
    if [ -n "$plan_name" ]; then missing="? (plan not found: $plan_path)"; else missing="? (plan not found: no *-test-plan*.md on the Plan file: line of section 1)"; fi
  fi
  printf '%s\n' "$rows" | awk -F'\t' -v total="$total" '
    NF { n++; c[$2]++; last = $1 }
    END { printf "PASS %d \302\267 FAIL %d \302\267 OBSERVED %d \302\267 BLOCKED %d \302\267 rows %d of %s\n", c["PASS"], c["FAIL"], c["OBSERVED"], c["BLOCKED"], n, total
          print "last row: " (n ? last : "none") }' | give_pipes
  echo "no row: $missing"
  # The block headings outside a fenced block: an example block quoted in a fence holds no id.
  block_ids() {  # $1 = F or N
    awk -v k="$1" '/^[ \t]*```/ { f = !f; next } !f && $0 ~ ("^### " k "[0-9]+ ") { s = $2; sub(/^[FN]/, "", s); print s }' "$rep" \
      | sort -n | tail -1
  }
  hf="$(block_ids F)"
  hn="$(block_ids N)"
  echo "highest finding: ${hf:+F}${hf:-none}"
  echo "highest note: ${hn:+N}${hn:-none}"
  # The Record: lines, section 3 only. The text is matched as a line, not split on `|`, so a value that
  # holds `\|` prints whole. A value is the backticked text after `=`, or, with no backticks, the text up
  # to the end of the sentence (never cut at a space).
  perl -CSD -ne '
    if (/^\s*```/) { $fence = !$fence; next }
    next if $fence;
    if (/^## /) { $in = /^## 3\./; next }
    next unless $in;
    while (/`?Record:\s+([A-Z][A-Z0-9_]*)`?\s*(?:=\s*(`[^`]*`|.+?(?=\.(?:\s|$)|\s*`?Record:|$))|(not recorded))/g) {
      my ($h, $v, $n) = ($1, $2, $3);
      if (defined $v) { $v =~ s/[\s.,;:]+$// unless $v =~ /^`/; print "record: $h = $v (line $.)\n" }
      else { print "record: $h not recorded (line $.)\n" }
    }' "$rep"
}
# G. grades mode: `grades <report> [<previous report>]` prints, in the report's case status table order,
#    one line per targeted row, `<case id> <STATUS>`, with ` was <PREVIOUS STATUS>` appended when the
#    status differs from the previous report's row of that case (matched by case id, not row order) and
#    ` new` appended when a previous report is given and has no row for the case; then the last line,
#    `targeted <n> of <m>` (m = the rows of the report's case status table). A targeted row is any row
#    graded FAIL, OBSERVED or BLOCKED, plus any row whose status differs from the previous report's; a
#    PASS row with no previous row is not targeted. A row whose third cell holds `excluded by the
#    operator` or `writes disabled server-side (dry-run)` (the fixed BLOCKED labels of mcp-plan
#    references/rules.md and stand-facts.md) is never targeted, even when it differs. A previous
#    row whose third cell holds one of them counts as no previous row: a case the previous run did
#    not send is not targeted when it is now PASS, and is ` new` when it is not. Exit 0; 2 on a
#    usage error (the argument count is not 2 or 3, a file is missing or unreadable, an argument starts
#    with `-`). The reader is case_rows, so a `\|` in a cell keeps its row whole.
grades_mode() {  # $1 = report, $2 = previous report or empty
  # The previous stream opens with a `#` line, so that awk's first input is never empty.
  awk -F'\t' -v has_prev="$([ -n "${2:-}" ] && echo 1 || echo 0)" '
    function fixed(c) { return index(c, "excluded by the operator") || index(c, "writes disabled server-side (dry-run)") }
    NR == FNR { if ($1 != "#" && !fixed($3)) prev[$1] = $2; next }
    { m++ }
    fixed($3) { next }
    {
      id = $1; st = $2
      if (id in prev) { if (prev[id] != st) { out = id " " st " was " prev[id] } else if (st != "PASS") { out = id " " st } else { next } }
      else if (st != "PASS") { out = id " " st (has_prev == 1 ? " new" : "") }
      else { next }
      print out; n++
    }
    END { print "targeted " n + 0 " of " m + 0 }' \
    <(printf '#\t#\t#\n'; if [ -n "${2:-}" ]; then case_rows "$2"; fi) <(case_rows "$1")
}
if [ "${1:-}" = grades ]; then
  { [ $# -eq 2 ] || [ $# -eq 3 ]; } || usage
  for a in "${@:2}"; do
    case "$a" in -*) usage;; esac
    { [ -f "$a" ] && [ -r "$a" ]; } || usage
  done
  grades_mode "$2" "${3:-}"; exit 0
fi
if [ "${1:-}" = status ]; then
  { [ $# -eq 2 ] && [ -f "$2" ] && [ -r "$2" ]; } || usage
  status_mode "$2"; exit 0
fi
[ $# -le 1 ] || usage
case "${1:-}" in -*) usage;; esac

PLAN="$(cd "$(dirname "$0")/.." && pwd)"          # mcp-plan
ROOT="$(dirname "$PLAN")"                          # <plugin>/skills: the folder holding the skill folders
EXEC="$ROOT/mcp-run"
DATA="${1:-$HOME/.kinoa-qa/mcp}"; DATA="${DATA%/}"
PLANS="$DATA/plans"
REPORTS="$DATA/reports"
[ -d "$EXEC" ] || { echo "PROBLEM: mcp-run is not installed next to mcp-plan ($ROOT)"; exit 1; }
[ -d "$DATA" ] || { echo "PROBLEM: no data folder at $DATA (run: mkdir -p $DATA/plans $DATA/reports)"; exit 1; }
fail=0
problem() { echo "PROBLEM: $*"; fail=1; }
# A plan follows the current layout when at least one case row carries a stable id
# (<tool>-<kind>-NN, e.g. `update-ok-01`). Legacy plans use A5-K2 style ids (section-case).
STABLE_ID_ROW='^\| `?[a-z][a-z-]*-[0-9]{2}`? \|'
LEGACY_ID_ROW='^\| `?[A-Z][0-9]+-[A-Z][0-9]+`? \|'
is_stable_plan() { grep -qE "$STABLE_ID_ROW" "$1"; }
# 1. Every relative markdown link resolves from the file's own folder, and so does its #anchor:
#    the anchor must be the GitHub slug of a heading in the target file (lower-cased, punctuation
#    other than '-' and '_' dropped, each space a '-', a repeated heading suffixed -1, -2 …;
#    headings inside ``` fences do not count). Only the skill folders are scanned: not the data
#    folder, and not an evals/ folder, whose fixtures are data too.
scan_dirs=("$PLAN" "$EXEC")
slugs() {  # the anchors a markdown file offers, one per line
  perl -CSD -ne '
    if (/^\s*```/) { $fence = !$fence; next }
    next if $fence;
    next unless /^#{1,6}\s+(.*?)\s*#*\s*$/;
    my $s = lc $1; $s =~ s/[^\p{L}\p{N}\s_-]//g; $s =~ s/ /-/g;
    my $n = $seen{$s}++; print $n ? "$s-$n\n" : "$s\n";' "$1"
}
while IFS= read -r file; do
  dir="$(dirname "$file")"
  # Process substitution, not a pipe: a piped `while` runs in a subshell on bash 3.2 and loses fail=1.
  while IFS= read -r link; do
    target="${link%%#*}"; anchor=""
    case "$link" in *'#'*) anchor="${link#*#}";; esac
    if [ -n "$target" ]; then dest="$dir/$target"; else dest="$file"; fi
    [ -e "$dest" ] || { problem "dead link in ${file#$ROOT/}: $link"; continue; }
    [ -n "$anchor" ] && [ -f "$dest" ] || continue
    slugs "$dest" | grep -qxF -- "$anchor" || problem "dead anchor in ${file#$ROOT/}: $link"
  done < <(grep -o '\]([^)]*)' "$file" | sed 's/^](//; s/)$//' | grep -vE '^https?://' | grep -v '^$' | sort -u)
done < <(find "${scan_dirs[@]}" -type d -name evals -prune -o -name '*.md' -print)

# 2. Plan file name version matches the **Plan version:** header line.
for plan in "$PLANS"/*-test-plan*.md; do
  [ -e "$plan" ] || continue
  name="$(basename "$plan" .md)"
  if [[ "$name" =~ -v([0-9]+)$ ]]; then file_v="${BASH_REMATCH[1]}"; else file_v=1; fi
  grep -q '^\*\*Plan version:\*\*' "$plan" || { problem "no **Plan version:** line in ${plan#$DATA/}"; continue; }
  header_v="$(grep -m1 -oE '^\*\*Plan version:\*\* *[0-9]+' "$plan" | grep -oE '[0-9]+$')"
  [ -n "$header_v" ] || { problem "${plan#$DATA/}: the **Plan version:** line does not start with a plain number (write \`2 (<date>)\`, not \`v2\`)"; continue; }
  [ "$file_v" = "$header_v" ] || problem "${plan#$DATA/}: file name says v$file_v, header says v$header_v"
  grep -q '^\*\*Earlier runs:\*\*' "$plan" || problem "${plan#$DATA/}: no **Earlier runs:** line"
  # A plan written before the current layout is reported, not failed: it is rebuilt, not edited.
  is_stable_plan "$plan" || echo "LEGACY: ${plan#$DATA/} predates the fixed section order and stable ids; rebuild it before the next run"
done

# 3. Report file names carry a UTC stamp, with an optional `-<letters>` suffix after it for a
#    side-by-side run (file-layout.md, file names). Whether a report was edited in place cannot be
#    checked here, so only the name shape is.
REPORT_NAME='-test-report-[0-9]{8}-[0-9]{4}(-[a-z]+)?\.md$'
for report in "$REPORTS"/*-test-report-*.md; do
  [ -e "$report" ] || continue
  [[ "$(basename "$report")" =~ $REPORT_NAME ]] || problem "bad report name: $(basename "$report")"
done

# 4. No SKILL file and no reference restates a rule section that has a home in another reference.
#    Each pattern is a phrase that only the owning file should contain. Only the skill folders are
#    scanned, never the data folder: a plan or a fixture is data, not a rule's home.
declare -a owned=(
  'One idea per sentence. Aim for 20 words|language.md'
  'canonicalized with recursively sorted keys|rules.md'
  'the \**unfiltered\**.*listing, paged to the end|rules.md'
  'Only four values in the `Now` column|report-spec.md'
  'Nothing that carries meaning is cut|report-blocks.md'
  'Never renumber\.\** Inserting a case|plan-template.md'
  'The key only, never a URL|report-blocks.md'
  'the known bugs come second|SKILL.md'
  'Every rate limit is per replica|stand-facts.md'
  'Confirm-token TTL|stand-facts.md'
  '60 / minute / user|stand-facts.md'
  'kinoa_widget_|plan-template.md,report-spec.md,report-blocks.md'
  'designed when it is written|SKILL.md'
  'No scripts, at any time|rules.md'
  'No change to the project code|rules.md'
  'stays out of reach\.\** The file behind|rules.md'
  'filled in one way only|fixed-data.md'
  'reusable while the arguments stay the same|rules.md'
  'Owner rulings: expected behaviour|rules.md'
  'Validation lives in the backend, so the preview|rules.md'
  'nothing else comes before them|plan-template.md'
  'fits the tightest limit of the domain|fixed-data.md'
  'One determination per delete or lifecycle tool|rules.md'
  'the line is the evidence, the claim is not|SKILL.md'
  'only the text that .tools/list. would serve|plan-template.md'
  'A case is never in both 4 and 8|report-spec.md'
  'stand setup, never evidence|rules.md'
  'Removing all rows is one .DELETE. per row|stand-facts.md'
  'The rows in effect are read, not asked|rules.md'
  'A count is never an absolute number|plan-template.md'
  'graded on the clause before .Also record:|rules.md'
  'server never answered the chat|rules.md'
)
# The home is compared by full path, so a SKILL file is scanned unless it is the home itself, and
# the references are scanned against each other. A phrase check is paraphrase-blind: it catches a
# copied sentence, not a reworded one — the pruning pass (file-layout.md) catches the rest.
restate_scope=("$PLAN/SKILL.md" "$EXEC/SKILL.md" "$PLAN/references")
# An entry may name several homes, comma-separated, when each owns its own copy (two fictional
# examples of one domain: the plan shape and the report shape).
home_path() { case "$1" in SKILL.md) echo "$PLAN/SKILL.md";; *) echo "$PLAN/references/$1";; esac; }
is_home() { local h; for h in $(echo "$2" | tr ',' ' '); do [ "$1" = "$(home_path "$h")" ] && return 0; done; return 1; }
# Self-test: a phrase that no longer occurs in its home (reworded there, or markup inside it) can
# never fire, so every home must still hold its phrase at least once. Patterns tolerate `**` where
# the home has bold marks inside the phrase.
for entry in "${owned[@]}"; do
  pattern="${entry%|*}"; homes="${entry#*|}"
  for h in $(echo "$homes" | tr ',' ' '); do
    grep -qiE "$pattern" "$(home_path "$h")" || problem "owned phrase no longer in its home $h: /$pattern/"
  done
done
for entry in "${owned[@]}"; do
  pattern="${entry%|*}"; homes="${entry#*|}"; home="$(home_path "${homes%%,*}")"
  while IFS= read -r file; do
    is_home "$file" "$homes" && continue
    grep -qiE "$pattern" "$file" && problem "${file#$ROOT/} restates a rule owned by ${home#$ROOT/}: /$pattern/"
  done < <(find "${restate_scope[@]}" -name '*.md')
done

# 5. A plan under the stable-id scheme carries no legacy-shaped id: the two shapes never mix.
for plan in "$PLANS"/*-test-plan*.md; do
  [ -e "$plan" ] || continue
  is_stable_plan "$plan" || continue
  while read -r row; do
    problem "${plan#$DATA/}: legacy id shape in a stable-id plan: $row"
  done < <(grep -oE "$LEGACY_ID_ROW" "$plan" | head -3)
done

# 6. Fixed test data is never shipped in the tree: a plan that carries a `<…>` fixed-data placeholder
#    must say so in its header (redacted worked example); a new plan must hold literal values. The
#    references may name the placeholders (that is where they are defined).
# A placeholder is any `<UPPER_CASE_…_ID|NAME|EMAIL|HOST|TARGET|URL|UUID|API>` token, also with a tail
# such as `_UPPERCASE` or `_NO_DASHES`, or a bare handle in angle brackets (`<P1>`, `<PLAYER1>`,
# `<COMPANY>`, `<ADMIN_API>`); `<NAME>`, `<KEY>`, `<STAMP>` have no underscore and are not fixed data.
PLACEHOLDER='<[A-Z][A-Z0-9]*(_[A-Z0-9]+)*_(ID|NAME|EMAIL|HOST|TARGET|URL|UUID|API)(_[A-Z0-9]+)*>|<WEBHOOK_TARGET>|<(P1|P2|PLAYER1|PLAYER2|COMPANY)>'
# A row of the §0 constants table (the first table under `## 0.`) whose value cell is empty, a
# dash, `?`, or starts with `TBD`, `…` or `...`, or is only a lower-case `<…>` such as `<uuid of P1>`.
# The handle may be in backticks or bold. Prints `<constant>: <value cell>` per such row.
bad_zero_rows() {
  hold_pipes "$1" | awk -F'|' '
    /^## 0\./ { inzero = 1; next }
    inzero && /^#/ { exit }
    inzero && /^\|/ {
      if ($2 ~ /^ *(Constant|-+) *$/ || $2 ~ /^ *:?-+:? *$/) next
      v = $3; gsub(/^ +| +$/, "", v); w = v; gsub(/`/, "", w); gsub(/^ +| +$/, "", w)
      if (w == "" || w ~ /^(—|-|–|\?)$/ || w ~ /^(TBD|tbd|…|\.\.\.)/ || w ~ /^<[a-z][^>]*>$/) {
        c = $2; gsub(/^ +| +$/, "", c); print c ": " (v == "" ? "(empty)" : v)
      }
    }' | give_pipes
}
for plan in "$PLANS"/*-test-plan*.md; do
  [ -e "$plan" ] || continue
  redacted=0; grep -q '^\*\*Fixed data:\*\* redacted' "$plan" && redacted=1
  if grep -qE "$PLACEHOLDER" "$plan"; then
    if [ $redacted = 1 ]; then
      echo "REDACTED: ${plan#$DATA/} holds fixed-data placeholders and cannot be run; a new version needs literal values in §0"
    else
      problem "${plan#$DATA/}: holds a fixed-data placeholder ($(grep -oE "$PLACEHOLDER" "$plan" | sort -u | head -3 | tr '\n' ' ')) and no **Fixed data:** redacted line — ask the operator for the values (fixed-data.md, empty means ask)"
    fi
  fi
  [ $redacted = 1 ] && continue
  while IFS= read -r row; do
    problem "${plan#$DATA/}: §0 row without a literal value — $row (fixed-data.md, empty means ask)"
  done < <(bad_zero_rows "$plan" | head -5)
done
# 7. The shipped part of the tree (SKILL files, references, evals) carries nobody's e-mail address:
#    the account is per installation and lives in a plan's §0. The data folder is that
#    installation's own data and is not scanned.
shipped=("$PLAN/SKILL.md" "$PLAN/references" "$PLAN/evals" "$EXEC/SKILL.md" "$EXEC/evals")
while IFS= read -r hit; do problem "e-mail address in a shipped file: $hit"; done < <(grep -rnoE '[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+\.[A-Za-z0-9.-]*[a-z]{2,}' "${shipped[@]}" 2>/dev/null | grep -viE '@example\.(com|org|net)$' | head -20)
#    The same files against the operator's denylist, when it exists: a fixture value in a shipped
#    file would reach everyone who installs the plugin. Only the file and line are printed, never
#    the value.
DENY="${QA_PERSONAL_DENYLIST:-$HOME/.config/kinoa-qa/personal-denylist.txt}"
if [ -f "$DENY" ]; then
  while IFS= read -r hit; do problem "denylisted value in a shipped file: $hit — write its handle (P1, P2, PLAYER1, PLAYER2) instead"; done < <(
    grep -vE '^[[:space:]]*(#|$)' "$DENY" | cut -f1 | tr -d '\r' | while IFS= read -r v; do
      [ -n "$v" ] && grep -rniF -- "$v" "${shipped[@]}" 2>/dev/null | cut -d: -f1,2
    done | sed "s#^$ROOT/##" | sort -u | head -20)
fi

# 9–14. The shape of a stable-id plan, read off its rows. These rules were moved from the SKILL
#    checklist into this script on 2026-09-25, and a plan is never edited once written, so they
#    FAIL only for a plan whose **Plan version:** date is 2026-09-25 or later. An older runnable
#    (unredacted) plan gets an OLDER line for checks 9–12 instead: the next version fixes it.
#    9.  §A0 opens with the tool inventory: its first case row calls `tools/list` (plan-template.md,
#        the preflight).
#    10. No case has more than five steps: the highest `N.` step number in a Call cell is at most 5
#        (plan-template.md, cases are data).
#    11. Every tool section of Part A (`## A<n>. `kinoa_…``) has an `ok` case (plan-template.md,
#        the three soundness rules).
#    12. Every `_delete`, `_status` and `_deprecate` tool section has a `sem` case (rules.md, delete
#        semantics).
#    13. §1.2 has a row for every finding and note heading of every report on `**Earlier runs:**`,
#        written `F3 (0855)`, and every case id a §1.2 row names is a row of the plan
#        (plan-template.md, §1.2; file-layout.md, comparing runs).
#    14. §0 carries the `**Name limit:**` line, and its longest name and key fit the limit
#        (fixed-data.md, naming every artifact).
RULES_FROM=20260925
plan_shape() {  # $1 = plan; prints one problem per line, for checks 9–12
  hold_pipes "$1" | awk -F'|' '
    function close_sec() {
      if (sec != "" && !ok) print "no ok case in section " sec
      if (sec != "" && need && !sem) print "no sem case in section " sec
      sec = ""
    }
    /^## A0\./ { close_sec(); a0 = 1; next }
    /^## A[0-9]+\. `kinoa_/ { close_sec(); sec = $0; sub(/^## /, "", sec); ok = 0; sem = 0
                            need = ($0 ~ /_(delete|status|deprecate)`/); next }
    /^#/ { close_sec(); next }
    /^\| `[a-z0-9-]+` \|/ {
      id = $2; gsub(/[ `]/, "", id); c = $3
      if (a0) { x = c; gsub(/^ +/, "", x); if (x !~ /^`?tools\/list/) print "the first row of §A0 (" id ") is not a tools/list inventory case"; a0 = 0 }
      if (id ~ /-ok-[0-9][0-9]$/) ok = 1
      if (id ~ /-sem-[0-9][0-9]$/) sem = 1
      n = 0
      while (match(c, /(^| )[0-9]+\. /)) { v = substr(c, RSTART, RLENGTH); gsub(/[^0-9]/, "", v); if (v + 0 > n) n = v + 0; c = substr(c, RSTART + RLENGTH) }
      if (n > 5) print id " has " n " steps (at most 5)"
    }
    END { close_sec() }' | give_pipes
}
plan_known_issues() {  # $1 = plan; prints one problem per line, for check 13
  local plan="$1" rep hhmm id sec12 ids
  sec12="$(awk '/^### 1\.2/ { f = 1; next } f && /^#/ { exit } f' "$plan")"
  ids="$(grep -oE '^\| `[a-z0-9-]+` \|' "$plan" | tr -d '|` ')"
  for rep in $(sed -n '1,/^## 0\./p' "$plan" | grep -oE 'KING-[0-9]+-[a-z-]+-test-report-[0-9]{8}-[0-9]{4}(-[a-z]+)?\.md' | sort -u); do
    [ -f "$REPORTS/$rep" ] || { echo "earlier run $rep is not in $REPORTS/"; continue; }
    hhmm="$(echo "$rep" | sed -E 's/.*-[0-9]{8}-([0-9]{4})(-[a-z]+)?\.md$/\1/')"
    for id in $(grep -oE '^### [FN][0-9]+ — ' "$REPORTS/$rep" | awk '{ print $2 }'); do
      echo "$sec12" | grep -qF "$id ($hhmm)" || echo "§1.2 has no row for $id ($hhmm) of $rep"
    done
  done
  for id in $(echo "$sec12" | grep -E '^\|' | hold_pipes | awk -F'|' '{ print $(NF-1) }' | give_pipes | grep -oE '`[a-z][a-z0-9-]*-[0-9]{2}`' | tr -d '`' | sort -u); do
    echo "$ids" | grep -qx "$id" || echo "§1.2 names $id, which is no case row of the plan"
  done
}
plan_name_limit() {  # $1 = plan; prints one problem per line, for check 14
  local line lim nm ky
  line="$(awk '/^## 0\./ { f = 1; next } f && /^## / { exit } f && /^\*\*Name limit:\*\*/ { print; exit }' "$1")"
  [ -n "$line" ] || { echo "§0 has no **Name limit:** line"; return; }
  lim="$(echo "$line" | sed -nE 's/^\*\*Name limit:\*\* *([0-9]+).*/\1/p')"
  nm="$(echo "$line" | sed -nE 's/.*longest name ([0-9]+).*/\1/p')"
  ky="$(echo "$line" | sed -nE 's/.*longest key ([0-9]+).*/\1/p')"
  if [ -z "$lim" ] || [ -z "$nm" ] || [ -z "$ky" ]; then echo "the **Name limit:** line is not in the shape of fixed-data.md: $line"; return; fi
  [ "$nm" -le "$lim" ] || echo "the longest name ($nm) is over the name limit ($lim)"
  [ "$ky" -le "$lim" ] || echo "the longest key ($ky) is over the name limit ($lim)"
}
for plan in "$PLANS"/*-test-plan*.md; do
  [ -e "$plan" ] || continue
  is_stable_plan "$plan" || continue
  pdate="$(grep -m1 -oE '^\*\*Plan version:\*\* *[0-9]+ *\([0-9]{4}-[0-9]{2}-[0-9]{2}' "$plan" | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}' | tr -d -)"
  if [ -n "$pdate" ] && [ "$pdate" -ge "$RULES_FROM" ]; then
    while IFS= read -r p; do [ -n "$p" ] && problem "${plan#$DATA/}: $p"; done < <(plan_shape "$plan"; plan_known_issues "$plan"; plan_name_limit "$plan")
  elif ! grep -q '^\*\*Fixed data:\*\* redacted' "$plan"; then
    while IFS= read -r p; do [ -n "$p" ] && echo "OLDER: ${plan#$DATA/}: $p — fix it in the next version"; done < <(plan_shape "$plan")
  fi
done

# 15. A report whose Run stamp is REPORTS_FROM or later has the ten section headings of
#     report-spec.md, in order and nothing else at `## `, a case status table (report-spec.md,
#     the case status table), and as many table rows as the Total of its section 2 counts table.
#     An older report predates the table: it is history, never edited, and not checked. A report
#     with no `## 10.` heading is a run still in progress: IN PROGRESS, not a problem.
REPORTS_FROM=20261006
#     A report whose section 2 opens with `paused` (report-spec.md, the overall status) is a run
#     handed over before it ended: PAUSED, not a problem, checked once the run finishes.
is_paused_report() {  # $1 = report: the first non-blank line of its section 2 starts with `paused`
  awk '/^## 2\./ { f = 1; next } f && /^## / { exit } f && NF { gsub(/[`*]/, ""); print; exit }' "$1" | grep -q '^paused'
}
SECTIONS='1. Header
2. Overall status
3. What was done, per part
4. Findings
5. Notes
6. AC traceability
7. Hypothesis verdicts
8. Not covered / blocked
9. Artifacts left behind
10. Role rows at the end of the run'
for report in "$REPORTS"/*-test-report-*.md; do
  [ -e "$report" ] || continue
  stamp="$(basename "$report" | grep -oE -- '-test-report-[0-9]{8}-' | grep -oE '[0-9]{8}')"
  [ -n "$stamp" ] && [ "$stamp" -ge "$REPORTS_FROM" ] || continue
  r="${report#$DATA/}"
  grep -q '^## 10\. ' "$report" || { echo "IN PROGRESS: $r has no section 10 yet; it is checked once the run finishes"; continue; }
  is_paused_report "$report" && { echo "PAUSED: $r: the run was handed over; it is checked once it finishes (report-spec.md, the overall status)"; continue; }
  grep -qE '^\| *Case *\| *Status *\| *Finding / note / blocked row *\|' "$report" || { problem "$r: no case status table in section 3 (report-spec.md, the case status table)"; continue; }
  got="$(awk '/^[ \t]*```/ { f = !f; next } !f && /^## / { sub(/^## +/, ""); sub(/ +$/, ""); print }' "$report")"
  [ "$got" = "$SECTIONS" ] || problem "$r: the ## sections are not the ten of report-spec.md in order (found: $(echo "$got" | tr '\n' ';'))"
  rows="$(awk '/^\| *Case *\| *Status *\|/ { t = 1; next }
               t && /^\|[-: |]*\|$/ { next }
               t && /^\|/ { n++; next }
               t { exit }
               END { print n + 0 }' "$report")"
  total="$(hold_pipes "$report" | awk -F'|' '/^## 2\./ { s = 1; next } s && /^## / { exit }
               s && /^\| *`?PASS`? *\| *`?FAIL`? *\| *`?OBSERVED`? *\| *`?BLOCKED`? *\| *Total *\|/ { h = 1; next }
               h && /^\|[-: |]*\|$/ { next }
               h && /^\|/ { v = $(NF - 1); gsub(/[^0-9]/, "", v); print v; exit }')"
  if [ -z "$total" ]; then
    problem "$r: section 2 has no | PASS | FAIL | OBSERVED | BLOCKED | Total | counts table (report-spec.md, the ten sections)"
  elif [ "$rows" != "$total" ]; then
    problem "$r: the case status table has $rows rows, the section 2 Total is $total"
  fi
done

# 16–17. Two more row checks on a stable-id plan whose **Plan version:** date is 2026-10-07 or
#    later; an older plan is skipped, as for checks 9–14, because a plan is never edited once written.
#    16. The Expected cell opens with the deciding assertion and the rest follows the `Also record:`
#        label (plan-template.md, cases are data). A cell with no label and more than 8
#        `;`-separated clauses is probably a list with no deciding assertion: a WARN line, not a
#        failure, because a long cell can still be one assertion per step. A label not written
#        exactly (`Also record (OBSERVED):`, `Also record -`) is a PROBLEM: the run grades on the
#        exact label.
#    17. Every `<tool>-gap-NN` and `grey-NN` id of Part A is wired: it appears in the text of §1.1
#        or of the `# REPORT` section (plan-template.md, hypotheses). PROBLEM per missing id.
WIRING_FROM=20261007
plan_long_cells() {  # $1 = plan; prints one warning per line, for check 16
  hold_pipes "$1" | awk -F'|' '
    /^\| `[a-z0-9-]+` \|/ {
      id = $2; gsub(/[ `]/, "", id); e = $(NF - 1)
      if (e ~ /Also record:/) next
      n = gsub(/;/, ";", e) + 1
      if (n > 8) print id " has " n " clauses in its Expected cell and no `Also record:` label"
    }' | give_pipes
}
plan_bad_labels() {  # $1 = plan; prints one problem per line, for check 16
  hold_pipes "$1" | awk -F'|' '
    /^\| `[a-z0-9-]+` \|/ {
      id = $2; gsub(/[ `]/, "", id); e = $(NF - 1); n = 0
      while (match(e, /[Aa]lso [Rr]ecord.?/)) {
        s = substr(e, RSTART, RLENGTH); e = substr(e, RSTART + RLENGTH)
        if (s !~ /^Also record:/) n++
      }
      if (n) print id " writes the label in another form than `Also record:` (" n " time(s))"
    }' | give_pipes
}
plan_unwired() {  # $1 = plan; prints one problem per line, for check 17
  local plan="$1" wired id
  wired="$(awk '/^# REPORT/ { r = 1 } r { print; next } /^### 1\.1/ { f = 1; next } f && /^#/ { f = 0 } f' "$plan")"
  for id in $(awk '/^# PART A/ { a = 1 } /^# PART B/ { a = 0 } a' "$plan" | grep -oE '^\| `([a-z0-9-]+-gap-[0-9]{2}|grey-[0-9]{2})` \|' | tr -d '|` '); do
    echo "$wired" | grep -qF -- "$id" || echo "$id is wired to no §1.1 hypothesis and no AC bullet of the REPORT section"
  done
}
for plan in "$PLANS"/*-test-plan*.md; do
  [ -e "$plan" ] || continue
  is_stable_plan "$plan" || continue
  pdate="$(grep -m1 -oE '^\*\*Plan version:\*\* *[0-9]+ *\([0-9]{4}-[0-9]{2}-[0-9]{2}' "$plan" | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}' | tr -d -)"
  [ -n "$pdate" ] && [ "$pdate" -ge "$WIRING_FROM" ] || continue
  while IFS= read -r w; do [ -n "$w" ] && echo "WARN: ${plan#$DATA/}: $w"; done < <(plan_long_cells "$plan")
  while IFS= read -r p; do [ -n "$p" ] && problem "${plan#$DATA/}: $p"; done < <(plan_bad_labels "$plan"; plan_unwired "$plan")
done

# 18–19 and 22–25. Row checks on a stable-id plan whose **Plan version:** date is 2026-10-16 or
#    later; an older plan is skipped, as for checks 9–17 (a plan is never edited once written).
#    18. Every `NAME-…` / `NAME_S-…` / `KEY_…` literal in a `Call` cell, of Part A and of Part B, is
#        in the §0 artifacts table: every artifact inside the stamp scope, probes and twins
#        included, has a row there (plan-template.md, cases are data). A literal starts where no
#        letter, digit, `_` or `-` precedes it, so `CONFIRM_KEY_x` and `a-KEY_q` are not ones. A literal that starts a
#        literal of the table passes: a search scoped to the stamp (`"search": "KEY_create"`) names
#        no artifact of its own. PROBLEM per literal.
#    19. Every `"len<N>-…"` string literal in a `Call` cell is exactly N characters long, counted as
#        characters, not bytes (plan-template.md, cases are data). PROBLEM per literal.
#    22. A plan of version 2 or later keeps every case the newest report graded: every id of that
#        report's `### Case status` table whose status is `PASS`, `FAIL` or `OBSERVED` is still a
#        case row (plan-template.md, soundness rules; mcp-plan/SKILL.md, §1). The newest report is
#        the last by name for the plan's `<KEY>-<domain>`, side-by-side reports (`-<letters>`)
#        left out; a report with no such table (written before 2026-10-06) is not checked.
#        PROBLEM per id.
#    23. Every `{…}` argument object of a `Call` cell parses as JSON once the plan's handles are
#        taken as strings: outside JSON strings, a `<…>` placeholder and every token that starts
#        with a capital letter (`P1`, `W_A`, `BASE_P1`, not `true`/`false`/`null`) becomes `"X"`,
#        then the object is decoded. An object is cut from `{` to its matching `}`, braces inside
#        JSON strings not counted (plan-template.md, cases are data). PROBLEM per object, with the
#        start of the decoder's message.
#    24. Every `game_id` and `target_game_id` value of a `Call` cell is a §0 value: a bare handle
#        that §0 names (`P1`, `P2`, `FOREIGN` …) or a quoted literal that §0 holds, as a whole token
#        (`"7d3e"` is no §0 value although a uuid of §0 starts with it). Any other value
#        is a PROBLEM unless the row's `Expected` cell names it as the probe, by its text
#        (plan-template.md, cases are data).
#    25. No `Call` cell describes its calls instead of writing them: `and so on` or `up to the
#        last page` anywhere in the cell, `...` or `…` inside an argument object and outside its JSON
#        strings (plan-template.md, cases are data). PROBLEM per phrase.
#    26. A plan of version 2 or later numbers its new ids from the next free number: in every
#        `<tool>-<kind>` group (and `pre`, `grey`, `handoff`, `role-<tool>`), the ids no earlier version
#        of the plan holds are the numbers after the highest one any earlier version used, with no
#        gap (plan-template.md, stable case ids). PROBLEM for the first id of a group that skips.
#    27. A plan of version date SEGMENTS_FROM or later carries `### 1.4 Segments`, the table that
#        cuts Part A into the segments the run hands to sub-agents (plan-template.md, §1.4): a row
#        per segment, `| Segment | Sections | Reads | Records | Writes | Note |`, `Sections` being
#        `A<n>` or a range `A<n>–A<m>` (en dash or hyphen). A Part A tool section is a `## A<n>.`
#        heading, n >= 1, whose title starts with a backticked `kinoa_` tool name; §A0, the Grey box
#        (`## A<n>. Grey box` or `## Grey`), the Hand-off and Part B are no segment. PROBLEM for:
#        no heading or no row; a tool section in no segment; a tool section in two segments; a row
#        that names a section which is no tool section; two segments in table order that do not run
#        on from one another over the tool sections; a handle used in a segment before the segment
#        that records it — a handle is a `Record: X` token of an `Expected` cell in a tool section,
#        a use is that token as a whole word in a `Call` cell of a tool section; a handle that §0
#        names as a constant or that §A0 records is skipped, and so is a use outside the tool
#        sections; a `grey-NN` row under a tool section whose id the paragraph of the Grey box (the
#        text before its table) does not name.
NAMES_FROM=20261016
SEGMENTS_FROM=20261109
plan_unlisted_names() {  # $1 = plan; prints one problem per line, for check 18
  local plan="$1" zero lit id
  zero="$(awk '/^## 0\./ { f = 1; next } f && /^## / { exit } f' "$plan")"
  while IFS=$'\t' read -r id lit; do
    [ -n "$lit" ] || continue
    echo "$zero" | grep -qE "(^|[^A-Za-z0-9_-])${lit}" \
      || echo "\`$lit\` in the Call cell of \`$id\` is not in the §0 artifacts table (plan-template.md, cases are data)"
  done < <(hold_pipes "$plan" | perl -CSD -F'\|' -lane '
    next unless defined $F[1] && $F[1] =~ /^ *`?([a-z][a-z0-9-]*-[0-9]{2})`? *$/;
    my $id = $1; my $c = $F[2] // "";
    print "$id\t$1" while $c =~ /(?<![A-Za-z0-9_-])((?:NAME(?:_S)?-|KEY_)[A-Za-z0-9_-]+)/g;' | sort -u)
}
plan_segments() {  # $1 = plan; prints one problem per line, for check 27
  hold_pipes "$1" | perl -CSD -F'\|' -lane '
    BEGIN { $tail = " (plan-template.md, \x{a7}1.4)" }
    if (/^\s*```/) { $fence = !$fence; next }
    next if $fence;
    if (/^#{1,3} /) {                       # a heading ends the table and sets the section kind
      $seg = 0; $kind = "other"; $table = "";
      if (/^### 1\.4\b/) { $seg = 1; $has14 = 1 }
      elsif (/^## 0\./) { $kind = "zero" }
      elsif (/^## (?:A(\d+)\.\s*)?(.*)/) {
        my ($n, $t) = (defined $1 ? $1 + 0 : undef, $2);
        if ($t =~ /^\W*Grey\b/i) { $kind = "grey"; $grey_seen = 1 }
        elsif ($t =~ /^\W*Hand-?off\b/i) { $kind = "handoff" }
        elsif (defined $n && $n == 0) { $kind = "a0" }
        elsif (defined $n && $t =~ /^`kinoa_/) { $kind = "tool"; $sec = $n; push @secs, $n; $istool{$n} = 1 }
      }
      next;
    }
    if ($kind eq "grey" && !$seen_table && !/^\|/) { $prose .= "$_\n"; next }
    if ($kind eq "grey" && /^\|/) { $seen_table = 1 }
    if (!/^\|/) { $table = "" if $kind eq "zero"; next }
    my $cell = sub { my $v = $F[$_[0]] // ""; $v =~ s/\x1f/|/g; $v };
    if ($seg) {
      (my $id = $cell->(1)) =~ s/[\s`]//g;
      next if $id eq "" || $id =~ /^:?-+:?$/ || $id eq "Segment";
      my @r; my $sc = $cell->(2);
      while ($sc =~ /A(\d+)\s*(?:[\x{2013}-]\s*A(\d+))?/g) { push @r, [$1 + 0, ($2 // $1) + 0] }
      push @segs, [$id, [@r]]; next;
    }
    if ($kind eq "zero") {
      (my $h = $cell->(1)) =~ s/[\s`]//g;
      if (!$table) { $table = $h; next }
      if ($table eq "Constant" && $h !~ /^:?-+:?$/) { $const{$h} = 1 }
      next;
    }
    (my $id = $cell->(1)) =~ s/^\s*`?|`?\s*$//g;
    next unless $id =~ /^[a-z][a-z0-9-]*-[0-9]{2}$/;
    my ($c, $e) = ($cell->(2), $cell->(3));
    if ($kind eq "a0") { $a0{$1} = 1 while $e =~ /Record:\s+([A-Z][A-Z0-9_]*)/g; next }
    next unless $kind eq "tool";
    push @rows, [$sec, $id, $c, $e];
    push @greys, [$sec, $id] if $id =~ /^grey-[0-9]{2}$/;
    END { CHECK: {
      if (!$has14 || !@segs) { print "\x{a7}1.4 Segments is missing$tail"; last CHECK }
      my (%in, %named);
      for my $s (@segs) { for my $range (@{$s->[1]}) { for my $n ($range->[0] .. $range->[1]) {
        if (!$istool{$n}) {
          print "segment $s->[0] names A$n, which is not a Part A tool section$tail" unless $named{"$s->[0] $n"}++;
          next;
        }
        push @{$in{$n}}, $s->[0] unless grep { $_ eq $s->[0] } @{$in{$n}} } } }
      for my $n (@secs) {
        if (!$in{$n}) { print "section A$n is in no segment of \x{a7}1.4$tail" }
        elsif (@{$in{$n}} > 1) { print "section A$n is in two segments of \x{a7}1.4: " . join(", ", @{$in{$n}}) . $tail }
      }
      my %pos; $pos{$secs[$_]} = $_ for 0 .. $#secs;      # tool sections, judged by their place in Part A
      my $span = sub { my ($lo, $hi);
                       for my $p (@{$_[0][1]}) { for my $n ($p->[0] .. $p->[1]) { next unless $istool{$n};
                         $lo = $n if !defined $lo || $n < $lo; $hi = $n if !defined $hi || $n > $hi } }
                       return defined $lo ? ($lo, $hi) : () };
      for my $i (1 .. $#segs) {
        my ($plo, $phi) = $span->($segs[$i - 1]); my ($lo, $hi) = $span->($segs[$i]);
        next unless defined $plo && defined $lo;
        next if grep { my @l = @{$in{$_} // []}; @l > 1 && (grep { $_ eq $segs[$i][0] } @l) && (grep { $_ eq $segs[$i - 1][0] } @l) } ($lo .. $hi);   # an overlap is reported above
        print "the segments of \x{a7}1.4 are not consecutive: $segs[$i - 1][0] ends at A$phi, $segs[$i][0] starts at A$lo$tail" if $pos{$lo} != $pos{$phi} + 1;
      }
      my %rec;       # handle -> [segment index, segment id, row id] of its earliest record
      my %segidx; $segidx{$segs[$_][0]} = $_ for 0 .. $#segs;
      my $seg_of = sub { my $l = $in{$_[0]}; $l ? $l->[0] : undef };
      for my $row (@rows) {
        my $sid = $seg_of->($row->[0]); next unless defined $sid;
        while ($row->[3] =~ /Record:\s+([A-Z][A-Z0-9_]*)/g) {
          my $h = $1; next if $const{$h} || $a0{$h};
          $rec{$h} = [$segidx{$sid}, $sid, $row->[1]] if !$rec{$h} || $segidx{$sid} < $rec{$h}[0];
        }
      }
      my %said;
      for my $row (@rows) {
        my $sid = $seg_of->($row->[0]); next unless defined $sid;
        for my $h (sort keys %rec) {
          next if $said{$h} || $segidx{$sid} >= $rec{$h}[0];
          next unless $row->[2] =~ /(?<![A-Za-z0-9_-])\Q$h\E(?![A-Za-z0-9_-])/;
          $said{$h} = 1;
          print "`$h` is used in segment $sid (`$row->[1]`) but recorded in segment $rec{$h}[1] (`$rec{$h}[2]`)$tail";
        }
      }
      for my $g (@greys) {
        next if $prose =~ /(?<![A-Za-z0-9_-])\Q$g->[1]\E(?![A-Za-z0-9_-])/;
        print "`$g->[1]` sits in section A$g->[0] and the paragraph of \x{a7}Grey does not name it$tail";
      }
    } }' | give_pipes
}
plan_graded_rows() {  # $1 = plan; prints one problem per line, for check 22
  local plan="$1" name kd rep ids id st
  name="$(basename "$plan" .md)"
  [[ "$name" =~ -v([0-9]+)$ ]] && [ "${BASH_REMATCH[1]}" -ge 2 ] || return 0
  kd="${name%%-test-plan*}"
  rep="$(ls "$REPORTS/$kd"-test-report-*.md 2>/dev/null | grep -E -- '-test-report-[0-9]{8}-[0-9]{4}\.md$' | sort | tail -1)"
  [ -n "$rep" ] && grep -q '^### Case status' "$rep" || return 0
  ids="$(grep -oE '^\| `[a-z0-9-]+` \|' "$plan" | tr -d '|` ')"
  while IFS=$'\t' read -r id st; do
    [ -n "$id" ] || continue
    echo "$ids" | grep -qx "$id" \
      || echo "\`$id\` was graded \`$st\` in $(basename "$rep") but is no case row of this version (plan-template.md, soundness rules)"
  done < <(awk '/^### Case status/ { f = 1; next } f && /^#/ { exit } f' "$rep" | hold_pipes | awk -F'|' '
    /^\|/ { id = $2; gsub(/[ `]/, "", id); st = $3; gsub(/[ `]/, "", st)
            if (id == "Case" || id ~ /^:?-+:?$/) next
            if (st == "PASS" || st == "FAIL" || st == "OBSERVED") print id "\t" st }')
}
plan_nn_numbers() {  # $1 = plan; prints one problem per line, for check 26
  local plan="$1" name base n earlier=()
  name="$(basename "$plan" .md)"
  [[ "$name" =~ ^(.*-test-plan)-v([0-9]+)$ ]] && [ "${BASH_REMATCH[2]}" -ge 2 ] || return 0
  base="${BASH_REMATCH[1]}"
  [ -f "$PLANS/$base.md" ] && earlier+=("$PLANS/$base.md")
  for (( n = 2; n < ${BASH_REMATCH[2]}; n++ )); do [ -f "$PLANS/$base-v$n.md" ] && earlier+=("$PLANS/$base-v$n.md"); done
  [ ${#earlier[@]} -gt 0 ] || return 0
  perl -e '
    my ($plan, @old) = @ARGV; my (%max, %where, %seen);
    for my $f (@old) { open my $h, "<", $f or next; (my $b = $f) =~ s{.*/}{};
      while (<$h>) { next unless /^\| `([a-z][a-z0-9-]*)-([0-9]{2})` \|/; $seen{"$1-$2"} = 1;
        if (!defined $max{$1} || $2 > $max{$1}) { $max{$1} = $2 + 0; $where{$1} = $b } } }
    open my $h, "<", $plan or exit; my %new;
    while (<$h>) { next unless /^\| `([a-z][a-z0-9-]*)-([0-9]{2})` \|/; push @{$new{$1}}, $2 + 0 unless $seen{"$1-$2"} }
    for my $g (sort keys %new) { my $next = ($max{$g} // 0) + 1;
      for my $num (sort { $a <=> $b } @{$new{$g}}) {
        if ($num != $next) { my $was = defined $max{$g} ? "$where{$g} ends the group at " . sprintf("%02d", $max{$g})
                                                          : "no earlier version has a case of the group";
          printf "`%s-%02d` is not the next free number of `%s`: %s, so the next is %02d (plan-template.md, stable case ids)\n",
                 $g, $num, $g, $was, $next; last }
        $next++ } }' "$plan" "${earlier[@]}"
}
plan_call_objects() {  # $1 = plan; prints one problem per line, for checks 23–25
  local zero
  zero="$(awk '/^## 0\./ { f = 1; next } f && /^## / { exit } f' "$1")"
  hold_pipes "$1" | ZERO="$zero" perl -CSD -MJSON::PP -F'\|' -lane '
    BEGIN { $zero = $ENV{ZERO}; utf8::decode($zero); $tail = " (plan-template.md, cases are data)" }
    next unless defined $F[1] && $F[1] =~ /^ *`?([a-z][a-z0-9-]*-[0-9]{2})`? *$/;
    my $id = $1; my $c = $F[2] // ""; my $e = $F[3] // "";
    s/\x1f/|/g for ($c, $e);
    for my $p ("and so on", "up to the last page") {   # 25, anywhere in the cell
      print "`$id` describes calls instead of writing them: \"$p\"$tail" if index($c, $p) >= 0;
    }
    my @objs; my ($depth, $start, $in, $esc) = (0, -1, 0, 0);   # cut every top-level {…}
    for my $i (0 .. length($c) - 1) {
      my $ch = substr($c, $i, 1);
      if ($in) { if ($esc) { $esc = 0 } elsif ($ch eq "\\") { $esc = 1 } elsif ($ch eq "\"") { $in = 0 } next }
      if ($ch eq "\"" && $depth > 0) { $in = 1; next }
      if ($ch eq "{") { $start = $i if $depth == 0; $depth++ }
      elsif ($ch eq "}" && $depth > 0) { $depth--; push @objs, substr($c, $start, $i - $start + 1) if $depth == 0 }
    }
    for my $o (@objs) {
      (my $bare = $o) =~ s/"(?:[^"\\]|\\.)*"/"X"/g;   # 25, inside an object, outside its strings
      for my $p ("...", "\x{2026}") {
        print "`$id` describes calls instead of writing them: \"$p\"$tail" if index($bare, $p) >= 0;
      }
      (my $j = $o) =~ s/("(?:[^"\\]|\\.)*")|<[^<]*?>(?=\s*[,}\]])|\b(?!(?:true|false|null)\b)[A-Z][A-Za-z0-9_]*\b/defined $1 ? $1 : "\"X\""/ge;   # 23
      eval { JSON::PP->new->decode($j) };
      if ($@) { (my $m = $@) =~ s/\s+/ /g; $m =~ s/,? at (character offset|\S+ line) .*//; print "`$id` has an argument object that is not JSON once the handles are strings: " . substr($m, 0, 60) . $tail }
    }
    while ($c =~ /"((?:target_)?game_id)"\s*:\s*("(?:[^"\\]|\\.)*"|<[^<]*?>(?=\s*[,}\]])|[^,}\s]+)/g) {   # 24
      my ($k, $v) = ($1, $2); my $ok;
      my $whole = sub { my ($t, $x) = @_; $x ne "" && $t =~ /(?<![A-Za-z0-9_-])\Q$x\E(?![A-Za-z0-9_-])/ };
      if ($v =~ /^"(.*)"$/) { my $lit = $1; $ok = $whole->($zero, $lit) || $whole->($e, $lit) }
      else { $ok = $whole->($zero, $v) || $whole->($e, $v) }
      $ok ||= $v eq "\"\"" && index($e, "\"\"") >= 0;
      print "`$id` sends $k $v, which is no \x{a7}0 value and not named in its Expected cell (plan-template.md, cases are data)" unless $ok;
    }' | give_pipes
}
plan_len_probes() {  # $1 = plan; prints one problem per line, for check 19
  hold_pipes "$1" | perl -CSD -F'\|' -lane '
    next unless defined $F[1] && $F[1] =~ /^ *`?([a-z][a-z0-9-]*-[0-9]{2})`? *$/;
    my $id = $1; my $c = $F[2] // "";
    while ($c =~ /"(len([0-9]+)-[^"]*)"/g) {
      my ($v, $n) = ($1, $2); my $l = length $v;
      print "`$id` sends a `len$n-` value of $l characters, not $n (plan-template.md, cases are data)" if $l != $n;
    }' | give_pipes
}
for plan in "$PLANS"/*-test-plan*.md; do
  [ -e "$plan" ] || continue
  is_stable_plan "$plan" || continue
  pdate="$(grep -m1 -oE '^\*\*Plan version:\*\* *[0-9]+ *\([0-9]{4}-[0-9]{2}-[0-9]{2}' "$plan" | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}' | tr -d -)"
  [ -n "$pdate" ] && [ "$pdate" -ge "$NAMES_FROM" ] || continue
  while IFS= read -r p; do [ -n "$p" ] && problem "${plan#$DATA/}: $p"; done < <(plan_unlisted_names "$plan"; plan_len_probes "$plan"; plan_graded_rows "$plan"; plan_call_objects "$plan"; plan_nn_numbers "$plan")
done
for plan in "$PLANS"/*-test-plan*.md; do   # check 27 has its own date gate
  [ -e "$plan" ] || continue
  is_stable_plan "$plan" || continue
  pdate="$(grep -m1 -oE '^\*\*Plan version:\*\* *[0-9]+ *\([0-9]{4}-[0-9]{2}-[0-9]{2}' "$plan" | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}' | tr -d -)"
  [ -n "$pdate" ] && [ "$pdate" -ge "$SEGMENTS_FROM" ] || continue
  while IFS= read -r p; do [ -n "$p" ] && problem "${plan#$DATA/}: $p"; done < <(plan_segments "$plan")
done

# 20. A plan older than its report: a runnable plan whose header says `**Earlier runs:** none`
#     while reports/ holds a report for its `<KEY>-<domain>` gets a WARN, not a failure — the run
#     says in its first message that a new plan version is due and runs as the rules say
#     (mcp-run/SKILL.md, §1 step 4). A redacted plan is skipped: it cannot be run at all. A report
#     whose section 2 opens with `paused` is a run of this plan still in progress (report-spec.md,
#     the overall status; is_paused_report above), not an earlier run: it gives no WARN.
for plan in "$PLANS"/*-test-plan*.md; do
  [ -e "$plan" ] || continue
  grep -q '^\*\*Fixed data:\*\* redacted' "$plan" && continue
  grep -qE '^\*\*Earlier runs:\*\* *none( |$)' "$plan" || continue   # `none` alone or with a tail
  kd="$(basename "$plan" .md)"; kd="${kd%%-test-plan*}"
  for report in "$REPORTS/$kd"-test-report-*.md; do
    [ -e "$report" ] || continue
    is_paused_report "$report" && continue
    echo "WARN: ${plan#$DATA/}: **Earlier runs:** none, but reports/ holds $(basename "$report") — a new plan version is due"
  done
done

# 21. Research inputs and §1.3 (plan-template.md, the skeleton). A plan whose header has a
#     `**Research inputs:**` line: when it is not `none`, the heading `### 1.3` exists, every table
#     row under it has a `Cases` cell holding one or more ids of the shape check 5 defines or
#     starting with `not reachable:`, and every id named there is a case row of the plan; when it
#     is `none`, there is no `### 1.3` heading (a research input nobody named). A plan with no such
#     header line predates KING-23440 and is skipped, as check 5 skips legacy plans. PROBLEM each.
plan_research() {  # $1 = plan; prints one problem per line, for check 21
  local plan="$1" line ids src cases id
  line="$(sed -n '1,/^## 0\./p' "$plan" | grep -m1 -E '^\*\*Research inputs:\*\*')"
  [ -n "$line" ] || return 0
  if echo "$line" | grep -qE '^\*\*Research inputs:\*\* *none *$'; then
    grep -q '^### 1\.3' "$plan" && echo "the header says **Research inputs:** none, but the plan has a ### 1.3 section — a research input nobody named (plan-template.md, the skeleton)"
    return 0
  fi
  grep -q '^### 1\.3' "$plan" || { echo "the header names research inputs, but the plan has no ### 1.3 section (plan-template.md, the skeleton)"; return 0; }
  ids="$(grep -oE '^\| `[a-z0-9-]+` \|' "$plan" | tr -d '|` ')"
  while IFS=$'\t' read -r src cases; do
    [ -n "$src" ] || continue
    case "${cases#\`}" in "not reachable:"*) continue;; esac   # the label may be in backticks
    found="$(echo "$cases" | grep -oE '`[a-z][a-z0-9-]*-[0-9]{2}`' | tr -d '`' | sort -u)"
    [ -n "$found" ] || { echo "the §1.3 row \`$src\` has no case id and no \`not reachable:\` (plan-template.md, the skeleton)"; continue; }
    for id in $found; do
      echo "$ids" | grep -qx "$id" || echo "§1.3 names \`$id\`, which is no case row of the plan (plan-template.md, the skeleton)"
    done
  done < <(awk '/^### 1\.3/ { f = 1; next } f && /^#/ { exit } f' "$plan" | hold_pipes | awk -F'|' '
    /^\|/ { if ($2 ~ /^ *(Source|-+|:?-+:?) *$/) next
            s = $2; gsub(/^ +| +$/, "", s); c = $(NF - 1); gsub(/^ +| +$/, "", c); print s "\t" c }' | give_pipes)
}
for plan in "$PLANS"/*-test-plan*.md; do
  [ -e "$plan" ] || continue
  while IFS= read -r p; do [ -n "$p" ] && problem "${plan#$DATA/}: $p"; done < <(plan_research "$plan")
done

if [ "$fail" = 0 ]; then echo "OK: layout checks passed"; fi
exit $fail
