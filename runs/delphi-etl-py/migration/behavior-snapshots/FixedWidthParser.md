# Behavior snapshot — FixedWidthParser (ParseSalesLine)

來源：人類依固定寬度欄位規格文件手動推導（不是實測 Delphi 輸出）——見
`migration/ground-truth-strategy.md` 的 tier 決策。欄位配置定義在
`../../fixtures/delphi-etl/legacy/FixedWidthParser.pas` 的註解：

```
1-10  CustomerId (space-padded)
11-18 Date as YYYYMMDD (11-14 年, 15-16 月, 17-18 日)
19-28 Amount as zero-padded integer cents
29-30 Currency code
```

## 案例 1：一般情況

輸入行（30 字元）：`CUST0001  202403150000123456US`

| 欄位 | 原始子字串 (1-based) | 預期值 |
|---|---|---|
| CustomerId | `CUST0001  `（1-10） | `"CUST0001"`（trim 掉尾端空白） |
| SaleDate | `2024`+`03`+`15`（11-18） | `"2024-03-15"` |
| AmountCents | `0000123456`（19-28） | `123456` |
| CurrencyCode | `US`（29-30） | `"US"` |

## 案例 2：CustomerId 內部含連續空白（驗證 Trim 只去頭尾，不動中間）

輸入行：`AB  CD    202401010000000100JP`

| 欄位 | 原始子字串 | 預期值 |
|---|---|---|
| CustomerId | `AB  CD    `（10 碼） | `"AB  CD"`（頭尾空白去掉，中間兩個空白保留） |
| SaleDate | `2024`+`01`+`01` | `"2024-01-01"` |
| AmountCents | `0000000100` | `100` |
| CurrencyCode | `JP` | `"JP"` |

## 案例 3：金額轉換失敗（非數字）應該拋例外，不是回傳預設值

輸入行：`CUST0002  20240101ABCDEFGHIJUS`

- Amount 欄位 `ABCDEFGHIJ` 不是數字：預期拋出例外（對應 Pascal
  `StrToInt` 的 `EConvertError`；Python `int()` 天生會拋
  `ValueError`）。**不應該**回傳 `0` 或任何預設值。

## 未涵蓋

- 金額超過 10 位數上限時的邊界行為（例如全 9）：這個 fixture 沒有真實
  Delphi 環境可以驗證 32-bit 整數溢位是否會拋例外或靜默環繞，本 snapshot
  不提供這個案例的預期值。如果轉換/測試遇到這個邊界，依
  `migration/ground-truth-strategy.md` 沒有涵蓋的部分處理——用最保守的方
  式（不假設會溢位，因為 Python `int` 是任意精度）並標記為
  `INFERRED, NOT VERIFIED`，不要當作 snapshot 已驗證過的行為。
