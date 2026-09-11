#!/usr/bin/env python3
"""Deterministic dependency mapper for a flat Python source tree.

Parses `import X` / `from X import ...` at module scope, resolves X against
the set of local module names found in the source directory (anything not
matching a local module is treated as external and ignored — this migration
kit only orders *this codebase's own* files).

Usage: depmap_python.py <source_dir> <output_dir>
Writes: edges.tsv (from<TAB>to), order.txt (topological order, one path per
line, cycle members grouped on the same line separated by ','), cycles.txt
(one line per cycle, module names separated by ',').
"""
import re
import sys
from pathlib import Path

IMPORT_RE = re.compile(r"^\s*(?:from\s+(\S+)\s+import|import\s+(\S+))")


def local_modules(src_dir: Path):
    return {p.stem: p for p in src_dir.glob("*.py")}


def parse_edges(modules: dict):
    edges = []
    for name, path in modules.items():
        for line in path.read_text().splitlines():
            m = IMPORT_RE.match(line)
            if not m:
                continue
            target = (m.group(1) or m.group(2)).split(".")[0]
            if target in modules and target != name:
                edges.append((name, target))
    return edges


def topo_order_with_cycles(modules, edges):
    graph = {m: set() for m in modules}
    for a, b in edges:
        graph[a].add(b)

    visited, order, cycles = set(), [], []

    def visit(node, path):
        if node in path:
            cyc = path[path.index(node):] + [node]
            group = frozenset(cyc[:-1])
            if group not in [frozenset(c) for c in cycles]:
                cycles.append(sorted(group))
            return
        if node in visited:
            return
        visited.add(node)
        for dep in graph[node]:
            visit(dep, path + [node])
        order.append(node)

    for m in modules:
        visit(m, [])
    return order, cycles


def main():
    src_dir = Path(sys.argv[1])
    out_dir = Path(sys.argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)

    modules = local_modules(src_dir)
    edges = parse_edges(modules)
    order, cycles = topo_order_with_cycles(modules, edges)

    (out_dir / "edges.tsv").write_text(
        "\n".join(f"{a}\t{b}" for a, b in edges) + ("\n" if edges else "")
    )
    (out_dir / "order.txt").write_text("\n".join(order) + "\n")
    (out_dir / "cycles.txt").write_text(
        "\n".join(",".join(c) for c in cycles) + ("\n" if cycles else "")
    )
    print(f"modules={len(modules)} edges={len(edges)} cycles={len(cycles)}")


if __name__ == "__main__":
    main()
