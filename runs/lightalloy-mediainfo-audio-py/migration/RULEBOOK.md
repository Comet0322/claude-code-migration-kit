# Rulebook — fixtures/lightalloy-mediainfo-audio (Delphi 7 → Python 3)

Domain skill: `domain-lightalloy-mediainfo-audio`。這批來源程式碼跟
`fixtures/lightalloy-delphi7` 是同一個 Light Alloy checkout（`source_path`
以相對路徑 `../../fixtures/lightalloy-delphi7/source-repo/...` 引用同一份，沒有重新
clone），但涵蓋完全不同的子系統（22 個音訊格式中繼資料解析器，不是
CRC-32 工具 class），是獨立的 domain skill、獨立的 migration/ 狀態。以下
規則對轉換 agent 是唯讀的，不可在迴圈內修改；有缺口就走 Deviation log，
交給人類決定。

## 決定

1. **檔案/串流 I/O 統一對應**：`TFileStream`/`TMemoryStream`（15 個檔
   案）與舊式 untyped file（`AssignFile`/`BlockRead`/`BlockWrite`/
   `CloseFile`，7 個檔案：atlAPEtag、atlID3v2、atlFPLfile、atlID3v1、
   atlTwinVQ、atlMPEGplus、atlWAVfile）一律對應到 Python
   `open(path, "rb")`/`io.BytesIO`，用 `.read()`/`.write()`/`.seek()`。
   （來源：domain skill 語法轉換規則 #1）
2. **固定長度 record 一律用 `struct`，`<` little-endian 前綴，禁止猜測
   padding**：動手前先驗算欄位大小總和是否等於實際讀取的 byte 數；對不
   上就記 deviation，不准自己猜一個 padding 方案硬套。特別留意這批裡宣
   告成非 `packed` 的 record 型別：`atlAPEtag.RTagHeader/RField`、
   `atlID3v2.FrameHeaderNew/Old/TagInfo`、
   `atlMPEGaudio.VBRData/FrameData`、
   `atlMPEGplus`/`atlMusepack.HeaderRecord`、
   `atlTwinVQ.ChunkHeader/HeaderInfo`、`atlWAVfile.WAVRecord`、
   `atlWAVPackfile` 的 4 個 record（`wavpack_header3`、
   `wavpack_header4`、`fmt_chunk`、`riff_chunk`）、`atlWMAfile.FileData`。
   （來源：domain skill 語法轉換規則 #2）
3. **位元級解析用內建整數位元運算**（`atlAACfile.ReadBits`、
   `atlMPEGaudio.IsFrameHeader`），不引入額外套件。
   （來源：domain skill 語法轉換規則 #3）
4. **Sync word / magic number 常數原封不動搬遷**：保留來源的比較型態
   （數值比較就繼續數值比較、字串比較就繼續字串比較），不要因為「看起
   來像是位元組序反轉的 magic number」就自己重新推導成看起來更合理的
   十六進位或 bytes-literal 表示法——搬字過紙，不是重新設計。
   （來源：domain skill 語法轉換規則 #4）
5. **Class 命名衝突**：`atlMPEGplus.pas` 與 `atlMusepack.pas` 都宣告了
   同名的 `TMPEGplus` class（彼此完全獨立、非同一型別，只是巧合同
   名）。Python 對應類別依「檔案」而非「原始類別名稱」命名：
   - `atlMPEGplus.pas` → class `MPEGPlus`（`target/src/audio/mpegplus.py`）
   - `atlMusepack.pas` → class `Musepack`（`target/src/audio/musepack.py`）
   兩者各自的 8 個全域輔助函式（`ReadHeader`/`GetStreamVersion`/
   `GetSampleRate`/`GetEncoder`/`GetChannelModeID`/`GetFrameCount`/
   `GetBitRate`/`GetProfileID`）簽名雖然幾乎一樣，也分別留在各自的模組
   內，不合併成共用 helper——這兩個 unit 除了巧合的命名，沒有任何實際
   共用關係。
   （來源：domain skill 語法轉換規則 #5）
6. **`Dialogs` 依賴一律捨棄，不建立任何等價物**：`atlAPEtag.pas:338`
   跟 `atlFPLfile.pas:213` 是這批僅有的兩處 `Dialogs` 相關程式碼，且
   **都是整行被 `//` 註解掉的死碼**（`ShowMessage` debug 呼叫），已逐行
   核對過（`Dialogs.`、`MessageDlg`、`MessageBox`、`InputBox`、
   `InputQuery`、`PromptForFileName`、`SelectDirectory`、`ShowModal` 等
   字樣均無其他出現），沒有任何流程依賴對話框回傳值。轉換時直接不
   import `Dialogs`，不需要用 `print`/`logging` 或任何東西頂替。
   （來源：domain skill 語法轉換規則 #6）
