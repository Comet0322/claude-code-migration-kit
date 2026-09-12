#!/usr/bin/env python3
"""Deterministic dependency mapper for a flat Delphi/Object Pascal unit tree.

Parses `uses A, B, C;` clauses (interface and implementation sections both
scanned) and resolves each name against the set of local unit names found in
the source directory (external units like SysUtils are ignored).

Usage: depmap_pascal.py <source_dir> <output_dir>
Writes: edges.tsv, order.txt, cycles.txt (same format as depmap_python.py).
"""
import re
import sys
from pathlib import Path

USES_RE = re.compile(r"\buses\b(.*?);", re.IGNORECASE | re.DOTALL)


def local_units(src_dir: Path):
    return {p.stem: p for p in src_dir.glob("*.pas")}


def parse_edges(units: dict):
    edges = []
    for name, path in units.items():
        text = path.read_text()
        for m in USES_RE.finditer(text):
            names = [n.strip() for n in m.group(1).split(",")]
            for n in names:
                if n in units and n != name:
                    edges.append((name, n))
    return sorted(set(edges))


def topo_order_with_cycles(units, edges):
    graph = {u: set() for u in units}
    for a, b in edges:
        graph[a].add(b)

    visited, order, cycles = set(), [], []

    def visit(node, path):
        if node in path:
            cyc = path[path.index(node):] + [node]
            group = sorted(frozenset(cyc[:-1]))
            if group not in cycles:
                cycles.append(group)
            return
        if node in visited:
            return
        visited.add(node)
        for dep in graph[node]:
            visit(dep, path + [node])
        order.append(node)

    for u in units:
        visit(u, [])
    return order, cycles


def main():
    src_dir = Path(sys.argv[1])
    out_dir = Path(sys.argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)

    units = local_units(src_dir)
    edges = parse_edges(units)
    order, cycles = topo_order_with_cycles(units, edges)

    (out_dir / "edges.tsv").write_text(
        "\n".join(f"{a}\t{b}" for a, b in edges) + ("\n" if edges else "")
    )
    (out_dir / "order.txt").write_text("\n".join(order) + "\n")
    (out_dir / "cycles.txt").write_text(
        "\n".join(",".join(c) for c in cycles) + ("\n" if cycles else "")
    )
    print(f"units={len(units)} edges={len(edges)} cycles={len(cycles)}")


if __name__ == "__main__":
    main()
