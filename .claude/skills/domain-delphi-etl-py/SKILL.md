---
name: domain-delphi-etl-py
description: >
  [測試用 domain skill] 涵蓋 fixtures/delphi-etl 這批 Delphi 固定寬度欄位
  ETL 解析程式，目標語言 Python 3（只用標準庫，不裝任何 pip 套件）。用來端
  到端驗證 migration kit 在「來源語言在這個環境裡沒有編譯器/執行環境可跑」
  時是否還穩健，不是真實客戶案例。
---

# domain-delphi-etl-py

## 這個 domain skill 涵蓋的應用類型

Delphi 寫的固定寬度欄位（fixed-width）銷售記錄 ETL 解析器
（`fixtures/delphi-etl/legacy/*.pas`），依賴內部私有業務規則單元
`CurrencyRules`。目標語言 Python 3，只用標準庫。指紋：找得到 `.pas`/`.dpr`
副檔名的檔案；找得到 `uses FixedWidthParser` 或 `uses CurrencyRules` 字樣。

## 私有套件文件

`CurrencyRules.pas` 是模擬的內部業務規則單元，只有一個函式
`NormalizeCurrencyCode(LegacyCode)`：把公司內部使用的 2 碼區域代號對應到
ISO 4217 貨幣代碼（`US`→`USD`、`EU`→`EUR`、`JP`→`JPY`，其他一律
`XXX`）。**這是公司特有的業務資料，不是可以用通用函式庫取代的正規化演算
法**——跟上一個 domain skill（`domain-toy-legacy-py2js`）裡
`legacycorp_normalize` 那種「可以內聯成通用邏輯」的私有套件不同：這裡的
對照表本身就是要保留、原樣搬過去的業務知識，不是可拋棄的實作細節。

## 來源語言執行環境

**未知，不可假設任何一台機器裝得起來。** Delphi 是編譯語言，且是商業授
權（Embarcadero）；就算用相容的 Free Pascal Compiler（`fpc`）替代，也不
是每個環境都會裝。migration-clarify 必須在這個 domain skill 底下每次都當
場確認（`which fpc`／`which dcc32`，唯讀查詢），不能假設前一個 repo 有裝
這次就一定有。沒有的話，依 migration-clarify 的三層規則，優先跟人類要
mock data/snapshot，不要讓任何 agent 自己安裝編譯器。

## 模板專案

```
target/
  src/
    fixed_width_parser.py
    currency_rules.py
    sales_summary.py
  test/
    test_fixed_width_parser.py
    test_currency_rules.py
    test_sales_summary.py
```

用 Python 標準庫的 `unittest`，不裝任何 pip 套件。模組系統就是一般 Python
`import`（無特殊限制）。

沒有單一進入點——這三個 unit 是解析/業務規則函式庫，不是一個有進入點的
程式。整合檢查只需要「全部測試一起跑」，不用執行進入點這項。

外部套件：無，只用 Python 標準庫，不需要 `pip install` 任何東西。

## 語法轉換 / library 替換規則

1. **`Copy(s, start, len)` 是 1-based，Python 切片是 0-based**：一律換算成
   `s[start-1 : start-1+len]`。這是整個 fixture 裡最容易翻錯的地方——每個
   欄位邊界都要重新算一次索引，不能憑感覺平移。
2. **`CurrencyRules.pas` 的對照表要原樣搬成 Python 模組
   `currency_rules.py`**，不可以內聯、不可以用任何通用函式庫取代——這是業
   務資料，不是演算法（見上面私有套件文件那節）。輸出介面：
   `normalize_currency_code(legacy_code: str) -> str`，邏輯逐條對應原
   Pascal 的 if/elif 鏈。
3. **`StrToInt` 轉換失敗時的行為要保留「拋出例外」**，不要吞掉錯誤回傳預
   設值——Delphi 的 `StrToInt` 對非數字字串會拋 `EConvertError`，Python
   對應寫法用 `int(s)`（本身在非數字輸入時就會拋 `ValueError`），不需要額
   外包 try/except 去「優雅處理」。
4. **金額用浮點數除法，不要換成 `Decimal`**：Delphi 原始碼用
   `AmountCents / 100.0`（`Double`），這在數學上跟浮點數二進位表示法有已
   知的精度風險，但這是舊系統本來的行為。維持位元組對位元組的行為一致是
   本次遷移的目標，`Decimal` 雖然「更正確」，但改變了舊系統的數值行為，
   屬於本次遷移範圍外的改善，不要做。Python 對應寫法：
   `amount_cents / 100`。
5. **輸出的小數點符號一律用 `.`，不要重現 Delphi `FormatFloat` 的 locale
   相依行為**：原始碼的 `FormatFloat('0.00', Amount)` 在逗號小數點的作業
   系統 locale 下會輸出 `1234,56` 而不是 `1234.56`——這是舊系統的潛在可攜
   性 bug，不是刻意設計的行為，不屬於「舊程式碼是唯一 spec、要逐字保留」
   的範圍。Python 一律用 `f"{amount:.2f}"`，固定用 `.`，不隨 locale 變
   動。（跟上一個 domain skill 的 None 顯示規則不同：這裡選擇不重現舊系統
   的意外行為，因為它明顯是環境依賴造成的缺陷，而不是設計意圖——這個判斷
   已經在這裡明講，遇到規則衝突不要自己重新判斷。）

## 新語言 library 文件

只用得到 Python 內建的字串切片、`int()`、f-string 格式化
（`f"{x:.2f}"`）。不需要任何額外文件。

## 測試 / build 方法

- Build（語法檢查）：對每個 `target/src/*.py` 執行 `python3 -m py_compile
  <file>`。
- Test：`python3 -m unittest discover -s target/test`（相對於這次遷移的執
  行根目錄 `runs/<這次遷移的名稱>/`，不是這個 domain skill 描述的來源
  `fixtures/delphi-etl/`）。

## Fingerprint

- 應該找得到 `.pas` 或 `.dpr` 副檔名的檔案。
- 應該找得到字樣 `uses FixedWidthParser` 或 `uses CurrencyRules`。
