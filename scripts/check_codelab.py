#!/usr/bin/env python3
"""Check that every ```python block in the codelab is taken from
codelab-complete/agents/*/agent.py: its lines appear in one agent.py, in order.
Blank lines and trailing spaces are ignored, so a block may skip lines of the
source (shortened descriptions) but may not change or add any.

usage: check_codelab.py [CODELAB.md]
"""
import glob
import re
import sys

md_path = sys.argv[1] if len(sys.argv) > 1 else "codelab/building-a-multi-agent-system-adk2.md"


def read(path):
    with open(path) as f:
        return f.read()


md = read(md_path)
sources = {
    p: [line.rstrip() for line in read(p).splitlines() if line.strip()]
    for p in sorted(glob.glob("codelab-complete/agents/*/agent.py"))
}


def in_order(block, src):
    """Return the first block line that cannot be matched in order, or None."""
    i = 0
    for line in block:
        while i < len(src) and src[i] != line:
            i += 1
        if i == len(src):
            return line
        i += 1
    return None


failed = 0
blocks = re.findall(r"```python\n(.*?)```", md, re.DOTALL)
for n, text in enumerate(blocks, 1):
    block = [line.rstrip() for line in text.splitlines() if line.strip()]
    misses = {p: in_order(block, src) for p, src in sources.items()}
    match = [p for p, miss in misses.items() if miss is None]
    if match:
        print(f"ok    block {n} ({len(block)} lines) in {match[0]}")
    else:
        failed += 1
        print(f"FAIL  block {n} starting {block[0]!r}: no agent.py has it")
        for p, miss in misses.items():
            print(f"        {p}: first unmatched line {miss!r}")

print(f"{len(blocks) - failed} of {len(blocks)} python blocks match codelab-complete")
sys.exit(1 if failed or not blocks else 0)
