#!/usr/bin/env python3
"""依賴分析腳本：Delphi (.pas)。

跟 migration-analyze 的契約：這支腳本是**預先寫好、隨這個 skill 一起打
包**的，來源語言是 Delphi 時直接重用，不要在跑遷移的過程中臨時重寫一份
（見 `migration-analyze` 的「依賴圖：用腳本，不要用判斷力排序」節）。

做法：
1. 掃 ROOT 底下所有 .pas 檔案當本地模組節點——Delphi 的 unit 一個檔案一
   個，`.pas` 副檔名本身就是夠可靠的訊號，不像 VB6 需要另外讀 .vbp 才知
   道有哪些本地模組。`.dpr` 進入點檔案本身不當節點，只是應用程式的組裝
   點，不是可重用的「單元」。
2. 讀每個 .pas 檔案裡的 `unit <Name>;` 宣告取得這個檔案的單元名稱，抓不
   到就用檔名（去掉副檔名）代替。
3. 解析每個檔案裡全部 `uses ... ;` 子句（interface/implementation 各自
   可能各有一個，都要抓，不能只抓第一個）取得這個檔案宣告依賴的單元名
   稱清單，逐一比對是否為本地模組——是本地模組就記一條邊 A -> B（A 依
   賴 B）；不是本地模組（標準庫如 SysUtils/Classes/IniFiles，或私有套
   件的外部 COM DLL）就記進 `external-refs.tsv`，**原生標準庫跟私有套件
   一律不分類、原樣全部記下來**——這兩者的邊界本身是判斷，不是事實，判
   斷交給 migration-clarify 讀這份檔案時用它對來源語言的知識去篩，這支
   腳本只負責把「解析不到本地檔案的引用」如實列出來，不做篩選、不猜測
   哪些重要哪些不重要。
   這是保守的 `uses` 子句擷取（先把 `//` 行註解跟 `{...}` 區塊註解拿
   掉，再抓 `uses ... ;`），不是完整的 Delphi 語法解析器——條件式編譯
   （`{$IFDEF}`）之類的邊角案例抓不到時，交給 units.tsv 的 risk_flag/
   risk_reason 欄標 high risk，不在這支腳本裡硬做完整 parser。
4. 拓樸排序；抓循環依賴分組（跟 depmap_vb6.py 同一套演算法）。

輸出：跟 depmap_vb6.py 同一份契約：
  migration/analysis/depmap/edges.tsv          (from, to)
  migration/analysis/depmap/order.txt          拓樸排序後的檔案路徑，一行一個
  migration/analysis/depmap/cycles.txt         循環依賴分組，一行一組（逗號分隔）
  migration/analysis/depmap/external-refs.tsv  (source_path, reference)——
    這個檔案引用了哪個解析不到本地檔案的識別字，一列一筆，同一個
    reference 出現在很多檔案就會有很多列（migration-clarify 用列數當出
    現次數的證據）

用法：
  python3 depmap_delphi.py <legacy 目錄> <輸出目錄>
  預設值分別是 "legacy"、"migration/analysis/depmap"。

自我測試：
  python3 .claude/skills/migration/scripts/depmap_delphi.py fixtures/dept200-delphi/legacy /tmp/depmap-dept200-delphi
"""
import glob
import os
import re
import sys
from collections import defaultdict, deque

ROOT = sys.argv[1] if len(sys.argv) > 1 else "legacy"
OUT_DIR = sys.argv[2] if len(sys.argv) > 2 else "migration/analysis/depmap"

os.makedirs(OUT_DIR, exist_ok=True)

UNIT_NAME_RE = re.compile(r"^\s*unit\s+([A-Za-z_][A-Za-z0-9_.]*)\s*;", re.IGNORECASE | re.MULTILINE)
USES_CLAUSE_RE = re.compile(r"\buses\b(.*?);", re.IGNORECASE | re.DOTALL)
LINE_COMMENT_RE = re.compile(r"//.*")
BLOCK_COMMENT_RE = re.compile(r"\{.*?\}", re.DOTALL)


def strip_comments(content):
    content = BLOCK_COMMENT_RE.sub(" ", content)
    content = LINE_COMMENT_RE.sub("", content)
    return content


def find_pas():
    return sorted(glob.glob(os.path.join(ROOT, "**", "*.[pP][aA][sS]"), recursive=True))


def unit_name_from_content(path, content):
    m = UNIT_NAME_RE.search(content)
    if m:
        return m.group(1)
    return os.path.splitext(os.path.basename(path))[0]


def parse_uses(content):
    """回傳這個檔案全部 uses 子句裡列出的識別字（可能跨 interface/
    implementation 兩個子句），去除前後空白。"""
    names = []
    for clause in USES_CLAUSE_RE.findall(content):
        for part in clause.split(","):
            name = part.strip()
            if name:
                names.append(name)
    return names


def main():
    pas_files = find_pas()
    if not pas_files:
        print("no .pas files found under", ROOT, file=sys.stderr)

    contents = {}
    for path in pas_files:
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                contents[path] = strip_comments(f.read())
        except OSError:
            contents[path] = ""

    name_to_path = {}
    for path, content in contents.items():
        name = unit_name_from_content(path, content)
        name_to_path[name.lower()] = path

    edges = set()
    external_refs = set()
    for path, content in contents.items():
        for used in parse_uses(content):
            target = name_to_path.get(used.lower())
            if target and target != path:
                edges.add((path, target))
            elif not target:
                external_refs.add((path, used))

    edges_path = os.path.join(OUT_DIR, "edges.tsv")
    with open(edges_path, "w", encoding="utf-8") as f:
        for a, b in sorted(edges):
            f.write(f"{a}\t{b}\n")

    external_refs_path = os.path.join(OUT_DIR, "external-refs.tsv")
    with open(external_refs_path, "w", encoding="utf-8") as f:
        for path, ref in sorted(external_refs):
            f.write(f"{path}\t{ref}\n")

    # 拓樸排序 + 循環偵測 (Tarjan SCC 簡化版：用 DFS 找環)——跟 depmap_vb6.py 同一套
    nodes = set(contents.keys())
    graph = defaultdict(set)
    for a, b in edges:
        graph[a].add(b)

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
    for n in sorted(collapsed_nodes):
        if n not in seen:
            order.append(n)

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