7. **`atlMPEGaudio.pas` 的 Win32 handle-based API 語意等價於
   `TFileStream`**：implementation 區的 `uses Windows;`（L274）不是殘
   留 import，`ReadFromFile` 方法（L799-874）真的呼叫了
   `FileOpen`/`GetFileSize`/`SetFilePointer`/`ReadFile`/`CloseHandle`。
   這些呼叫語意上跟其他檔案用 `TFileStream` 完全等價，對應到同一套
   Python 檔案 API，不需要因為看到 `uses Windows` 就當成 Windows-only
   邏輯特殊處理，也不需要引入 `ctypes`/`pywin32`。
   （來源：domain skill 語法轉換規則 #7）
8. **`PChar`/指標算術對應到 Python bytes 索引/切片**：`atlAPEtag.pas`
   （`PChar` × 5、指標算術）、`atlMPEGaudio.pas`（`Pointer` × 3、
   `Inc(P` × 多次）用的是 C 風格指標位移，一律對應到 Python
   `bytes`/`bytearray` 的索引或切片（`data[i]`、`data[i:i+n]`），不使用
   `ctypes`。
   （來源：domain skill 語法轉換規則 #8）
9. **模組層級的全域可變狀態，對應到 Python module-level 變數，各自獨
   立、不合併**：`atlID3v1.pas` 在 `initialization` section
   （L626-788）設定 5 個 interface-scope 全域變數（`aTAG_MusicGenre`
   148 個字串的 genre 清單、`bTAG_PreserveDate`、
   `bTAG_ID3v2PreserveALL`、`bTAG_UseLYRICS3`、`bTAG_GenreOther`）；
   `atlFLACfile.pas` 也在 interface scope 宣告了一個**同名但完全獨立**
   的 `bTAG_PreserveDate`（L176-177，`atlFLACfile.pas` 沒有 `uses
   atlID3v1`，這不是共用同一個變數，是巧合同名的兩個宣告）；
   `atlFPLfile.pas` 有一個 interface-scope 的 `FPLItems: array of
   TFPLitem`（L137-138）。轉換時每個都對應到各自目標模組裡的
   module-level 變數，保留原始初始值，**不要因為看到同名就合併成共用
   設定物件**。
   （來源：domain skill 語法轉換規則 #9）
10. **`atlFPLfile.pas` 裡被註解掉的 `//uses Main;`（L143）確認是死碼殘
    留**（這個 unit 目前不依賴應用程式主表單的任何東西），Python 版本
    不需要重建任何主表單相關功能，直接忽略這行殘留註解。
    （來源：domain skill 語法轉換規則 #10）
11. **`atlCDAtrack.pas` 用 `TIniFile` 讀 `cdplayer.ini`**（Windows 標準
    CD 音軌快取檔），對應到 Python 標準庫 `configparser`。**注意
    `configparser` 預設對 section/key 大小寫的處理跟 Windows INI 語意
    可能有差異**（`configparser` 的 key 預設 case-insensitive、但
    section name 是 case-sensitive；Windows API 的 INI 讀取通常兩者都
    case-insensitive）——轉換這個檔案時要對照 `atlCDAtrack.pas` 實際讀
    的 section/key 名稱大小寫是否一致，不一致就明確處理（例如統一轉小
    寫比對），不要假設兩邊語意自動對齊。
    （來源：domain skill 語法轉換規則 #11）
12. **32-bit/16-bit 環繞行為需要逐一判斷，不套用其他 fixture 的通則**：
    這批部分格式（例如 atlOggVorbis/atlSpeex 的自訂 CRC 變體）的環繞行
    為本身可能是演算法正確性的一部分，轉換 agent 要針對每個運算式自己
    判斷是否需要顯式 `& 0xFFFFFFFF`/`& 0xFFFF`，不能假設「反正是無號整
    數運算就不需要 mask」。
    （來源：domain skill「新語言 library 文件」小節最後一條）

## Deviation log

（轉換迴圈執行中若發現規則缺口，記錄在這裡；本檔案在迴圈內唯讀，此區塊由
人類在批次之間維護。目前無項目。）
