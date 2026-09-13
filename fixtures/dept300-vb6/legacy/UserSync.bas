Attribute VB_Name = "UserSync"
Option Explicit

' 夜間批次工作：從 staging_users 表撈出待同步的資料，寫回 users 表。
' CorpUtil300.dll 是部門 300 的私有 all-in-one library（一個 DLL 裡有
' clsConn 跟 clsEventLogger 兩個 class，早期繫結 COM component；clsConn
' 走 ODBC，Connect 內部讀取 registry HKLM\Software\Dept300\DB\ConnString
' 取得連線字串，沒有交易 API）——查詢跟寫入都透過同一個私有套件對同一個
' DB 操作，不經過任何外部檔案。

Public Sub RunNightlySync()
    Dim Conn As New clsConn
    Dim Logger As New clsEventLogger
    Dim rsExisting As Object
    Dim RowCount As Long

    Conn.Connect

    Set rsExisting = Conn.Exec("SELECT COUNT(*) AS Cnt FROM sync_log WHERE dept = ? AND sync_date = ?", _
                                Array("300", Format(Date, "yyyy-mm-dd")))

    If rsExisting("Cnt").Value > 0 Then
        Logger.Write evtInformation, "sync already ran today, skipping", "dept=300"
        Conn.Disconnect
        Exit Sub
    End If

    ' clsConn 沒有交易 API，每次 Run 呼叫內部就地 commit
    RowCount = SyncPendingUsers(Conn)

    Logger.Write evtInformation, "nightly sync completed", "unit=user_sync,rows=" & RowCount
    Conn.Disconnect
End Sub

' Extract：從 staging_users 撈出這個部門待同步的資料
' Load：逐列寫回 users 表——同一個私有套件、同一個 DB，沒有外部檔案介入
Private Function SyncPendingUsers(ByRef Conn As Object) As Long
    Dim rsPending As Object
    Dim Count As Long

    Set rsPending = Conn.Exec("SELECT id, name FROM staging_users WHERE dept = ?", Array("300"))

    Do While Not rsPending.EOF
        Conn.Run "UPDATE users SET name = ? WHERE id = ?", _
                 Array(rsPending("name").Value, rsPending("id").Value)
        Count = Count + 1
        rsPending.MoveNext
    Loop

    SyncPendingUsers = Count
End Function
