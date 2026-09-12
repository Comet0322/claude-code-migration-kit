---
name: domain-lightalloy-mediainfo-audio
description: >
  涵蓋 fixtures/lightalloy-delphi7 這批取自真實開源專案 Light Alloy（Windows
  媒體播放器，Borland Delphi 7，GPL-2.0）的音訊格式中繼資料解析器，路徑
  Source/Engine/MediaInfo/Audio/ 底下全部 22 個 .pas 檔案（atl 前綴命名，
  ID3v1/ID3v2/APE tag/FLAC/WAV/OGG Vorbis/Speex/WMA/AAC/DTS/AC3/CD 音軌等）。
  目標語言 Python 3（只用標準庫，不裝任何 pip 套件）。跟 domain-lightalloy-delphi7
  是同一個原始 repo，但涵蓋完全不同的子系統（音訊格式解析 vs. 單一 CRC-32
  工具 class），是刻意分開的獨立 domain skill，不是同一份的擴充。
---

# domain-lightalloy-mediainfo-audio

## 這個 domain skill 涵蓋的應用類型

Light Alloy（`light-alloy.ru`）——同一套 Windows 媒體播放器（見
`domain-lightalloy-delphi7`），這次涵蓋的是它的音訊格式中繼資料解析層：
`fixtures/lightalloy-delphi7/source-repo/Source/Engine/MediaInfo/Audio/` 底
下全部 22 個 `.pas` 檔案，全部以 `atl` 前綴命名（Audio Tag Library 的縮
寫，觀察自檔名慣例）：

```
atlAACfile  atlAC3      atlAPEtag     atlCDAtrack   atlDTS
atlFLACfile atlFPLfile  atlID3v1      atlID3v2      atlMPEGaudio
atlMPEGplus atlMonkey   atlMusepack   atlOggVorbis  atlOptimFROG
atlSpeex    atlTTA      atlTwinVQ     atlVorbisComment
atlWAVPackfile atlWAVfile atlWMAfile
```

每個檔案是一個獨立的 `TObject` 子類別，各自解析一種音訊格式的檔頭/中繼
資料（不做音訊解碼）。目標語言 Python 3，只用標準庫。

指紋：檔案開頭有 `unit atl<Something>;` 宣告；路徑含
`Source/Engine/MediaInfo/Audio/`；主要 class 一律直接繼承 `TObject`（或省
略、隱含 `TObject`），彼此之間用「持有」而非繼承（例如多數檔案的 class 內
部有 `FID3v1: TID3v1`、`FID3v2: TID3v2`、`FAPEtag: TAPETag` 私有欄位）。

## 私有套件文件

沒有這批以外的外部私有套件。但這批**內部**有 3 個基礎 unit 被其他多數檔
案依賴（已用 `depmap_pascal.py` 腳本驗證，非採信推測）：

- `atlID3v1`：被 7 個檔案依賴（atlAACfile, atlMPEGaudio, atlMPEGplus,
  atlMonkey, atlMusepack, atlOptimFROG, atlTTA）
- `atlID3v2`：被 8 個檔案依賴（同上 7 個 + atlFLACfile）
- `atlAPEtag`：被 8 個檔案依賴（同上 7 個 + atlWAVPackfile）

無循環依賴。轉換順序必須先處理這三個基礎 unit（細節見
`migration/analysis/modules.tsv` 與 `migration/analysis/depmap/`），這三個
出錯會波及 7-8 個下游檔案，風險等級因此標高（見 risk-notes.tsv）。

`atlVorbisComment` 被 `atlSpeex` 依賴（1 個），`atlOggVorbis` 也用到
Vorbis comment 概念但沒有透過 `uses` 依賴 `atlVorbisComment`（各自獨立實
作）。其餘檔案彼此獨立。

## 來源語言執行環境

跟 `domain-lightalloy-delphi7` 完全一樣的情況（同一個 Delphi 7 codebase）：
**未知，不可假設任何一台機器裝得起來。** migration-clarify 必須當場確認
（`which dcc32`、`which fpc`，唯讀查詢），不能沿用其他 repo 實例的結論，
也不能自己安裝。這批的 ground truth 分層決定見
`migration/ground-truth-strategy.md`。

## 模板專案

（這批獨立成自己的一次遷移，`target/` 不再跟 domain-lightalloy-delphi7
那批的 `crc32.py` 共用同一個執行根目錄——兩者現在是各自獨立的
`runs/<名稱>/`，這裡列的路徑相對於這次遷移自己的執行根目錄。）

