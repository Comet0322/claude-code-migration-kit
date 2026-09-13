#!/usr/bin/env python3
"""依賴分析腳本：VB6 (.vbp / .bas / .cls / .frm)。

跟 migration-analyze 的契約：這支腳本是**預先寫好、隨這個 skill 一起打
包**的，來源語言是 VB6 時直接重用，不要在跑遷移的過程中臨時重寫一份
（見 `migration-analyze` 的「依賴圖：用腳本，不要用判斷力排序」節）。

做法：
1. 從 .vbp 檔案列出所有本地模組（Module=/Class=/Form=），COM 參考
   （Object=...; xxx.dll）視為外部私有套件，不排進依賴圖裡（依賴圖只管
   本地檔案之間的順序），但記進 `external-refs.tsv`——VB6 沒有逐檔宣告
   依賴的語法，`Object=` 是專案層級（整個 .vbp）的參考，不是特定某個
   .bas/.cls/.frm 檔案宣告的，所以這裡的 `source_path` 欄記的是 .vbp
   本身，不是呼叫端的檔案。是不是原生/標準庫、要不要納入 domain skill
   覆蓋範圍，是判斷不是事實，這支腳本不篩選、原樣列出，判斷交給
   migration-clarify。
2. 對每個本地模組檔案，掃描是否出現其他本地模組的名稱（呼叫其 Public
   Sub/Function、或 New 出其 class）當作邊：A -> B 表示 A 依賴 B。
   這是保守的字串比對啟發式，不是完整的 VB6 語法解析器——對於呼叫關係
   單純的批次程式已經足夠；如果之後遇到解析不出來的語法，交給
   units.tsv 的 risk_flag/risk_reason 欄標 high risk，不在這支腳本裡硬做
   完整 parser。
3. 拓樸排序；抓循環依賴分組。

輸出：
  migration/analysis/depmap/edges.tsv          (from, to)
  migration/analysis/depmap/order.txt          拓樸排序後的檔案路徑，一行一個
  migration/analysis/depmap/cycles.txt         循環依賴分組，一行一組（逗號分隔）
  migration/analysis/depmap/external-refs.tsv  (source_path, reference)——
    .vbp 裡的 `Object=` COM 參考，一列一筆

用法：
  python3 depmap_vb6.py <legacy 目錄> <輸出目錄>
  預設值分別是 "legacy"、"migration/analysis/depmap"。

自我測試：
  python3 .claude/skills/migration/scripts/depmap_vb6.py fixtures/dept200-vb6/legacy /tmp/depmap-dept200-vb6
  python3 .claude/skills/migration/scripts/depmap_vb6.py fixtures/dept300-vb6/legacy /tmp/depmap-dept300-vb6
"""
import glob
import os
import re
import sys
from collections import defaultdict, deque

ROOT = sys.argv[1] if len(sys.argv) > 1 else "legacy"
OUT_DIR = sys.argv[2] if len(sys.argv) > 2 else "migration/analysis/depmap"

os.makedirs(OUT_DIR, exist_ok=True)


def find_vbp():
    return glob.glob(os.path.join(ROOT, "**", "*.vbp"), recursive=True)


