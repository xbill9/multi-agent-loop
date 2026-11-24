#!/bin/bash
# PostToolUse (Write|Edit): ruff check an edited .py file and report only if the
# edit added findings compared with the committed version (vendored upstream code
# already has some). Exit 2 sends the findings back to Claude.
f=$(jq -r '.tool_input.file_path // .tool_response.filePath')
case "$f" in *.py) ;; *) exit 0 ;; esac
[ -f "$f" ] || exit 0
cd "$(dirname "$f")" || exit 0
rel=$(git ls-files --full-name -- "$f" 2>/dev/null)

count() { grep -c ': [A-Z]\+[0-9]\+' || true; }
after_out=$(ruff check --quiet --output-format concise "$f" 2>&1)
after=$(printf '%s\n' "$after_out" | count)
before=0
if [ -n "$rel" ]; then
  before=$(git show "HEAD:$rel" 2>/dev/null | ruff check --quiet --output-format concise --stdin-filename "$f" - 2>&1 | count)
fi
if [ "$after" -gt "$before" ]; then
  echo "ruff: $f has $after findings, $before before this edit:" >&2
  printf '%s\n' "$after_out" | head -20 >&2
  exit 2
fi
exit 0
