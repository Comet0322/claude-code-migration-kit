---
name: legacy-200-delphi
description: >
  部門 200 Delphi 舊應用的來源端知識（私有套件文件、來源語言執行環境、
  Fingerprint）。同一批 Delphi 原始碼被規劃遷移到兩個不同目標語言
  （`domain-200-delphi-java`、`domain-200-delphi-python`），來源端事實跟
  目標語言無關，抽成這裡共用，不在兩個 domain skill 裡各填一份。理解／維
  護這批 Delphi 舊程式碼本身（不只是遷移）時也適用。刻意不用 `domain-`
  開頭——這不是可以被 `migration-clarify` 直接選中的 domain skill，只被
  上述兩個 domain skill 引用。
---

# 部門 200 Delphi 舊應用：來源端知識

## 涵蓋範圍 / Fingerprint

- 所有單元都會 `uses Dept200Data, Dept200Log;`——部門 200 自己的私有
  package，打包在 `Dept200Common.dpk`。
- 專案根目錄下有 `app.ini`，含 `[DB]` 區段跟 `ConnString=` 設定。
- 進入點檔名是 `*.dpr`，跟 `Dept200Data.pas` / `Dept200Log.pas` 兩個私有
  unit 放在同一層或 `common/` 子目錄。

## 私有套件文件

這個私有套件的實作以原始碼形式跟著每個 app 一起放在 repo 裡：
**`Dept200Data.pas`、`Dept200Log.pas`**。migration-clarify 比對
`modules.tsv` 時，這兩個檔案對應到的 unit 要標記成 `excluded`——它們是
套件本身的實作，不是應用程式邏輯，目標端已經有 `python-corplib`/
`java-corplib` 取代，不需要逐行翻譯，只需要轉換其他 unit 裡呼叫它們的
地方。

### `Dept200Data.pas`——`TDBConnection` class

```pascal
var
  Conn: TDBConnection;
begin
  Conn := TDBConnection.Create(ReadIniConnString('app.ini'));
  try
    Rows := Conn.Query('SELECT id, name FROM users WHERE dept = :dept',
                        ['dept', '200']);
    Conn.Execute('UPDATE users SET name = :name WHERE id = :id',
                 ['name', 'foo', 'id', 1]);
  finally
    Conn.Free;
  end;
end;
```

- 底層是 BDE 連到 MS SQL Server（跟 `corplib` 系列連的是同一台）。
- `TDBConnection` 沒有內建交易介面，呼叫端要自己包
  `Conn.BeginTransaction` / `Conn.Commit` / `Conn.Rollback`——這點跟
  `python-corplib`/`java-corplib` 的 `transaction()` 自動 commit/rollback
  不同，是語法轉換規則裡要特別處理的落差，兩個 domain skill 都要記。

### `Dept200Log.pas`——`LogMessage` procedure

```pascal
LogMessage(llInfo, 'fetched user', ['unit_id=u123', 'user_id=1']);
LogMessage(llError, 'db timeout', ['unit_id=u123']);
```

- 寫到本機 `logs/<date>.log` 純文字檔，格式是
  `[時間] [等級] message key=value ...`，不是 JSON——轉去
  `corplib`/`java-corplib` 的 JSON line logger 時，key=value 這幾個欄位
  要拆出來塞進 `extra`/`Map`。

## 來源語言執行環境（選填）

未知，需要在 migration-clarify 階段當場確認——這台機器不一定裝得起 Delphi
7 IDE/命令列編譯器（`dcc32`）。沒有的話走 snapshot 或 inference 層級。
