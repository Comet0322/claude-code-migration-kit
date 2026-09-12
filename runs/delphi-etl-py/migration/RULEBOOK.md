# Rulebook — fixtures/delphi-etl (Delphi → Python)

Domain skill: `domain-delphi-etl-py`。以下規則對轉換 agent 是唯讀的，不可
在迴圈內修改；有缺口就走 Deviation log，交給人類決定。

## 決定

1. **索引換算**：`Copy(s, start, len)`（1-based）→
   `s[start-1 : start-1+len]`（0-based）。每個欄位邊界都要重新計算，不能
   平移既有數字了事。
   （來源：domain skill 語法轉換規則 #1）
2. **`CurrencyRules` 業務對照表原樣搬遷**：獨立成 `currency_rules.py`，不
   內聯、不用通用函式庫取代。這是業務資料，不是可拋棄的實作細節，跟
   `domain-toy-legacy-py2js` 那種私有套件的處理方式不同——**不要套用上一
   個 domain skill 學到的「私有套件一律內聯替換」當通則**，這裡明確是另
   一條規則。
   （來源：domain skill 語法轉換規則 #2）
3. **數字轉換失敗要拋例外，不要吞掉**：`StrToInt` 對應 Python `int()`，兩
   者失敗時都拋例外，不要額外包 try/except 換成預設值。
   （來源：domain skill 語法轉換規則 #3）
4. **金額用浮點數除法，不換成 `Decimal`**：`AmountCents / 100.0` →
   `amount_cents / 100`，維持舊系統原本的浮點精度風險，這是刻意的位元組
   對位元組相容決策，不是遺漏。
   （來源：domain skill 語法轉換規則 #4）
5. **輸出小數點固定用 `.`，不重現 Delphi FormatFloat 的 locale 相依行
   為**：這是本次遷移刻意選擇「不逐字保留舊行為」的例外——因為那是環境
   依賴造成的潛在 bug，不是設計意圖。Python 用 `f"{amount:.2f}"`。
   （來源：domain skill 語法轉換規則 #5；跟規則 3/4「忠實保留」的精神不
   同，這裡刻意不保留，理由已經寫在 domain skill 裡，遇到規則衝突以這條
   明講的例外為準，不要自己重新判斷「應該要忠實保留」）

## Deviation log

（轉換迴圈執行中若發現規則缺口，記錄在這裡；本檔案在迴圈內唯讀，此區塊由
人類在批次之間維護。目前無項目。）
