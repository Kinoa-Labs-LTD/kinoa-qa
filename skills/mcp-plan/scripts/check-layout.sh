#!/usr/bin/env bash
# Mechanical checks for the mcp-plan / mcp-run skills and their data folder.
# Run from anywhere: bash <plugin>/skills/mcp-plan/scripts/check-layout.sh [<data folder>]
# (<plugin>/skills = the folder holding both skill folders; the script locates them from its own path.)
# <data folder> holds plans/ and reports/ and defaults to ~/.kinoa-qa/mcp; CI passes the eval
# fixture tree, <plugin>/skills/mcp-run/evals.
# Exit code 1 if any check fails, 2 on a usage error. Prints one line per problem.

set -u
usage() { echo "usage: bash check-layout.sh [<data folder>]"; exit 2; }
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
# Every table row is split on `|` through these two: hold_pipes turns each escaped `\|` into the
# byte $PIPE_HOLD so it stays inside its cell, give_pipes turns it back on the way out.
# Usage: hold_pipes [<file>] | awk -F'|' '…' | give_pipes
PIPE_HOLD="$(printf '\037')"
hold_pipes() { sed "s/\\\\|/$PIPE_HOLD/g" "$@"; }
give_pipes() { sed "s/$PIPE_HOLD/\\\\|/g"; }

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

# 3. Report file names carry a UTC stamp. Whether a report was edited in place cannot be checked
#    here, so only the name shape is.
for report in "$REPORTS"/*-test-report-*.md; do
  [ -e "$report" ] || continue
  [[ "$(basename "$report")" =~ -test-report-[0-9]{8}-[0-9]{4}\.md$ ]] || problem "bad report name: $(basename "$report")"
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
  for rep in $(sed -n '1,/^## 0\./p' "$plan" | grep -oE 'KING-[0-9]+-[a-z-]+-test-report-[0-9]{8}-[0-9]{4}\.md' | sort -u); do
    [ -f "$REPORTS/$rep" ] || { echo "earlier run $rep is not in $REPORTS/"; continue; }
    hhmm="${rep%.md}"; hhmm="${hhmm##*-}"
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

if [ "$fail" = 0 ]; then echo "OK: layout checks passed"; fi
exit $fail
