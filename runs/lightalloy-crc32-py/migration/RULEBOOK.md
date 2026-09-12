# Rulebook — fixtures/lightalloy-delphi7 (Delphi 7 → Python 3)

Domain skill: `domain-lightalloy-delphi7`。以下規則對轉換 agent 是唯讀
的，不可在迴圈內修改；有缺口就走 Deviation log，交給人類決定。

## 決定

1. **Class/成員命名對應**：`TCRC32 = class(TObject)` → Python class
   `CRC32`（放在 `target/src/crc32.py`）。`constructor Create` →
   `__init__`；`Reset` → `reset()`；`Result`（方法名，不是隱含返回值）→
   `result()`；`UpdateWithBuffer` → `update(data: bytes)`；
   `UpdateWithStream` → `update_stream(stream)`。
   （來源：domain skill 語法轉換規則 #1）
2. **不得用 `zlib.crc32` 頂替實作**：`CRCHash` 查表迴圈要真的翻譯成
   Python，`zlib.crc32` 只能是 `migration/behavior-snapshots/CRC32.md` 的
   驗證基準來源，不是實作本身可以委派的對象。
   （來源：domain skill 語法轉換規則 #2）
3. **`CRCHash` 256 個常數原樣搬遷**：逐一從 `$XXXXXXXX` 換成
   `0xXXXXXXXX`，數值、順序都要跟原始 Pascal 表逐條一致，不可以用程式產生
   的方式重算或簡化替代（例如不要因為「反正是標準演算法」就自己用位元運
   算生成表格取代硬編碼常數表——搬字過紙才是這個 unit 要驗證的翻譯品
   質）。
   （來源：domain skill 語法轉換規則 #3）
4. **`Buf:Pointer;Size:LongInt` → `data: bytes`（或其他 bytes-like，例如
   `bytearray`/`memoryview`）**，逐位元組迭代取代指標算術。
   （來源：domain skill 語法轉換規則 #4）
5. **不需要額外顯式 `& 0xFFFFFFFF` mask**：domain skill 已經證明這條運算
   式在整個過程中數值不會超出 32-bit 範圍，Python 任意精度 int 不會意外
   「長大」。轉換 agent 不必為了「看起來像在做無號整數運算」到處加 mask。
   （來源：domain skill 語法轉換規則 #5）
6. **`TStream` 參數用支援 `seek()`/`read()` 的 binary stream 物件代表**，
   不重建 `.Size` 屬性，改用「讀到 EOF（`read()` 回傳空 bytes）就停」的迴
   圈；語意等價於原始「先問 `Size` 再分塊讀」寫法。
   （來源：domain skill 語法轉換規則 #6）

## Deviation log

（轉換迴圈執行中若發現規則缺口，記錄在這裡；本檔案在迴圈內唯讀，此區塊由
人類在批次之間維護。目前無項目。）