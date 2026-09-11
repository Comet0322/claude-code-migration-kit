# settings.deny.json — 轉換迴圈的 guardrail

這是 `migration-convert` skill 開跑前檢查的東西。三個 subagent
（`migration-test-writer` / `migration-converter` / `migration-test-reviewer`）
已經各自用 `tools:` 白名單擋掉了不該有的能力（converter 沒有 Bash、writer
跟 reviewer 沒有 Write/Edit），這份設定是**再加一層兜底**：不管哪個角色，
整個 session 都不該在轉換迴圈跑的時候動版控。

## 安裝方式

**由人類手動安裝，不要讓 agent 自己編輯 `.claude/settings.json`。**

- 目標 repo 還沒有 `.claude/settings.json`：直接複製這份檔案過去，改檔名成
  `.claude/settings.json`。
- 已經有：把這份檔案 `permissions.deny` 陣列裡的項目，合併進既有設定的
  `permissions.deny` 陣列。

## 什麼時候裝、什麼時候解除

- 裝的時機：`migration-clarify` 完成、要開始跑 pilot-manifest 之前。
  `migration-convert` 開跑前會檢查這個檔案存在，沒有就停下來告訴你要加什
  麼，不會自己補。
- 整個批次（所有 pilot + 完整 manifest）期間都應該保持啟用。
- 這份 kit 目前的範圍只到「轉換完成、每個 unit 測試通過」，不包含原始 kit
  裡那種「編譯階段放寬 typecheck deny」的 dissolve 機制——如果之後擴充到
  build/run 階段，才需要再討論要不要放寬。

## 為什麼不讓 agent 自己裝

自我修改防護是故意的：一個在迴圈裡跑的 agent，如果自己有能力修改限制它
的設定，這個限制就形同虛設。原本的 code-migration-kit-with-claude-code 也
是同一條紀律——被擋下來是設計在運作，不是要繞過的障礙。
