Attribute VB_Name = "UserSync"
Option Explicit

' 夜間批次工作：從 staging_users 表撈出待同步的資料，寫回 users 表。
' Dept200Common.dll 是部門 200 的私有 all-in-one library（一個 DLL 裡有
' clsDBConn 跟 clsLogger 兩個 class，早期繫結 COM component，DB 底層走
' ADO）——查詢跟寫入都透過同一個私有套件對同一個 DB 操作，不經過任何外部
' 檔案。

Public Sub RunNightlySync()
    Dim Conn As New clsDBConn
    Dim Logger As New clsLogger
    Dim rsExisting As Object
    Dim RowCount As Long

    Conn.Open App.Path & "\app.ini"

    ' 沒有交易包起來的查詢：只是先確認今天還沒同步過
    Set rsExisting = Conn.Query("SELECT COUNT(*) AS Cnt FROM sync_log WHERE dept = ? AND sync_date = ?", _
                                 Array("200", Format(Date, "yyyy-mm-dd")))

    If rsExisting("Cnt").Value > 0 Then
        Logger.LogInfo "sync already ran today, skipping", "dept=200"
        Conn.Close
        Exit Sub
    End If

    ' 有手動交易包起來的批次寫入：全部成功才 commit
    Conn.BeginTrans
    On Error GoTo TransFail

    RowCount = SyncPendingUsers(Conn)

    Conn.CommitTrans
    Logger.LogInfo "nightly sync completed", "unit_id=user_sync;rows=" & RowCount
    Conn.Close
    Exit Sub

TransFail:
    Conn.RollbackTrans
    Logger.LogError "nightly sync failed: " & Err.Description, "unit_id=user_sync"
    Conn.Close
End Sub

' Extract：從 staging_users 撈出這個部門待同步的資料
' Load：逐列寫回 users 表——同一個私有套件、同一個 DB，沒有外部檔案介入
Private Function SyncPendingUsers(ByRef Conn As Object) As Long
    Dim rsPending As Object
    Dim Count As Long

    Set rsPending = Conn.Query("SELECT id, name FROM staging_users WHERE dept = ?", Array("200"))

    Do While Not rsPending.EOF
        Conn.Execute "UPDATE users SET name = ? WHERE id = ?", _
                     Array(rsPending("name").Value, rsPending("id").Value)
        Count = Count + 1
        rsPending.MoveNext
    Loop

    SyncPendingUsers = Count
End Function
