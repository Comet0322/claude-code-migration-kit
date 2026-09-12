# Rulebook — fixtures/toy-app (Python → JavaScript)

Domain skill: `domain-toy-legacy-py2js`。以下規則對轉換 agent 是唯讀的，
不可在迴圈內修改；有缺口就走 Deviation log，交給人類決定。

## 決定

1. **私有套件替換**：`legacycorp_normalize.normalize_name` 不建立對應的
   target 模組，也不可以在任何 target 檔案裡 import 它。呼叫點一律內聯
   `s.trim().toLowerCase().replace(/\s+/g, ' ')`。
   （來源：domain skill 語法轉換規則 #1）
2. **整數除法**：Python 的 `//` 一律換成 `Math.floor(a / b)`。此寫法對負數
   輸入同樣正確（`Math.floor` 跟 Python `//` 都是向負無窮捨去），不需要額
   外處理——pilot 執行時原本寫「僅限非負輸入」，經審查 agent 跟兩個獨立
   test-writer agent 各自驗證後確認是保守誤判，已修正。
   （來源：domain skill 語法轉換規則 #2）
3. **None 的字串顯示行為必須逐字保留**：`display_name` 為 `null` 時，輸出
   字面上的 `"None"` 三個字，不得「修正」成空字串或其他更合理的預設值。
   這是刻意的 bug-for-bug 相容決策，不是本次遷移要改善的範圍。JS 寫法：
   `display_name === null ? "None" : display_name`。
   （來源：domain skill 語法轉換規則 #3；原則依據：舊程式碼是唯一的
   spec，未經人類明確核准不做行為改善）

## Deviation log

（轉換迴圈執行中若發現規則缺口，記錄在這裡；本檔案在迴圈內唯讀，此區塊由
人類在批次之間維護。目前無項目。）