```
target/
  src/
    audio/                # 這個 domain skill 的產物
      id3v1.py
      id3v2.py
      apetag.py
      flacfile.py
      wavfile.py
      oggvorbis.py
      vorbiscomment.py
      speex.py
      tta.py
      cdatrack.py
      aacfile.py
      ac3.py
      dts.py
      mpegaudio.py
      mpegplus.py
      musepack.py
      monkey.py
      optimfrog.py
      twinvq.py
      wavpackfile.py
      wmafile.py
      fplfile.py
  test/
    audio/
      __init__.py          # 空檔，必須存在——見下方「測試目錄慣例」
      test_id3v1.py
      test_id3v2.py
      ...（每個 unit 一個 test_<name>.py，同上列命名）
```

用 Python 標準庫的 `unittest`，不裝任何 pip 套件。

**模組匯入慣例（沿用 CRC32 那批的風格，刻意不建立 package）**：
`target/src/audio/` 底下的檔案彼此用 flat import 互相參照（例如
`monkey.py` 裡 `from id3v1 import ID3v1`），不用 `from .id3v1 import
ID3v1` 這種 relative import——這代表任何會 import 同批其他模組的檔案，測
試檔案跟被匯入的模組都要能在 `sys.path` 上同時看到
`target/src/audio/`（不是 `target/src/`）。測試檔案開頭跟著 `test_crc32.py`
的慣例，用：
```python
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src", "audio"))
```
（比 `test_crc32.py` 多一層 `..`，因為測試檔案這次放在 `target/test/audio/`
子目錄底下，不是 `target/test/` 直接底下）。

**測試目錄慣例**：`target/test/audio/` 需要一個空的 `__init__.py`——已經
在 clarify 階段用 `python3 -m unittest discover` 實測驗證過：**沒有這個
檔案，`unittest discover` 不會遞迴進子目錄找測試**（在乾淨的 Python 3.14
環境下直接試驗確認過，不是聽說）。這個檔案已經在 scaffold 階段建立好。

沒有單一進入點——這批全部是各自獨立的格式解析 class，不是有進入點的程
式（跟 CRC32 那批同樣情況，但這兩批現在是各自獨立的 `runs/`，不共用同一
個執行根目錄）。整合檢查只需要「全部測試一起跑」
（`python3 -m unittest discover -s target/test`，相對於這次遷移自己的
執行根目錄）。

外部套件：無，只用 Python 標準庫（`struct`、`io`、`configparser`），不需
要 `pip install` 任何東西。

## 語法轉換 / library 替換規則

1. **檔案/串流讀取統一對應**：這批檔案混用兩種 Delphi I/O 風格——
   `TFileStream`/`TMemoryStream`（15 個檔案）跟舊式 untyped file
   （`AssignFile`/`Reset(f,1)`/`BlockRead`/`BlockWrite`/`CloseFile`，7 個
   檔案：atlAPEtag, atlID3v2, atlFPLfile, atlID3v1, atlTwinVQ, atlMPEGplus,
   atlWAVfile）。兩者語意相同（開檔、seek、讀/寫固定長度 bytes），一律對
   應到 Python `open(path, "rb")`（或 `"r+b"` 需要寫入時）/`io.BytesIO`，
   用 `.read(n)`/`.write(data)`/`.seek(offset[, whence])` 統一介面，不要因
   為來源用的 API 形狀不同就翻出兩種不同的 Python 抽象。

2. **固定長度 record 讀取一律用 `struct`（stdlib）逐欄位對應，禁止猜測
   padding**：這批大量透過 `BlockRead(f, Header, N)` 或
   `Stream.Read(Header, N)` 把一段固定 N bytes 直接讀進一個 Pascal
   `record`。轉換 agent 動手前必須先驗算：把 record 每個欄位依 Delphi 型
   別大小相加（`Byte`=1、`Word`=2、`LongInt`/`DWORD`/`Integer`/
   `Cardinal`=4、`Int64`=8、`array[1..K] of Byte`/`of Char`=K），確認總和
   等於 `N`。對得上才能直接用 `struct.unpack("<...", data)`（Delphi
   在 x86/Win32 是 little-endian，一律用 `<` 前綴，不要用 native 對齊模式
   `@`/`=` 以外的其他前綴，因為 Python `struct` 的 native 模式會插入平台
   對齊 padding，那不是我們要的）。**對不上就不准自己猜一個 padding 方案
   硬套**——记一筆 deviation，交人類決定（可能是某個欄位型別看錯、或
   record 宣告雖然沒寫 `packed` 但實際上編譯器沒插 padding，需要人工用其
   他方式核對）。這批 22 個檔案裡，多個 record 型別**沒有**宣告
   `packed`（`atlAPEtag.RTagHeader/RField`、`atlID3v2.FrameHeaderNew/Old/
   TagInfo`、`atlMPEGaudio.VBRData/FrameData`、
   `atlMPEGplus`/`atlMusepack.HeaderRecord`、
   `atlTwinVQ.ChunkHeader/HeaderInfo`、`atlWAVfile.WAVRecord`、
   `atlWAVPackfile` 的 4 個 record、`atlWMAfile.FileData`）——这些是本規
   則最需要留意的對象。

