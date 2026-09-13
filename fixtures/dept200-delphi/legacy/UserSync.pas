unit UserSync;

interface

procedure RunNightlySync;

implementation

uses
  Dept200Data, Dept200Log, SysUtils, Classes;

// Extract：從 staging_users 撈出這個部門待同步的資料
// Load：逐列寫回 users 表——同一個私有套件、同一個 DB，沒有外部檔案介入
// （Rows 的存取方式是 fixture 示意寫法，實際型別依 BDE 回傳的 dataset 而定）
function SyncPendingUsers(Conn: TDBConnection): Integer;
var
  Rows: Variant;
  RowIndex, Count: Integer;
begin
  Count := 0;
  Rows := Conn.Query('SELECT id, name FROM staging_users WHERE dept = :dept', ['dept', '200']);
  for RowIndex := VarArrayLowBound(Rows, 1) to VarArrayHighBound(Rows, 1) do
  begin
    Conn.Execute('UPDATE users SET name = :name WHERE id = :id',
      ['name', Rows[RowIndex].Name, 'id', Rows[RowIndex].Id]);
    Inc(Count);
  end;
  Result := Count;
end;

procedure RunNightlySync;
var
  Conn: TDBConnection;
  ExistingCount: Variant;
  RowCount: Integer;
begin
  Conn := TDBConnection.Create(ReadIniConnString('app.ini'));
  try
    // 無交易的查詢：先確認今天還沒同步過
    ExistingCount := Conn.Query(
      'SELECT COUNT(*) AS Cnt FROM sync_log WHERE dept = :dept AND sync_date = :d',
      ['dept', '200', 'd', FormatDateTime('yyyy-mm-dd', Now)]);

    if ExistingCount > 0 then
    begin
      LogMessage(llInfo, 'sync already ran today, skipping', ['dept=200']);
      Exit;
    end;

    // 有手動交易的批次寫入
    Conn.BeginTransaction;
    try
      RowCount := SyncPendingUsers(Conn);
      Conn.Commit;
      LogMessage(llInfo, 'nightly sync completed',
        ['unit_id=user_sync', 'rows=' + IntToStr(RowCount)]);
    except
      on E: Exception do
      begin
        Conn.Rollback;
        LogMessage(llError, 'nightly sync failed: ' + E.Message, ['unit_id=user_sync']);
      end;
    end;
  finally
    Conn.Free;
  end;
end;

end.
