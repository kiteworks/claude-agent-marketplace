#!/bin/sh
# kw-allowlist.sh: plugin-level PreToolUse hook (Claude Code >= 2.1.258).
#
# Agent frontmatter can only allow an MCP tool by its full mcp__<server>__<tool>
# name, which pins the server name the user gave the Kiteworks connector. The
# marketplace therefore lists each agent's Kiteworks tools in hooks/allowlist.json
# and this hook enforces that list for ANY server whose name contains "kiteworks"
# (case-insensitive) or is a bare connection UUID (see below), denying every other
# MCP server. It judges only THIS plugin's
# agents: the main thread and other plugins' agents pass through (exit 0).
#
# stdin: the hook payload (JSON). exit 0 = allow; exit 2 = deny, one line on
# stderr for the model. POSIX sh + one awk pass; no bash, jq, sed, tr or python.
# Every installed plugin's copy runs on every MCP call, so the common case (main
# thread: no "agent_type" in the payload) exits before spawning anything.

set -u
payload=$(cat)
case $payload in *'"agent_type"'*) ;; *) exit 0 ;; esac

# Directory of this script. Claude Code may hand us a Windows path with
# backslashes, which dirname would not split, so turn them into slashes first
# (bs is a literal backslash; pure sh, no sed or tr).
bs=$(printf '\134')
here=""; rest=$0
while case $rest in *"$bs"*) true ;; *) false ;; esac; do
  here="$here${rest%%"$bs"*}/"; rest=${rest#*"$bs"}
done
here="$here$rest"
case $here in */*) here=${here%/*} ;; *) here=. ;; esac
allowlist="$here/allowlist.json"
manifest="$here/../.claude-plugin/plugin.json"

# One awk pass over the payload: the first TOP-LEVEL "tool_name" and
# "agent_type" string values, plus the tool's server segment (lowercased) and
# bare name, split on the LAST "__" because server names may contain "__".
# A small depth-tracking scan, so the same keys nested inside tool_input (as
# real keys or as escaped text inside a string) can never decide, whatever the
# key order or formatting of the payload. Prints five lines; the last is the
# server classification: kiteworks / uuid / other.
#
# UUID servers are admitted because Claude Desktop mounts claude.ai directory
# connectors under their connection id (mcp__<uuid>__<tool>, upstream issue
# anthropics/claude-code#77598), so a Kiteworks connector added that way carries
# no "kiteworks" in its name; the agents' connector-probe skill identifies
# Kiteworks by its tool fingerprint instead. Residual risk: a same-named generic
# tool on another UUID-named connector; accepted by the developer 2026-09-20.
parsed=$(printf '%s' "$payload" | LC_ALL=C awk '
  { buf = buf $0 "\n" }
  END {
    bsl = "\134"; n = length(buf); depth = 0; want = 0; i = 1
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
          if (k == "tool_name" && !("t" in v)) v["t"] = s
          if (k == "agent_type" && !("a" in v)) v["a"] = s
          if (("t" in v) && ("a" in v)) break
          want = 0; continue
        }
        j = i
        while (j <= n && index(" \t\r\n", substr(buf, j, 1))) j++
        if (depth == 1 && substr(buf, j, 1) == ":") { k = s; want = 1; i = j + 1 }
        continue
      }
      if (c == "{" || c == "[") { depth++; want = 0 }
      else if (c == "}" || c == "]") { if (--depth < 1) break }
      else if (!index(" \t\r\n,", c)) want = 0
      i++
    }
    tool = v["t"]; server = ""; bare = ""; kind = "other"
    if (index(tool, "mcp__") == 1) {
      rest = substr(tool, 6); bare = rest; sub(/.*__/, "", bare)
      server = tolower(substr(rest, 1, length(rest) - length(bare) - 2))
      if (index(server, "kiteworks")) kind = "kiteworks"
      else if (split(server, g, "-") == 5 && length(g[1]) == 8 && length(g[2]) == 4 && length(g[3]) == 4 && length(g[4]) == 4 && length(g[5]) == 12 && server ~ /^[0-9a-f-]*$/) kind = "uuid"
    }
    print tool; print v["a"]; print server; print bare; print kind
  }')
{
  IFS= read -r tool
  IFS= read -r agent
  IFS= read -r server
  IFS= read -r bare
  IFS= read -r kind
} <<EOF
$parsed
EOF

[ -n "$agent" ] || exit 0                    # main thread: not this hook's business
case $tool in mcp__*) ;; *) exit 0 ;; esac

deny() {
  printf 'kw-allowlist: agent %s may not call %s: %s. Allowed Kiteworks tools for this agent are listed in hooks/allowlist.json of its plugin.\n' "$agent" "$tool" "$1" >&2
  exit 2
}

# "<plugin>:<agent>": another plugin's agent is not ours to judge. The plugin
# name is the top-level "name" of our manifest (indent 2; author.name is deeper).
attributed=0; unprefixed=0
case $agent in
  *:*)
    prefix=${agent%:*}; agent=${agent##*:}; own=""
    if [ -f "$manifest" ]; then
      while IFS= read -r line; do
        case $line in '  "name": "'*) own=${line#*: \"}; own=${own%%\"*}; break ;; esac
      done < "$manifest"
    fi
    [ -n "$own" ] && [ "$prefix" != "$own" ] && exit 0
    [ "$prefix" = "$own" ] && attributed=1
    ;;
  *) unprefixed=1 ;;
esac

# Our own agent (or an unprefixed name) with no allowlist at all: fail closed.
[ -f "$allowlist" ] || {
  [ $attributed = 1 ] || [ $unprefixed = 1 ] || exit 0
  deny "hooks/allowlist.json is missing from its plugin"
}

# Pure-sh lookup in the marketplace-written allowlist (json.dumps indent=2: one
# agent key per line, one tool per line). known = agent listed; found = tool listed.
known=0; found=0; inlist=0
while IFS= read -r line; do
  if [ $known = 0 ]; then
    [ "$line" = "  \"$agent\": {" ] && known=1
    continue
  fi
  case $line in
    '  }'|'  },') break ;;
    '    "kiteworks": ['*) inlist=1; case $line in *']'*) inlist=0 ;; esac ;;
    '    ]'*) inlist=0 ;;
    *) if [ $inlist = 1 ]; then
         v=${line#*\"}; v=${v%%\"*}
         [ "$v" = "$bare" ] && { found=1; break; }
       fi ;;
  esac
done < "$allowlist"

if [ $known = 0 ]; then
  [ $attributed = 1 ] || exit 0              # cannot attribute: leave it alone
  deny "it is not listed in hooks/allowlist.json"
fi
case $kind in
  kiteworks|uuid) ;;
  *) deny "server \"$server\" is not a Kiteworks connector" ;;
esac
[ $found = 1 ] && exit 0
deny "\"$bare\" is not in this agent's allowlist"
