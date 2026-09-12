# Ground truth strategy — runs/lightalloy-crc32-py (來源: fixtures/lightalloy-delphi7)

Tier 選定：**snapshot**

## 決策過程

依 migration-clarify 三層順序檢查：

1. **tier: environment** — 不採用。唯讀查詢確認這台機器沒有可用的來源語言
   執行環境：`which dcc32` → not found，`which fpc` → not found。
   `domain-lightalloy-delphi7` 的「來源語言執行環境」小節也明講「未知，不
   可假設任何一台機器裝得起來」。不自己安裝 `dcc32`/`fpc`。
2. **tier: snapshot** — 採用。這個 unit（`TCRC32`）實作的是業界標準演算法
   CRC-32（IEEE 802.3 / ISO-HDLC，跟 zlib、PNG、Ethernet FCS、PKZIP 用的是
   同一個演算法：poly 0xEDB88320 反射多項式、初始值
   `$FFFFFFFF`、輸出前 XOR `$FFFFFFFF`——這些都直接對得上
   `legacy/CRC32.pas` 裡的 `CRCHash` 表跟 `Reset`/`Result` 實作）。因此可
   以用 Python 內建、跟來源語言完全無關的外部權威實作 `zlib.crc32` 算出標
   準值，由人工核對演算法一致後存成快照，不需要真的跑起 Delphi。存在
   `migration/behavior-snapshots/CRC32.md`。
3. **tier: inference** — 不需要，snapshot 已經涵蓋這個 fixture 需要的案例
   （空輸入、單一 unit、edge 值、全 256 值、任意字串、跨呼叫累加）。

## 為什麼這裡跟 delphi-etl fixture 不同

`domain-delphi-etl-py` 那批的固定寬度欄位解析邏輯是這個 repo 自訂的業務規
則，沒有語言無關的外部權威可以核對，snapshot 只能靠人工依規格文件手動推
導。這裡不同：CRC-32 是公開發表、廣泛實作的標準演算法，`zlib.crc32` 不是
「猜測」，是同一個演算法的另一份獨立實作，拿來當 snapshot 來源比手動推導
更可靠、也更不需要懷疑正確性。