def parse_vbp_modules(vbp_path):
    """回傳這個 .vbp 裡列出的本地模組檔案相對路徑清單。"""
    base_dir = os.path.dirname(vbp_path)
    modules = []
    with open(vbp_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            m = re.match(r"(Module|Class|Form)=([^;]+);\s*(.+)$", line)
            if m:
                rel_file = m.group(3).strip()
                modules.append(os.path.normpath(os.path.join(base_dir, rel_file)))
    return modules


def parse_vbp_object_refs(vbp_path):
    """回傳這個 .vbp 裡列出的 COM 參考（Object= 那些行），原樣不篩選。"""
    refs = []
    with open(vbp_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if line.startswith("Object="):
                refs.append(line[len("Object="):].strip())
    return refs


def module_name_from_path(path):
    """讀檔案裡的 Attribute VB_Name，抓不到就用檔名。"""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                m = re.match(r'Attribute VB_Name = "(.+)"', line.strip())
                if m:
                    return m.group(1)
    except OSError:
        pass
    return os.path.splitext(os.path.basename(path))[0]


def main():
    vbp_files = find_vbp()
    if not vbp_files:
        print("no .vbp project files found under", ROOT, file=sys.stderr)

    all_modules = []  # (path, name)
    for vbp in vbp_files:
        for path in parse_vbp_modules(vbp):
            if os.path.exists(path):
                all_modules.append((path, module_name_from_path(path)))

    # 沒有 .vbp 或抓不到模組時，退回直接掃 legacy 目錄下的 .bas/.cls/.frm
    if not all_modules:
        for path in glob.glob(os.path.join(ROOT, "**", "*.[bB][aA][sS]"), recursive=True) + \
                     glob.glob(os.path.join(ROOT, "**", "*.[cC][lL][sS]"), recursive=True) + \
                     glob.glob(os.path.join(ROOT, "**", "*.[fF][rR][mM]"), recursive=True):
            all_modules.append((path, module_name_from_path(path)))

    name_to_path = {name: path for path, name in all_modules}
    edges = set()

    for path, name in all_modules:
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except OSError:
            content = ""
        for other_name, other_path in name_to_path.items():
            if other_path == path:
                continue
            # 字串邊界比對，避免子字串誤判 (例如 UserSync 在 UserSyncHelper 裡)
            if re.search(r"\b" + re.escape(other_name) + r"\b", content):
                edges.add((path, other_path))

    edges_path = os.path.join(OUT_DIR, "edges.tsv")
    with open(edges_path, "w", encoding="utf-8") as f:
        for a, b in sorted(edges):
            f.write(f"{a}\t{b}\n")

    external_refs = set()
    for vbp in vbp_files:
        for ref in parse_vbp_object_refs(vbp):
            external_refs.add((vbp, ref))

    external_refs_path = os.path.join(OUT_DIR, "external-refs.tsv")
    with open(external_refs_path, "w", encoding="utf-8") as f:
        for vbp, ref in sorted(external_refs):
            f.write(f"{vbp}\t{ref}\n")

    # 拓樸排序 + 循環偵測 (Tarjan SCC 簡化版：用 DFS 找環)
    graph = defaultdict(set)
    nodes = {p for p, _ in all_modules}
    for a, b in edges:
        graph[a].add(b)

    # Tarjan's SCC
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

        for w in graph.get(v, ()):
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
    for n in sorted(nodes):
        if n not in index:
            strongconnect(n)

    cycles = [scc for scc in sccs if len(scc) > 1]
    # 自環 (A 呼叫自己遞迴) 不算 unit 間循環，忽略
    cycle_groups = []
    node_to_cycle = {}
    for i, scc in enumerate(cycles):
        cycle_groups.append(scc)
        for n in scc:
            node_to_cycle[n] = i

    cycles_path = os.path.join(OUT_DIR, "cycles.txt")
    with open(cycles_path, "w", encoding="utf-8") as f:
        for scc in cycle_groups:
            f.write(",".join(sorted(scc)) + "\n")

    # 把循環內節點收縮成單一節點做拓樸排序
    def rep(n):
        return f"__cycle_{node_to_cycle[n]}__" if n in node_to_cycle else n

    collapsed_graph = defaultdict(set)
    collapsed_nodes = set()
    for n in nodes:
        collapsed_nodes.add(rep(n))
    for a, b in edges:
        ra, rb = rep(a), rep(b)
        if ra != rb:
            collapsed_graph[ra].add(rb)

    # 邊 a->b 表示 a 依賴 b：拓樸序要讓 b (被依賴者) 排在 a 前面
    # 反轉邊做 Kahn's algorithm
    rev_in_degree = defaultdict(int)
    rev_graph = defaultdict(set)
    for a in collapsed_graph:
        for b in collapsed_graph[a]:
            rev_graph[b].add(a)
            rev_in_degree[a] += 1
    for n in collapsed_nodes:
        rev_in_degree.setdefault(n, 0)

    queue = deque(sorted(n for n in collapsed_nodes if rev_in_degree[n] == 0))
    order = []
    seen = set()
    while queue:
        n = queue.popleft()
        if n in seen:
            continue
        seen.add(n)
        order.append(n)
        for m in sorted(rev_graph.get(n, ())):
            rev_in_degree[m] -= 1
            if rev_in_degree[m] == 0:
                queue.append(m)
    # 剩下沒排到的 (理論上不該發生，因為循環已收縮) 附加在最後
    for n in sorted(collapsed_nodes):
        if n not in seen:
            order.append(n)

    # 展開回真實檔案路徑
    expanded_order = []
    for n in order:
        if n.startswith("__cycle_"):
            idx = int(n[len("__cycle_"):-2])
            expanded_order.extend(sorted(cycle_groups[idx]))
        else:
            expanded_order.append(n)

    order_path = os.path.join(OUT_DIR, "order.txt")
    with open(order_path, "w", encoding="utf-8") as f:
        for p in expanded_order:
            f.write(p + "\n")

    print(f"modules={len(nodes)} edges={len(edges)} cycle_groups={len(cycle_groups)} "
          f"external_refs={len(external_refs)}")
    print(f"wrote {edges_path}, {order_path}, {cycles_path}, {external_refs_path}")


if __name__ == "__main__":
    main()