3. **位元級解析用內建整數位元運算**：`atlAACfile.pas` 的全域函式
   `ReadBits`（L150）跟 `atlMPEGaudio.pas` 的 `IsFrameHeader`（L292-309）
   都是逐 bit（非 byte 對齊）解析，一律用 Python 內建 `>>`、`<<`、`&`、
   `|` 對應，不要引入額外的 bitstring 類套件（標準庫沒有，也不需要）。

4. **Sync word / magic number 常數原封不動搬遷，不重新推導表示法**：這批
   很多格式用固定數值或固定字串當簽章（例如 `atlAC3.pas` 的
   `SignatureChunk = 30475`、`atlDTS.pas` 的 `SignatureChunk =
   25230975`、`atlTTA.pas` 用 `StrLComp(...,'TTA1',4)`、
   `atlOggVorbis.pas` 的 `OGG_PAGE_ID = 'OggS'`、`atlFLACfile.pas` 核對
   `'fLaC'`、`atlAPEtag.pas` 的 `APE_ID = 'APETAGEX'`）。轉換 agent 要保
   留來源選擇的比較型態（數值比較就繼續數值比較、字串比較就繼續字串比
   較），不要因為「看起來像是位元組序反轉的 magic number」就自己重新推
   導成看起來更合理的十六進位或 bytes-literal 表示法——跟 CRC32 rulebook
   #3 同精神：搬字過紙，不是重新設計。

5. **Class 命名衝突：`atlMPEGplus.pas` 與 `atlMusepack.pas` 都宣告了同名
   的 `TMPEGplus` class**（彼此完全獨立、非同一型別，只是 Light Alloy 原
   始碼剛好取了一樣的名字），Python 對應類別依「檔案」而非「原始類別名
   稱」命名，避免兩個結構不同的東西在目標語言裡撞名：
   - `atlMPEGplus.pas` → class `MPEGPlus`（`target/src/audio/mpegplus.py`）
   - `atlMusepack.pas` → class `Musepack`（`target/src/audio/musepack.py`）
   兩者各自的 8 個全域輔助函式（`ReadHeader`/`GetStreamVersion`/
   `GetSampleRate`/`GetEncoder`/`GetChannelModeID`/`GetFrameCount`/
   `GetBitRate`/`GetProfileID`）簽名雖然幾乎一樣，也分別留在各自的模組
   內，不要合併成共用 helper——這兩個 unit 除了巧合的命名，沒有任何實
   際共用關係。

6. **`Dialogs` 依賴一律捨棄，不建立任何等價物**：`atlAPEtag.pas:338` 跟
   `atlFPLfile.pas:213` 是這批僅有的兩處 `Dialogs` 相關程式碼，且**都是
   整行被 `//` 註解掉的死碼**（`ShowMessage` debug 呼叫），已在 clarify
   階段逐行核對過，沒有任何流程依賴對話框回傳值。轉換時直接不 import
   這兩個檔案原本的 `Dialogs`，不需要用 `print`/`logging` 或任何東西頂
   替——那些行本來就不會執行。

7. **`atlMPEGaudio.pas` 的 Win32 handle-based API 語意等價於
   `TFileStream`**：implementation 區的 `uses Windows;`（L274）不是殘
   留 import，`ReadFromFile` 方法（L799-874）真的呼叫了
   `FileOpen`/`GetFileSize`/`SetFilePointer`/`ReadFile`/`CloseHandle`。
   這些呼叫語意上跟其他檔案用 `TFileStream` 完全等價（開檔、找位置、
   讀固定長度、關檔），對應到同一套 Python 檔案 API（`open`/`.seek`/
   `.read`/`.close` 或改用 `with` context manager），不需要因為看到
   `uses Windows` 就當成 Windows-only 邏輯特殊處理，也不需要引入
   `ctypes`/`pywin32` 之類的東西。

8. **`PChar`/指標算術對應到 Python bytes 索引/切片**：`atlAPEtag.pas`
   （`PChar` × 5、指標算術）、`atlMPEGaudio.pas`（`Pointer` × 3、
   `Inc(P` × 多次）用的是 C 風格指標位移，一律對應到 Python
   `bytes`/`bytearray` 的索引或切片（`data[i]`、`data[i:i+n]`），不使用
   `ctypes`。

