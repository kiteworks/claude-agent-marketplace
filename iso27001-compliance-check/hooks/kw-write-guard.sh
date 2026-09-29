#!/bin/sh
# kw-write-guard.sh: plugin-level PreToolUse hook for the Write tool (#307).
#
# Report-saving agents may use Write so they never have to push report text
# through a heredoc, printf or a Python one-liner (apostrophes, < and >,
# non-ASCII text and the Windows command-length limit break those and have
# changed delivered report text). This hook narrows Write to report staging
# files: for THIS plugin's agents a write is allowed only when tool_input's
# file_path, with backslashes read as slashes,
#   - sits directly in a folder named exactly _kiteworks-report,
#   - has no ".." segment and no ":" in the file name, and
#   - ends in .json, .csv, .txt or .md.
# Everything else is denied. The main thread and other plugins' agents pass.
#
# stdin: the hook payload (JSON). exit 0 = allow; exit 2 = deny, one line on
# stderr for the model. POSIX sh + one awk pass, like kw-allowlist.sh. The
# common case (main thread: no "agent_type" in the payload) exits before
# spawning anything.

set -u
payload=$(cat)
case $payload in *'"agent_type"'*) ;; *) exit 0 ;; esac

# Directory of this script; see kw-allowlist.sh for why backslashes are
# turned into slashes by hand (bs is a literal backslash).
bs=$(printf '\134')
here=""; rest=$0
while case $rest in *"$bs"*) true ;; *) false ;; esac; do
  here="$here${rest%%"$bs"*}/"; rest=${rest#*"$bs"}
done
here="$here$rest"
case $here in */*) here=${here%/*} ;; *) here=. ;; esac
allowlist="$here/allowlist.json"
manifest="$here/../.claude-plugin/plugin.json"

# One awk pass: the first TOP-LEVEL "tool_name" and "agent_type" string values
# and the "file_path" string directly inside the top-level "tool_input" object.
# The same depth-tracking scan as kw-allowlist.sh, so keys nested deeper (or
# escaped text inside a string) never decide. The path is JSON-decoded for
# \\ and \/ only; any other escape (\u, \n, \", ...) could hide a separator or
# a ".." segment from the checks below, so it is reported as "bad" instead.
parsed=$(printf '%s' "$payload" | LC_ALL=C awk '
  { buf = buf $0 "\n" }
  END {
    bsl = "\134"; n = length(buf); depth = 0; want = 0; kd = 0; inti = 0; i = 1
    while (i <= n) {
      c = substr(buf, i, 1)
      if (c == "\"") {
        start = ++i
        while (i <= n) {
          c = substr(buf, i, 1)
          if (c == bsl) { i += 2; continue }
          if (c == "\"") break
          i++
        }
        s = substr(buf, start, i - start); i++
        if (want) {
          if (kd == 1 && k == "tool_name" && !("t" in v)) v["t"] = s
          if (kd == 1 && k == "agent_type" && !("a" in v)) v["a"] = s
          if (kd == 2 && k == "file_path" && !("p" in v)) v["p"] = s
          want = 0; continue
        }
        j = i
        while (j <= n && index(" \t\r\n", substr(buf, j, 1))) j++
        if ((depth == 1 || (depth == 2 && inti)) && substr(buf, j, 1) == ":") {
          k = s; kd = depth; want = 1; i = j + 1
        }
        continue
      }
      if (c == "{" || c == "[") {
        depth++
        if (c == "{" && want && depth == 2 && kd == 1 && k == "tool_input") inti = 1
        want = 0
      }
      else if (c == "}" || c == "]") { if (--depth < 2) inti = 0; if (depth < 1) break }
      else if (!index(" \t\r\n,", c)) want = 0
      i++
    }
    raw = v["p"]; path = ""; bad = 0; m = length(raw); i = 1
    while (i <= m) {
      c = substr(raw, i, 1)
      if (c == bsl) {
        e = substr(raw, i + 1, 1)
        if (e == bsl || e == "/") path = path e
        else bad = 1
        i += 2; continue
      }
      path = path c; i++
    }
    if (!("p" in v)) bad = 1
    print v["t"]; print v["a"]; print bad; print path
  }')
{
  IFS= read -r tool
  IFS= read -r agent
  IFS= read -r bad
  IFS= read -r path
} <<EOF
$parsed
EOF

[ -n "$agent" ] || exit 0                    # main thread: not this hook's business
[ "$tool" = Write ] || exit 0

# Is the agent ours? "<plugin>:<agent>" is ours when the prefix is the top-level
# "name" of our manifest; an unprefixed name (or a prefixed one when the
# manifest is unreadable) only when hooks/allowlist.json lists it. Anything else
# (a built-in subagent, another plugin's agent) is left alone.
stem=${agent##*:}; own=""
if [ -f "$manifest" ]; then
  while IFS= read -r line; do
    case $line in '  "name": "'*) own=${line#*: \"}; own=${own%%\"*}; break ;; esac
  done < "$manifest"
fi
ours=0
case $agent in
  *:*) prefix=${agent%:*}
       if [ -n "$own" ]; then
         [ "$prefix" = "$own" ] || exit 0
         ours=1
       fi ;;
esac
if [ $ours = 0 ] && [ -f "$allowlist" ]; then
  while IFS= read -r line; do
    [ "$line" = "  \"$stem\": {" ] && { ours=1; break; }
  done < "$allowlist"
fi
[ $ours = 1 ] || exit 0

deny() {
  printf 'kw-write-guard: agents may only write report staging files (.../_kiteworks-report/*.json|csv|txt|md); agent %s may not write "%s": %s.\n' "$stem" "$path" "$1" >&2
  exit 2
}

[ "$bad" = 0 ] || deny "the path is missing or uses a JSON escape other than \\\\ and \\/"
[ -n "$path" ] || deny "the path is empty"

# Backslashes to slashes (Windows paths), pure sh.
norm=""; rest=$path
while case $rest in *"$bs"*) true ;; *) false ;; esac; do
  norm="$norm${rest%%"$bs"*}/"; rest=${rest#*"$bs"}
done
norm="$norm$rest"

case "/$norm/" in */../*) deny "it has a .. segment" ;; esac
case $norm in */*) ;; *) deny "it is not inside a _kiteworks-report folder" ;; esac
name=${norm##*/}
dir=${norm%/*}
[ "${dir##*/}" = _kiteworks-report ] || deny "it is not directly inside a _kiteworks-report folder"
case $name in *:*) deny "the file name contains a colon" ;; esac
case $name in
  ?*.json|?*.csv|?*.txt|?*.md) exit 0 ;;
esac
deny "only .json, .csv, .txt and .md files may be written"
