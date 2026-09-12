---
name: domain-toy-legacy-py2js
description: >
  [測試用 domain skill] 涵蓋 fixtures/toy-app 這批小型 Python legacy 工具程
  式，目標語言 JavaScript (Node.js，內建模組即可，不裝任何 npm 套件)。用來
  端到端驗證 migration kit 本身是否穩健，不是真實客戶案例。
---

# domain-toy-legacy-py2js

## 這個 domain skill 涵蓋的應用類型

小型 Python 工具程式（`fixtures/toy-app/legacy/*.py`），依賴 `mathutils`
跟內部私有套件 `legacycorp_normalize`。目標語言 JavaScript（Node.js 內建能
力，不引入任何第三方套件，避免環境限制）。指紋：找得到
`import ... legacycorp_normalize` 字樣、`.py` 副檔名檔案。

## 私有套件文件

`legacycorp_normalize` 是模擬的內部共用套件，只有一個函式
`normalize_name(s)`：去頭尾空白、轉小寫、把中間連續空白壓成單一空白。
**這個模組不可以被逐字翻譯成新語言的對應模組**——見下面替換規則。

## 來源語言執行環境

Python 是直譯語言，一般開發機/CI 環境幾乎都裝有 `python3`，直接執行
`python3 -c "..."` 或跑腳本即可取得真實行為。可視為預設 tier:
`environment` 可用；migration-clarify 仍應照流程用 `which python3` 之類
的唯讀方式確認一次，不要跳過確認直接假設。

## 模板專案

```
fixtures/toy-app/target/
  src/
    mathutils.js
    report.js
  test/
    mathutils.test.js
    report.test.js
```

用 Node 內建的 `node:assert` + `node:test`，不裝任何 npm 套件。**模組系統一律
用 CommonJS（`require` / `module.exports`）**，不用 ESM（沒有
`"type": "module"` 宣告、不用 `import`/`export`）——這條是 pilot 跑完之後補
上的：第一輪測試撰寫 agent 各自獨立猜到同一個答案，但這是運氣，不是保證，
明確寫下來避免下次不同 agent 猜出不同答案導致互相 import 失敗。

## 語法轉換 / library 替換規則

1. **`legacycorp_normalize.normalize_name` 一律替換**，不建立對應的
   `normalize.js` 模組，也不在 `report.js` 裡 import 任何 normalize 相關檔
   案。改成在呼叫點直接內聯以下等價實作：
   `s.trim().toLowerCase().replace(/\s+/g, ' ')`。
   （審查 agent 應該檢查：target 底下沒有多出一個
   normalize 相關的檔案；`report.js` 裡沒有 import 它。）
2. **Python `//`（floor division）一律換成 `Math.floor(a / b)`**。~~這個
   fixture 只考慮非負整數輸入，不處理負數時 `//` 跟 `Math.floor` 捨去方向
   不同的語意差異~~——**這條限制是錯的，pilot 跑完後修正**：`Math.floor`
   在數學上對任何實數輸入都跟 Python `//`（向負無窮捨去）語意一致，跟會
   跟 Python 不同的是「向零截斷」（`Math.trunc`）這種寫法，不是
   `Math.floor`。負數輸入不需要額外處理，`Math.floor(a / b)` 本身就是正確
   答案。
3. **`None` 造成的字串顯示行為必須逐字保留**：Python 對
   `f"...{None}..."` 會印出字面上的 `None` 三個字。新語言**不能**「修正」
   成更合理的行為（例如空字串或 `"unknown"`）——舊程式碼是唯一的 spec，
   這裡刻意選擇 bug-for-bug 相容，不是本次遷移的改善範圍。JS 對應寫法：
   `display_name === null ? "None" : display_name`。

## 新語言 library 文件

只用得到 JS 內建的 `String.prototype.trim` / `toLowerCase` / `replace`、
`Math.floor`、模板字串（``` `...` ```）。不需要任何額外文件。

## 測試 / build 方法

- Build（語法檢查）：對每個 `target/src/*.js` 執行 `node --check <file>`。
- Test：`node --test fixtures/toy-app/target/test`。

## Fingerprint

- 應該找得到字樣 `legacycorp_normalize`。
- 應該找得到 `.py` 副檔名的檔案。
