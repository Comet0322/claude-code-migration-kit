---
name: domain-lightalloy-delphi7
description: >
  涵蓋 fixtures/lightalloy-delphi7 這批取自真實開源專案 Light Alloy（Windows
  媒體播放器，Borland Delphi 7，GPL-2.0）的程式碼單元，目標語言 Python 3（只
  用標準庫，不裝任何 pip 套件）。目前只包裝了 Source/Common/Crypt/CRC32.pas
  (TCRC32 class) 這一個 unit 的領域知識——這批是刻意小規模、真實碼的驗證測
  試，不是完整遷移這個 194 檔案的 app。
---

# domain-lightalloy-delphi7

## 這個 domain skill 涵蓋的應用類型

Light Alloy（`light-alloy.ru`）——一套真實被使用過的 Windows 媒體播放器，
Borland Delphi 7 撰寫，GPL-2.0 授權，`fixtures/lightalloy-delphi7/legacy/`
底下是從其 `source-repo/Source/Common/Crypt/CRC32.pas` 抽出的單一 unit
（`TCRC32` class，標準 CRC-32 / IEEE 802.3 演算法）。目標語言 Python 3，只
用標準庫。

指紋：檔案內容含 `unit CRC32;`、`TCRC32 = class(TObject)`、常數陣列
`CRCHash:array [0..255] of DWORD`；或路徑含
`Source/Common/Crypt/CRC32.pas`。

## 私有套件文件

無。這個 unit 不依賴任何 Light Alloy 私有/內部套件——`uses Windows,
Classes` 兩個都是標準 Delphi 框架單元（Win32 API 繫結、VCL 基礎類別），不
是這個 repo 自製的東西，不需要额外文件。

## 來源語言執行環境

**未知，不可假設任何一台機器裝得起來。** 這是 Borland Delphi 7（商業授
權）寫的程式碼；不確定機器上有沒有相容的編譯環境（Delphi 7 本身或
Free Pascal Compiler）。migration-clarify 必須當場確認（`which dcc32`、
`which fpc`，唯讀查詢），不能假設前一個 repo 有裝這次就一定有，也不能自己
安裝。

不過這個 unit（CRC-32 / IEEE 802.3）剛好是業界標準演算法，有語言無關的外
部權威實作可以交叉驗證（例如 Python 內建 `zlib.crc32`），所以**即使沒有
Delphi 執行環境，也不必退到 `inference` tier**——見
`migration/ground-truth-strategy.md`，這批選的是 `snapshot` tier，快照內容
就是拿 `zlib.crc32` 算出來的標準值。

## 模板專案

```
fixtures/lightalloy-delphi7/target/
  src/
    crc32.py
  test/
    test_crc32.py
```

用 Python 標準庫的 `unittest`，不裝任何 pip 套件。模組系統就是一般 Python
`import`（無特殊限制）。

沒有單一進入點——這是一個獨立的 CRC-32 工具 class，不是一個有進入點的程
式。整合檢查只需要「全部測試一起跑」，不用執行進入點這項。

外部套件：無，只用 Python 標準庫，不需要 `pip install` 任何東西。

## 語法轉換 / library 替換規則

1. **`TCRC32 = class(TObject)` → Python class `CRC32`**（`target/src/crc32.py`
   模組內）。成員對應：
   - `constructor Create` → `__init__(self)`（呼叫 `reset()`）
   - `procedure Reset` → `def reset(self)`
   - `function Result:DWORD`（Delphi 這裡的 `Result` 是方法名稱，不是隱含返
     回值變數——刻意用 `Result` 當方法名） → `def result(self) -> int`
   - `procedure UpdateWithBuffer(Buf:Pointer;Size:LongInt)` → `def
     update(self, data: bytes) -> None`
   - `procedure UpdateWithStream(Stream:TStream)` → `def update_stream(self,
     stream) -> None`

