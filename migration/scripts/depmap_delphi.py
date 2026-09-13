#!/usr/bin/env python3
"""
Delphi dependency map generator.

Parses `uses` clauses (interface + implementation, and .dpr programs) in a
directory of .pas/.dpr files, builds a file-level dependency graph limited to
local units (units that exist as a file in the scanned directory), and emits:

  edges.tsv    from<TAB>to        (from depends on to)
  order.txt    topological order of source files, one per line
  cycles.txt   groups of files involved in a dependency cycle, one group per
               line, tab-separated; empty file if no cycles

Usage:
  python3 depmap_delphi.py <source_dir> <output_dir>
"""
import os
import re
import sys
from collections import defaultdict, deque


def find_unit_name(path):
    text = read_text(path)
    m = re.search(r'^\s*(unit|program)\s+([A-Za-z_][A-Za-z0-9_]*)\s*;', text, re.IGNORECASE | re.MULTILINE)
    if m:
        return m.group(2)
    return os.path.splitext(os.path.basename(path))[0]


def read_text(path):
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        return f.read()


def strip_comments(text):
    text = re.sub(r'\{.*?\}', '', text, flags=re.DOTALL)
    text = re.sub(r'\(\*.*?\*\)', '', text, flags=re.DOTALL)
    text = re.sub(r'//[^\n]*', '', text)
    return text


def find_uses_clauses(text):
    names = set()
    for m in re.finditer(r'\buses\b(.*?);', text, re.IGNORECASE | re.DOTALL):
        clause = m.group(1)
        for ident in re.split(r',', clause):
            ident = ident.strip()
            ident = re.sub(r'\s+in\s+.*$', '', ident, flags=re.IGNORECASE)
            ident = ident.strip()
            if ident:
                names.add(ident)
    return names


def main():
    if len(sys.argv) != 3:
        print(f"usage: {sys.argv[0]} <source_dir> <output_dir>", file=sys.stderr)
        sys.exit(1)

    source_dir, output_dir = sys.argv[1], sys.argv[2]
    os.makedirs(output_dir, exist_ok=True)

    files = []
    for root, _, filenames in os.walk(source_dir):
        for fn in filenames:
            if fn.lower().endswith(('.pas', '.dpr')):
                files.append(os.path.join(root, fn))
    files.sort()

    unit_to_file = {}
    for path in files:
        unit_to_file[find_unit_name(path).lower()] = path

    edges = []
    deps_by_file = defaultdict(set)
    for path in files:
        raw = read_text(path)
        text = strip_comments(raw)
        used = find_uses_clauses(text)
        for u in used:
            target = unit_to_file.get(u.lower())
            if target and target != path:
                edges.append((path, target))
                deps_by_file[path].add(target)

    def rel(p):
        return os.path.relpath(p, source_dir)

    with open(os.path.join(output_dir, 'edges.tsv'), 'w', encoding='utf-8') as f:
        for a, b in sorted(edges, key=lambda e: (rel(e[0]), rel(e[1]))):
            f.write(f"{rel(a)}\t{rel(b)}\n")

    # Tarjan's SCC to find cycles among local files
    index_counter = [0]
    stack = []
    lowlink = {}
    index = {}
    on_stack = {}
    sccs = []

    def strongconnect(v):
        index[v] = index_counter[0]
        lowlink[v] = index_counter[0]
        index_counter[0] += 1
        stack.append(v)
        on_stack[v] = True

        for w in deps_by_file.get(v, ()):
            if w not in index:
                strongconnect(w)
                lowlink[v] = min(lowlink[v], lowlink[w])
            elif on_stack.get(w):
                lowlink[v] = min(lowlink[v], index[w])

        if lowlink[v] == index[v]:
            scc = []
            while True:
                w = stack.pop()
                on_stack[w] = False
                scc.append(w)
                if w == v:
                    break
            sccs.append(scc)

    sys.setrecursionlimit(10000)
    for f in files:
        if f not in index:
            strongconnect(f)

    cycles = [scc for scc in sccs if len(scc) > 1]
    # self-loop check (file depends on itself directly) - not expected for uses clauses, skip

    with open(os.path.join(output_dir, 'cycles.txt'), 'w', encoding='utf-8') as f:
        for scc in cycles:
            f.write('\t'.join(sorted(rel(p) for p in scc)) + '\n')

    # Build condensation graph over SCCs for topological order
    file_to_scc = {}
    for i, scc in enumerate(sccs):
        for f in scc:
            file_to_scc[f] = i

    scc_deps = defaultdict(set)
    indegree = defaultdict(int)
    for i in range(len(sccs)):
        indegree[i] = 0
    for a, b in edges:
        sa, sb = file_to_scc[a], file_to_scc[b]
        if sa != sb and sb not in scc_deps[sa]:
            scc_deps[sa].add(sb)

    for sa, targets in scc_deps.items():
        for sb in targets:
            indegree[sb] += 1

    # a depends on b means b must come first -> edge b -> a in build order graph
    order_deps = defaultdict(set)
    order_indegree = defaultdict(int)
    for i in range(len(sccs)):
        order_indegree[i] = 0
    for sa, targets in scc_deps.items():
        for sb in targets:
            order_deps[sb].add(sa)
    for sb, targets in order_deps.items():
        for sa in targets:
            order_indegree[sa] += 1

    queue = deque(sorted(
        [i for i in range(len(sccs)) if order_indegree[i] == 0],
        key=lambda i: min(rel(p) for p in sccs[i])
    ))
    topo_scc = []
    seen = set()
    while queue:
        i = queue.popleft()
        if i in seen:
            continue
        seen.add(i)
        topo_scc.append(i)
        nxt = sorted(order_deps.get(i, ()), key=lambda j: min(rel(p) for p in sccs[j]))
        for j in nxt:
            order_indegree[j] -= 1
            if order_indegree[j] == 0:
                queue.append(j)

    with open(os.path.join(output_dir, 'order.txt'), 'w', encoding='utf-8') as f:
        for i in topo_scc:
            for p in sorted(sccs[i], key=rel):
                f.write(rel(p) + '\n')

    print(f"files={len(files)} edges={len(edges)} cycles={len(cycles)}")


if __name__ == '__main__':
    main()
