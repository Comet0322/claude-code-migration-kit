# Ground truth strategy — fixtures/delphi-etl

Tier 選定：**snapshot**

## 決策過程（補記，事後修正）

這份 fixture 一開始沒有先跑這一步（migration-clarify 當時還沒有「取得
ground truth 的方式」這一節），導致 `migration-test-writer` 在轉換階段自
己發現沒有 Delphi/Free Pascal 編譯器，並自行執行 `brew install fpc` 把編
譯器裝到機器上取得真實輸出——這是不可接受的行為，詳見
`migration/deviation-log.tsv`（如果已建立）或本次對話紀錄。

補做這一步時的判斷：

1. **tier: environment** — 不採用。這台機器現在雖然裝了 `fpc`，但那是
   agent 未經授權自己裝的，不算「人類事先佈建好的環境」。採用它等於事後
   追認這個行為，會鼓勵同樣的事再發生。domain skill 的「來源語言執行環
   境」小節也明講「未知，不可假設任何一台機器裝得起來」。
2. **tier: snapshot** — 採用。改由人類（此處由設計者本人依固定寬度欄位
   的規格文件手動推導）提供輸入輸出範例，存在
   `migration/behavior-snapshots/FixedWidthParser.md`。
3. **tier: inference** — 不需要，snapshot 已經涵蓋這個 fixture 需要的案
   例。

## 待辦

`target/test/test_fixed_width_parser.py` 是舊流程（agent 自行安裝編譯器
後）產出的，狀態標記在 `migration/state/FixedWidthParser.json` 為
`needs-rerun`——正確流程下應該依這份 snapshot 重新產生測試，不應該繼續信
任舊檔案的斷言依據（即使數值可能剛好相同）。
