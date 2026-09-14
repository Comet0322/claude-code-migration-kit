#!/usr/bin/env python3
"""依賴分析腳本：Delphi (.pas)。

跟 migration-analyze 的契約：這支腳本是**預先寫好、隨這個 skill 一起打
包**的，來源語言是 Delphi 時直接重用，不要在跑遷移的過程中臨時重寫一份
（見 `migration-analyze` 的「依賴圖：用腳本，不要用判斷力排序」節）。

做法：
1. 掃 ROOT 底下所有 .pas 檔案，讀每個檔案裡的 `unit <Name>;` 宣告取得單
   元名稱（抓不到就用檔名代替），建立「單元名稱 → 檔案路徑」的全域對照
   表——這一步只是為了之後能把 `uses` 子句裡的識別字解析回檔案路徑，本
   身不代表這些檔案都會被納入分析範圍（見步驟 2）。
2. **可達性分析，只納入真的被進入點用到的檔案**：從 ROOT 底下每個 `.dpr`
   進入點檔案自己的 `uses` 子句當起點（`.dpr` 本身不是可重用的「單元」，
   但它是應用程式實際組裝、真正決定「哪些檔案被編進這個程式」的地方，
   不能不讀），沿著每個已解析到的本地單元自己的 `uses` 子句遞迴展開。
   只有從進入點走得到的 `.pas` 檔案才當本地模組節點——ROOT 底下存在、但
   從 `.dpr` 走不到的檔案（棄用的實驗性程式碼、複製留下的舊版本……）不
   計入分析範圍，不會被誤判成需要遷移的 unit，也不會讓它們自己內部瞎猜
   的依賴污染 `external-refs.tsv`。找不到任何 `.dpr` 時（理論上不該發
   生，防禦性地）退回舊行為：ROOT 底下掃到的 `.pas` 全部當本地模組。
   每個 `.dpr` 各自展開一次（不是合成一個共用起點），這樣才能個別算出
   「這個進入點自己可達到幾個檔案」寫進 `entry-points.tsv`：ROOT 底下有
   一個以上的 `.dpr` 時，這支腳本會把所有進入點各自可達的集合取聯集
   （沒有足夠資訊判斷某個 `.dpr` 是不是其實沒被真的建置過——那是人的知
   識，不是能從原始碼推論的事實），但同時把每個進入點各自可達到幾個檔
   案列出來，交給 migration-clarify/人確認每一個是不是真的都屬於這次
   遷移範圍，而不是有一個其實是離群的舊/棄用進入點。
   同一個單元名稱如果在掃描範圍內對到不只一個檔案（新舊備份版本、真實
   專案裡靠搜尋路徑優先序決定用哪一份的情況——這支腳本沒有專案的搜尋路
   徑設定可用，無法真正判斷該用哪一份），一律記進
   `ambiguous-units.tsv`，解析時挑一個（依路徑排序取第一個，至少每次執
   行結果一致）繼續分析，不代表這就是「正確」的那一份。
3. 解析每個「進入點」與「可達單元」的全部 `uses ... ;` 子句（interface/
   implementation 各自可能各有一個，都要抓，`.dpr` 的 `uses` 還可能帶
   `UnitName in 'path.pas'` 這種語法，也要剝掉 `in '...'` 才能比對名
   稱），逐一比對是否為可解析到的本地單元——是本地單元就記一條邊 A -> B
   （A 依賴 B），並繼續展開 B；不是本地單元（標準庫如
   SysUtils/Classes/IniFiles，或私有套件的外部 COM DLL）就記進
   `external-refs.tsv`，**原生標準庫跟私有套件一律不分類、原樣全部記下
   來**——這兩者的邊界本身是判斷，不是事實，判斷交給 migration-clarify
   讀這份檔案時用它對來源語言的知識去篩，這支腳本只負責把「解析不到本
   地檔案的引用」如實列出來，不做篩選、不猜測哪些重要哪些不重要。
   這是保守的 `uses` 子句擷取（先把 `//` 行註解跟 `{...}` 區塊註解拿
   掉，再抓 `uses ... ;`），不是完整的 Delphi 語法解析器——條件式編譯
   （`{$IFDEF}`）之類的邊角案例抓不到時，交給 units.tsv 的 risk_flag/
   risk_reason 欄標 high risk，不在這支腳本裡硬做完整 parser。
4. 拓樸排序；抓循環依賴分組（跟 depmap_vb6.py 同一套演算法），只對步驟
   2 篩出的可達子集合做。

輸出：核心四項跟 depmap_vb6.py 同一份契約，另外兩項是 Delphi 專屬的診斷
輸出（depmap_vb6.py 沒有，因為 VB6 靠 .vbp 明確登記模組清單，沒有這兩種
歧義）：
  migration/analysis/depmap/edges.tsv          (from, to)
  migration/analysis/depmap/order.txt          拓樸排序後的檔案路徑，一行一個
  migration/analysis/depmap/cycles.txt         循環依賴分組，一行一組（逗號分隔）
  migration/analysis/depmap/external-refs.tsv  (source_path, reference)——
    這個檔案（可達單元或 .dpr 本身）引用了哪個解析不到本地檔案的識別
    字，一列一筆，同一個 reference 出現在很多檔案就會有很多列
    （migration-clarify 用列數當出現次數的證據）。只有可達單元/.dpr
    自己的 uses 子句會被列進來——不可達的死代碼檔案內部引用什麼，不出現
    在這份清單裡。
  migration/analysis/depmap/ambiguous-units.tsv  (unit_name, path)——同一個
    單元名稱在掃描範圍內對到不只一個檔案的每一筆候選，一列一筆；空檔案
    代表沒有這種歧義。
  migration/analysis/depmap/entry-points.tsv  (dpr_path, reachable_unit_count)
    ——ROOT 底下每個 .dpr 各自可達到幾個檔案，一列一筆；只有一列時代表
    只有一個進入點，不需要特別確認。

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
# .dpr 的 uses 子句裡，每個項目可能是 `UnitName` 或 `UnitName in 'path.pas'`
# （只有 .dpr 支援 `in` 子句，一般 unit 檔案自己的 uses 不會有，但這裡通
# 用處理不特別分支，不影響一般情況）。
USES_PART_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_.]*)\s*(?:in\s+['\"][^'\"]*['\"])?$", re.IGNORECASE)
LINE_COMMENT_RE = re.compile(r"//.*")
BLOCK_COMMENT_RE = re.compile(r"\{.*?\}", re.DOTALL)


def strip_comments(content):
    content = BLOCK_COMMENT_RE.sub(" ", content)
    content = LINE_COMMENT_RE.sub("", content)
    return content


def find_pas():
    return sorted(glob.glob(os.path.join(ROOT, "**", "*.[pP][aA][sS]"), recursive=True))


def find_dpr():
    return sorted(glob.glob(os.path.join(ROOT, "**", "*.[dD][pP][rR]"), recursive=True))


def unit_name_from_content(path, content):
    m = UNIT_NAME_RE.search(content)
    if m:
        return m.group(1)
    return os.path.splitext(os.path.basename(path))[0]


def parse_uses(content):
    """回傳這個檔案（或 .dpr）全部 uses 子句裡列出的識別字（可能跨
    interface/implementation 兩個子句），去除前後空白跟 `in '...'` 路徑
    後綴。解析不到預期格式的項目照原樣整段保留，交給後面 resolve 不到就
    記進 external-refs.tsv 當一筆線索，不靜默丟掉。"""
    names = []
    for clause in USES_CLAUSE_RE.findall(content):
        for part in clause.split(","):
            part = part.strip()
            if not part:
                continue
            m = USES_PART_RE.match(part)
            names.append(m.group(1) if m else part)
    return names


def main():
    pas_files = find_pas()
    dpr_files = find_dpr()
    if not pas_files:
        print("no .pas files found under", ROOT, file=sys.stderr)

    contents = {}
    for path in pas_files:
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                contents[path] = strip_comments(f.read())
        except OSError:
            contents[path] = ""

    # 同一個 unit 名稱可能在掃描範圍內的不同目錄各出現一次（新舊備份版本、
    # 真實專案裡靠搜尋路徑優先序決定用哪一份的情況）——這支腳本無法得知
    # 真正的搜尋路徑設定，只能挑一個（依路徑排序，取第一個，至少每次執行
    # 結果一致）當作 name_to_path 的解析結果，同時把每一筆衝突原樣記下
    # 來，不靜默吃掉，交給人判斷該用哪一份。
    name_to_candidates = defaultdict(list)
    for path, content in contents.items():
        name = unit_name_from_content(path, content)
        name_to_candidates[name.lower()].append((name, path))

    name_to_path = {}
    ambiguous_units = []
    for candidates in name_to_candidates.values():
        candidates.sort(key=lambda c: c[1])
        display_name, chosen_path = candidates[0]
        name_to_path[display_name.lower()] = chosen_path
        if len(candidates) > 1:
            for _, path in candidates:
                ambiguous_units.append((display_name, path))

    dpr_contents = {}
    for dpr in dpr_files:
        try:
            with open(dpr, "r", encoding="utf-8", errors="replace") as f:
                dpr_contents[dpr] = strip_comments(f.read())
        except OSError:
            dpr_contents[dpr] = ""

    edges = set()
    external_refs = set()

    if dpr_files:
        # 可達性分析：從每個 .dpr 自己的 uses 子句當起點各自展開一次（不是
        # 合成一個共用 queue）——這樣才能個別算出「這個進入點自己可達到幾
        # 個檔案」，寫進 entry-points.tsv 給人判斷是不是有進入點其實沒被
        # 真的建置過。最終的本地模組範圍是所有進入點各自可達集合的聯集：
        # 找不到某個 .dpr 是不是真的還在用是人的知識，這支腳本不猜，只把
        # 每個進入點各自的可達範圍攤開來給人看——見模組 docstring 步驟 2。
        reachable = set()
        entry_point_counts = {}
        for dpr in dpr_files:
            local_reachable = set()
            queue = deque()
            for used in parse_uses(dpr_contents[dpr]):
                target = name_to_path.get(used.lower())
                if target:
                    queue.append(target)
                else:
                    external_refs.add((dpr, used))

            while queue:
                path = queue.popleft()
                if path in local_reachable:
                    continue
                local_reachable.add(path)
                for used in parse_uses(contents.get(path, "")):
                    target = name_to_path.get(used.lower())
                    if target:
                        if target != path:
                            edges.add((path, target))
                        if target not in local_reachable:
                            queue.append(target)
                    else:
                        external_refs.add((path, used))

            entry_point_counts[dpr] = len(local_reachable)
            reachable |= local_reachable

        if len(dpr_files) > 1:
            print(
                f"warning: found {len(dpr_files)} .dpr entry points — verify every one is "
                "actually built as part of this migration (see entry-points.tsv), not a "
                "stale/abandoned prototype",
                file=sys.stderr,
            )

        contents = {path: content for path, content in contents.items() if path in reachable}
    else:
        # 找不到任何 .dpr（理論上不該發生）：退回舊行為，ROOT 底下掃到的
        # .pas 全部當本地模組，不做可達性篩選。
        entry_point_counts = {}
        for path, content in contents.items():
            for used in parse_uses(content):
                target = name_to_path.get(used.lower())
                if target and target != path:
                    edges.add((path, target))
                elif not target:
                    external_refs.add((path, used))

    if ambiguous_units:
        print(
            f"warning: {len({name for name, _ in ambiguous_units})} unit name(s) resolved "
            "ambiguously across multiple files — see ambiguous-units.tsv",
            file=sys.stderr,
        )

    edges_path = os.path.join(OUT_DIR, "edges.tsv")
    with open(edges_path, "w", encoding="utf-8") as f:
        for a, b in sorted(edges):
            f.write(f"{a}\t{b}\n")

    external_refs_path = os.path.join(OUT_DIR, "external-refs.tsv")
    with open(external_refs_path, "w", encoding="utf-8") as f:
        for path, ref in sorted(external_refs):
            f.write(f"{path}\t{ref}\n")

    ambiguous_units_path = os.path.join(OUT_DIR, "ambiguous-units.tsv")
    with open(ambiguous_units_path, "w", encoding="utf-8") as f:
        for name, path in sorted(ambiguous_units):
            f.write(f"{name}\t{path}\n")

    entry_points_path = os.path.join(OUT_DIR, "entry-points.tsv")
    with open(entry_points_path, "w", encoding="utf-8") as f:
        for dpr in sorted(dpr_files):
            f.write(f"{dpr}\t{entry_point_counts.get(dpr, 0)}\n")

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
          f"external_refs={len(external_refs)} entry_points={len(dpr_files)} "
          f"ambiguous_units={len({name for name, _ in ambiguous_units})}")
    print(f"wrote {edges_path}, {order_path}, {cycles_path}, {external_refs_path}, "
          f"{ambiguous_units_path}, {entry_points_path}")


if __name__ == "__main__":
    main()
