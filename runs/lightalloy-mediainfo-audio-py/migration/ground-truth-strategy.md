# Ground truth strategy — runs/lightalloy-mediainfo-audio-py

Tier 選定：**混合（11 個 snapshot / 11 個 inference，逐檔決定，見下表）**

## 決策過程

依 migration-clarify 三層順序檢查：

1. **tier: environment** — 不採用。唯讀查詢確認這台機器沒有可用的來源
   語言執行環境：`which dcc32` → not found，`which fpc` → not found。跟
   `runs/lightalloy-crc32-py` 那次是同一台機器、同一個結論，但這次是獨
   立重新查詢過的，不是沿用另一個 run 的結論。
2. **tier: snapshot** — 部分採用。凡是有公開發表、有足夠信心手動核對到
   位元精確的格式規格，用這層：依公開規格文件手動構造已知輸入的 byte
   序列，而不是執行 Delphi 程式碼。
3. **tier: inference** — 部分採用。沒有公開規格、或格式複雜到沒有把握
   手動驗證正確性的，誠實標成這層，並在對應的
   `migration/behavior-snapshots/<unit_id>.md` 標上 `INFERRED, NOT
   VERIFIED`，不偽裝成已驗證的行為。

## 逐檔分層決定（依「對這個格式規格的實際信心」判斷，不是猜）

**snapshot（11 個）**：

| unit_id | 依據 |
|---|---|
| atlID3v1 | ID3v1 是公開、極簡單的固定 128 bytes 格式（TAG 開頭 + 固定欄位 + genre 索引），可手動構造。 |
| atlID3v2 | id3.org 公開規格（ID3v2.2/2.3/2.4），header + 常見 text frame 佈局可手動構造；只涵蓋核心欄位，不保證涵蓋所有少見 frame 型別的邊界案例。 |
| atlAPEtag | APE tag 公開規格（'APETAGEX' magic，header/footer 32 bytes 佈局），可手動構造。 |
| atlFLACfile | xiph.org 公開 FLAC 格式規格（'fLaC' magic + STREAMINFO 等 metadata block），可手動構造，僅涵蓋 metadata 讀取（不含音訊解碼，這個 unit 本來就不做解碼）。 |
| atlOggVorbis | xiph.org 公開 Ogg container + Vorbis comment 規格，'OggS' magic 可手動構造；**注意**：`CalculateCRC`（L522-537）用的是 Ogg 自訂 CRC 多項式（非標準 CRC32），要對照公開規格的多項式手動推導，不能拿 `zlib.crc32` 頂替驗證。 |
| atlVorbisComment | 同上，Vorbis comment 是公開規格的一部分。 |
| atlSpeex | Speex header 格式（公開文件）核心欄位（版本字串、sample rate、channels 等）有信心手動構造；自訂 CRC（L408-423）跟 atlOggVorbis 一樣需要對照公開多項式推導。 |
| atlWAVfile | RIFF/WAVE 是最廣為人知的公開格式，**而且這個 repo 裡真的找到一個現成的真實範例檔** `lightalloy-delphi7/source-repo/Source/!Res/!Unpack/CLICK.wav`（1792 bytes，標準 44-byte PCM header，已用 `xxd` 核對 `RIFF`/`WAVE`/`fmt `/`data` 欄位），是本批 ground truth 證據最強的一個——可以直接對這個真實檔案的 hex dump 建立 snapshot，不只是手動構造假想輸入。 |
| atlTTA | True Audio header 格式簡單（'TTA1' 簽章 + 固定欄位），公開規格可手動構造。 |
| atlCDAtrack | 不是音訊格式問題，是 `cdplayer.ini` 這個標準 Windows INI 格式的解析，INI 語法本身簡單、可手動構造已知輸入輸出配對。 |
| atlAACfile | ADTS header 佈局（7-9 bytes 固定欄位，含 13 個公開發表的取樣率對照表）是相對常見、有信心手動構造到位元精確的部分；**只涵蓋 ADTS**，ADIF header 或更少見的變體如果轉換時遇到，要另外評估，不預設涵蓋在這次 snapshot 範圍內。 |

**inference（11 個，明確標記 `INFERRED, NOT VERIFIED`）**：

| unit_id | 為什麼不用 snapshot |
|---|---|
| atlMPEGaudio | MPEG audio frame header 是位元級精密編碼（bitrate/sample rate/padding 多個表格交叉查表 + Xing/VBR header 偵測），沒有把握手動構造到位元精確且自信驗證無誤。 |
| atlWMAfile | WMA/ASF 容器是巢狀 TLV 結構，物件種類多、GUID 對照表龐雜，沒有把握手動驗證。 |
| atlMonkey | Monkey's Audio (APE codec) 是 proprietary 壓縮格式，檔頭版本演進（新舊 3 種）細節沒有足夠公開規格可信心核對。 |
| atlMPEGplus | Musepack/MPEG+ SV7 是社群格式，缺乏有信心逐位元核對的公開規格文件。 |
| atlMusepack | 同上（兩個檔案是同一格式家族的不同版本讀取器）。 |
| atlWAVPackfile | WavPack 有公開格式但版本演進複雜（header3/header4 兩種佈局），沒有把握逐版本手動驗證到位元精確；tag 部分因為委派給 atlAPEtag，那部分繼承 atlAPEtag 的 snapshot 基礎，但 WavPack 原生 header 解析本身仍標 inference。 |
| atlOptimFROG | 相對冷門的 proprietary 壓縮格式，沒有足夠公開規格細節。 |
| atlTwinVQ | Yamaha TwinVQ 是較冷門的舊格式，沒有足夠公開規格細節。 |
| atlAC3 | Sync word（0x0B77）本身公開，但完整 bitstream 欄位（bitrate code、sample rate code 等對照表）沒有把握逐條手動驗證到位元精確——寧可保守標 inference，也不要對著記憶裡不確定的表格數字硬寫 snapshot。 |
| atlDTS | DTS Coherent Acoustics 是較少公開細節文件的 proprietary 格式，沒有把握手動驗證。 |
| atlFPLfile | 不是公開音訊格式，是 Light Alloy 自家 proprietary playlist 格式（自訂位元組加總校驗），沒有任何外部權威可查——這個案例甚至比「複雜到沒把握」更明確：它本來就不存在公開規格，inference 是唯一選項。 |

## 給 migration-test-writer 的提醒

- snapshot tier 的 11 個檔案裡，`atlOggVorbis`/`atlSpeex` 的自訂 CRC 多
  項式**不是**標準 CRC32，不能拿 `zlib.crc32` 驗證，要自己依公開的 Ogg
  CRC 規格手動推導/實作一份獨立於待測程式碼的參考實作來核對。
- `atlWAVfile` 有真實範例檔可用（見上表），優先拿它建 snapshot，比純手
  動構造假想輸入更可靠。
- inference tier 的 11 個檔案，`behavior-snapshots/<unit_id>.md` 跟對應
  測試檔案裡，斷言依據要明確標註 `INFERRED, NOT VERIFIED`，並寫清楚推
  論依據是讀了原始 Pascal 程式碼的哪一段邏輯，不要讓人誤以為是已驗證的
  行為。
- 具體每個 unit 的 `behavior-snapshots/<unit_id>.md` 內容由
  migration-test-writer 在 migration-convert 階段、該 unit 真正被處理到
  時才產生（22 個檔案在 clarify 階段就全部做完不合理，只有進 pilot 的
  才需要先做）。