2. **禁止直接呼叫 `zlib.crc32` 頂替實作**：這個 unit 存在的目的就是驗證「查
   表法逐位元組翻譯」轉得對不對，`zlib.crc32` 只能當**外部驗證基準**（見
   `migration/behavior-snapshots/CRC32.md`），轉換 agent 必須真的把
   `CRCHash` 查表迴圈翻譯成 Python，不能圖方便直接委派給 `zlib.crc32()`。

3. **`CRCHash` 常數表原樣搬遷**：256 個 `$XXXXXXXX` 十六進位常數，逐一換成
   Python `0xXXXXXXXX`，數值必須逐條比對正確（大小寫、順序都不能變）——這
   是演算法核心資料，不是可以重新生成或简化的東西。

4. **`Buf:Pointer;Size:LongInt` → `data: bytes`（或任何 bytes-like，例如
   `bytearray`/`memoryview`）**：Python 用 `for byte in data:` 逐位元組取代
   C 風格的指標算術（`Inc(P)`）。

5. **`DWORD` 32-bit 無號整數運算不需要額外顯式 `& 0xFFFFFFFF` mask**：可以
   證明 `Sum:=CRCHash[(Sum and $FF) xor P^] xor ((Sum shr 8) and
   $00FFFFFF)` 這條運算式裡，`CRCHash[...]` 本身 ≤ `0xFFFFFFFF`、
   `(Sum shr 8) and $00FFFFFF` ≤ `0x00FFFFFF`，兩者 XOR 的結果位元寬度不會
   超過運算元最大位元寬度，所以只要 `Sum` 一開始（`Reset` 設為
   `$FFFFFFFF`）就落在 32-bit 範圍內，之後每一步都會繼續落在 32-bit 範圍
   內，Python 的任意精度 `int` 不會不小心「長大」。轉換 agent 如果想額外加
   `& 0xFFFFFFFF` 保險也可以，但不是必須；不要因為看到 `DWORD` 就到處加 mask
   讓程式碼變得比原始邏輯更囉唆。

6. **`TStream` 參數用支援 `seek()`/`read()` 的 binary stream 物件代表**：
   任何實作 `seek(offset, whence)` 與 `read(size) -> bytes` 的物件皆可（內
   建 binary-mode file object、`io.BytesIO` 都符合）——不需要重建 Delphi
   `TStream.Size` 屬性。原始 `UpdateWithStream` 用 `Stream.Size` 算出還剩多
   少要讀、分成 ≤32768 bytes 的區塊讀取；Python 對應寫法改成更符合慣例的
   「讀到 EOF（`read()` 回傳空 bytes）就停」迴圈，不必先問長度：
   ```python
   def update_stream(self, stream, chunk_size: int = 32768) -> None:
       stream.seek(0)
       while True:
           chunk = stream.read(chunk_size)
           if not chunk:
               break
           self.update(chunk)
   ```
   行為上等價（都是「從頭讀到底，逐塊餵給 update」），只是不假設 stream 有
   `.Size`/`.seek` 之外的介面。

## 新語言 library 文件

不需要任何額外文件，只用得到：
- 內建 `bytes`/`bytearray`/`memoryview` 的逐位元組迭代
- 整數位元運算（`^`→`^`（Python 也是 `^`）、`shr`→`>>`、`and`→`&`）
- Python 3 `int` 是任意精度，不會有 Delphi `DWORD` 溢位環繞的問題（見上面
  規則 5 的證明，這裡刻意不需要額外套件）

## 測試 / build 方法

- Build（語法檢查）：`python3 -m py_compile
  fixtures/lightalloy-delphi7/target/src/crc32.py`
- Test：`python3 -m unittest discover -s
  fixtures/lightalloy-delphi7/target/test`

## Fingerprint

- 應該找得到字樣 `unit CRC32;` 與 `TCRC32 = class(TObject)`。
- 應該找得到常數陣列宣告 `CRCHash:array [0..255] of DWORD`。
- 路徑慣例：`Source/Common/Crypt/CRC32.pas`（相對於 Light Alloy 原始 repo
  根目錄）。
