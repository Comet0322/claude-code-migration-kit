# Ground truth 策略

- **tier**: `inference`
- **decision date**: 2026-09-13
- **decided by**: 使用者（jerrymark611@gmail.com）於 migration-clarify 對話中確認

## 理由

1. 這台機器沒有 Delphi 執行環境：`which dcc32` / `which fpc` / `which delphi`
   皆查無結果（唯讀探測，未嘗試安裝）。
2. `legacy-200-delphi` skill 的「來源語言執行環境」小節本身標記為未知，
   需要在本階段當場確認；確認結果是這台機器裝不起來。
3. 詢問使用者是否能提供 mock data / 既有測試案例 / production 資料快照
   （snapshot 層級），使用者選擇跳過，直接接受 `inference` 層級的風險。

## 對測試撰寫 agent 的影響

`dept200_data` / `dept200_log` / `user_sync` 三個 unit 的測試斷言，一律
依據閱讀 `legacy/` 底下的 Delphi 原始碼跟 `legacy-200-delphi` skill 文件
推論出的行為撰寫，**沒有實際執行結果或人工資料驗證**。測試撰寫 agent 不得
自行安裝編譯器或修改本機環境來取得更高層級的 ground truth；如認為某個
unit 的行為推論風險過高，應回報而非自行決定升級層級。