9. **模組層級的全域可變狀態，對應到 Python module-level 變數，各自獨
   立、不合併**：`atlID3v1.pas` 在 `initialization` section（L626-788）
   設定 5 個 interface-scope 全域變數（`aTAG_MusicGenre` 148 個字串的
   genre 清單、`bTAG_PreserveDate`、`bTAG_ID3v2PreserveALL`、
   `bTAG_UseLYRICS3`、`bTAG_GenreOther`）；`atlFLACfile.pas` 也在
   interface scope 宣告了一個**同名但完全獨立**的
   `bTAG_PreserveDate`（L176-177，`atlFLACfile.pas` 沒有 `uses
   atlID3v1`，這不是共用同一個變數,是巧合同名的兩個宣告）；
   `atlFPLfile.pas` 有一個 interface-scope 的 `FPLItems: array of
   TFPLitem`（L137-138）。轉換時每個都對應到各自目標模組裡的
   module-level 變數，保留原始初始值，**不要因為看到同名就合併成共用設
   定物件**。

10. **`atlFPLfile.pas` 裡被註解掉的 `//uses Main;`（L143）確認是死碼殘
    留**（這個 unit 目前不依賴應用程式主表單的任何東西），Python 版本不
    需要重建任何主表單相關功能，直接忽略這行殘留註解。

11. **`atlCDAtrack.pas` 用 `TIniFile` 讀 `cdplayer.ini`**（Windows 標準
    CD 音軌快取檔），對應到 Python 標準庫 `configparser`。**注意
    `configparser` 預設對 section/key 大小寫的處理跟 Windows INI 語意可
    能有差異**（`configparser` 的 key 預設 case-insensitive、但 section
    name 是 case-sensitive；Windows API 的 INI 讀取通常兩者都
    case-insensitive）——轉換這個檔案時要對照 `atlCDAtrack.pas` 實際讀
    的 section/key 名稱大小寫是否一致，不一致就明確處理（例如統一轉小
    寫比對），不要假設兩邊語意自動對齊。

## 新語言 library 文件

- `struct`（stdlib）：`struct.unpack(fmt, data)`/`struct.pack(fmt, ...)`。
  `fmt` 開頭一律用 `<`（little-endian，無平台對齊 padding）。常用格式
  字元對照 Delphi 型別：`B`=Byte(1)、`H`=Word(2)、`I`=DWORD/Cardinal(4)、
  `i`=LongInt/Integer(4，有號)、`Q`=UInt64(8)、`q`=Int64(8，有號)、
  `<Ns>`=固定長度 char 陣列（`N` 個 byte 的 bytes，不會自動去除補零字
  元，要自己 `.rstrip(b"\x00")` 或找到第一個 `\x00`）。
- `io.BytesIO`：記憶體內建立可 `seek`/`read` 的物件，行為對應 Delphi
  `TMemoryStream`。
- `configparser`：解析 `.ini` 格式（`atlCDAtrack.pas` 用），
  `configparser.ConfigParser()` + `.read(path)` + `cp[section][key]`。
- 內建 `bytes`/`bytearray`/`memoryview` 的逐位元組迭代：對應
  `Buf:Pointer;Size:LongInt` 這種指標+長度參數（跟 CRC32 那批同樣模
  式）。
- Python 3 `int` 任意精度，不會有 Delphi `DWORD`/`Word` 溢位環繞問題——
  但這批部分格式（例如 checksum、CRC 變體）**依賴** 32-bit/16-bit 環繞
  行為本身是演算法的一部分（不像 CRC32 那批已經證明過不需要），轉換時
  要逐一判斷是否需要顯式 `& 0xFFFFFFFF`/`& 0xFFFF` mask,不能沿用 CRC32
  那條「不需要 mask」的結論——那個結論是針對 `CRCHash` 那個特定運算式證
  明的，不是通則。

## 測試 / build 方法

（以下路徑相對於這次遷移自己的執行根目錄 `runs/<這次遷移的名稱>/`，不是
這個 domain skill 描述的來源 `fixtures/lightalloy-delphi7/`；這批跟
domain-lightalloy-delphi7 的 CRC32 是各自獨立的 run，不共用執行根目錄，
不會出現「含 CRC32」的整合測試）

- Build（語法檢查，逐檔或整批）：
  `python3 -m py_compile target/src/audio/*.py`
- 單一 unit 測試：
  `python3 -m unittest discover -s target/test/audio`
- 整合測試（這批全部）：
  `python3 -m unittest discover -s target/test`

## Fingerprint

- 檔名以 `atl` 開頭，內容含 `unit atl<Name>;` 宣告。
- 路徑含 `Source/Engine/MediaInfo/Audio/`。
- 主要 class 直接繼承 `TObject`（或省略括號隱含 `TObject`），不會有跨檔
  案的 class 繼承（已用逐檔掃描驗證：這 22 個檔案彼此之間全部是「持有」
  關係，沒有繼承關係）。
- 常見 uses：`atlID3v1`、`atlID3v2`、`atlAPEtag`（3 個基礎 unit，被 7-8
  個其他檔案依賴）。
