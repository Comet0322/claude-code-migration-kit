# settings.deny.json — 轉換迴圈的 guardrail

這是 `migration-convert` skill 開跑前檢查的東西。三個 subagent
（`migration-test-writer` / `migration-converter` / `migration-test-reviewer`）
已經各自用 `tools:` 白名單擋掉了不該有的能力（converter 沒有 Bash、writer
跟 reviewer 沒有 Write/Edit），這份設定是**再加一層兜底**：不管哪個角色，
整個 session 都不該在轉換迴圈跑的時候動版控，也不該安裝軟體/套件。

後面這條（禁止安裝軟體）是實測出來的教訓：曾經真實發生 test-writer 找不到
來源語言的編譯器，自己執行 `brew install fpc` 把編譯器裝到機器上。這份
deny 清單能擋掉常見套件管理員的 `install` 指令（`brew`/`apt`/`pip`/`npm`/
`gem`/`go`/`cargo`），但**這只是防止手滑的兜底，不是完整防線**——deny
清單只能列出「已知」的安裝方式，真正防止繞過的是
`migration-test-writer.md`/`migration-test-reviewer.md` 裡明講「不能安裝
軟體、環境不夠用就停下來回報」，以及 `migration-clarify` 在釐清需求跟 Gap
階段就先問清楚有沒有可用執行環境（見該 skill 的「取得 ground truth 的方
式」小節），從源頭消除 test-writer 需要自己生出一個環境的動機。

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
- 這份 kit 的範圍到「轉換完成、每個 unit 測試通過、加一次輕量整合
  build/run 檢查」為止（`migration-convert` 全部 unit pass 後自動跑一
  次，見該 skill 的「全部 unit 通過後的整合檢查」小節）。不包含原始 kit
  裡那種「編譯階段放寬 typecheck deny、錯誤變機器佇列」的重量級 dissolve
  機制——那是為大規模批次設計的，這裡用不到，如果之後真的要擴充到那個規
  模，才需要再討論要不要放寬。

## 為什麼不讓 agent 自己裝

自我修改防護是故意的：一個在迴圈裡跑的 agent，如果自己有能力修改限制它
的設定，這個限制就形同虛設。原本的 code-migration-kit-with-claude-code 也
是同一條紀律——被擋下來是設計在運作，不是要繞過的障礙。
