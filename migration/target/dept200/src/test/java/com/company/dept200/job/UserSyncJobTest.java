package com.company.dept200.job;

import com.company.corplib.db.Database;
import com.company.corplib.logging.Loggers;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertSame;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyMap;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * 對照 Delphi 原始碼 migration/legacy/UserSync.pas 的 RunNightlySync / SyncPendingUsers
 * 推論而來的行為測試。
 *
 * <p>Ground truth tier: INFERENCE（見 migration/ground-truth-strategy.md）——這台機器沒有
 * Delphi 執行環境，本檔案所有斷言都是「讀 Delphi 原始碼 + domain skill 的語法轉換規則表」
 * 推論出的行為，沒有實際執行 Delphi 程式或人工資料驗證過。標記 {@code INFERRED, NOT VERIFIED}
 * 的斷言風險相對更高，其餘則是從原始碼結構直接、低風險翻譯過來的行為（例如 rulebook 已經
 * 明確決定的例外契約、型別窄化、null 語意）。詳細風險清單見交付時附上的「行為觀察筆記」。
 *
 * <p>本測試假設 {@code UserSyncJob} 的建構子簽名如下（轉換 agent 請依此實作，
 * 以便本測試可以注入 mock；轉換 agent 若要另外提供給 Spring 用的 no-arg / 
 * {@code @Autowired} 建構子，可以疊加，但下面這個兩參數建構子必須保留）：
 * <pre>
 *   public UserSyncJob(Database db, Loggers.Logger logger)
 *   public void run()
 * </pre>
 */
class UserSyncJobTest {

    private Database db;
    private Database.Session session;
    private Database.Transaction tx;
    private Loggers.Logger logger;
    private UserSyncJob job;

    @BeforeEach
    void setUp() {
        db = mock(Database.class);
        session = mock(Database.Session.class);
        tx = mock(Database.Transaction.class);
        logger = mock(Loggers.Logger.class);

        when(db.session()).thenReturn(session);
        when(db.transaction()).thenReturn(tx);

        job = new UserSyncJob(db, logger);
    }

    // --- Path 1：今天已經同步過 -> 直接 skip，不開交易，不做任何寫入 ---
    // 對照 Delphi: ExistingCount > 0 -> LogMessage(llInfo, 'sync already ran today, skipping',
    // ['dept=200']); Exit;  （在 BeginTransaction 之前就返回）
    @Test
    void run_skipsAndLogsInfo_whenAlreadySyncedToday() {
        // INFERRED, NOT VERIFIED: fetchOne 回傳 row 的 key 假設為 "cnt"（對應 SQL 中的
        // `AS Cnt` 別名，大小寫是用最literal的方式對應，真實大小寫取決於轉換 agent 怎麼寫
        // SQL / corplib 底層 JDBC driver 的 ResultSetMetaData.getColumnLabel 行為，這台機器
        // 無法實際跑 DB 驗證）。同時把 fetchAll 也 stub 成回傳同一筆資料，避免測試綁死在
        // 「一定是呼叫 fetchOne 而非 fetchAll」這個次要實作選擇上。
        Map<String, Object> countRow = Map.of("cnt", 1L);
        when(session.fetchOne(anyString(), anyMap())).thenReturn(countRow);
        when(session.fetchAll(anyString(), anyMap())).thenReturn(List.of(countRow));

        assertDoesNotThrow(() -> job.run());

        // 不應該進入交易區塊：Delphi 在 Exit 之前完全沒呼叫 BeginTransaction
        verify(db, never()).transaction();

        @SuppressWarnings("unchecked")
        ArgumentCaptor<Map<String, Object>> infoParams = ArgumentCaptor.forClass(Map.class);
        verify(logger).info(eq("sync already ran today, skipping"), infoParams.capture());
        assertEquals("200", String.valueOf(infoParams.getValue().get("dept")));

        verify(logger, never()).error(anyString(), anyMap());
        verify(logger, never()).error(anyString(), anyMap(), any());

        // try-with-resources 應該把查詢用的 session 關掉
        verify(session).close();
    }

    // --- Path 2：還沒同步過，批次寫入全部成功 -> commit，記錄成功筆數 ---
    // 對照 Delphi: BeginTransaction; RowCount := SyncPendingUsers(Conn); Conn.Commit;
    // LogMessage(llInfo, 'nightly sync completed', ['unit_id=user_sync', 'rows=' + IntToStr(RowCount)]);
    @Test
    void run_syncsPendingUsersAndCommits_whenNotYetSyncedToday() {
        Map<String, Object> countRow = Map.of("cnt", 0L);
        when(session.fetchOne(anyString(), anyMap())).thenReturn(countRow);
        when(session.fetchAll(anyString(), anyMap())).thenReturn(List.of(countRow));

        // id 一律當 long 處理（rulebook 型別窄化決定），name 當 String
        Map<String, Object> row1 = Map.of("id", 1L, "name", "Alice");
        Map<String, Object> row2 = Map.of("id", 2L, "name", "Bob");
        when(tx.fetchAll(anyString(), anyMap())).thenReturn(List.of(row1, row2));

        assertDoesNotThrow(() -> job.run());

        verify(db).transaction();

        @SuppressWarnings("unchecked")
        ArgumentCaptor<Map<String, Object>> execParams = ArgumentCaptor.forClass(Map.class);
        verify(tx, times(2)).execute(anyString(), execParams.capture());
        List<Map<String, Object>> capturedExecs = execParams.getAllValues();
        // 對照 Delphi: Conn.Execute('UPDATE users SET name = :name WHERE id = :id',
        //   ['name', Rows[RowIndex].Name, 'id', Rows[RowIndex].Id]) —— 逐列把 id/name 帶進更新參數
        assertEquals("1", String.valueOf(capturedExecs.get(0).get("id")));
        assertEquals("Alice", String.valueOf(capturedExecs.get(0).get("name")));
        assertEquals("2", String.valueOf(capturedExecs.get(1).get("id")));
        assertEquals("Bob", String.valueOf(capturedExecs.get(1).get("name")));

        verify(tx).commit();

        @SuppressWarnings("unchecked")
        ArgumentCaptor<Map<String, Object>> infoParams = ArgumentCaptor.forClass(Map.class);
        verify(logger).info(eq("nightly sync completed"), infoParams.capture());
        Map<String, Object> capturedInfo = infoParams.getValue();
        assertEquals("user_sync", String.valueOf(capturedInfo.get("unit_id")));
        // INFERRED, NOT VERIFIED: rows 的值用 String.valueOf 比對，接受 "2"（String）或 2（Integer/Long）
        // 兩種型別呈現方式，因為 Delphi 原始碼是把 IntToStr(RowCount) 接成字串再塞進 key=value 陣列，
        // 但轉換到 Map<String,Object> 時轉換 agent 可能選擇保留數值型別而非字串，這裡不對型別鎖死。
        assertEquals("2", String.valueOf(capturedInfo.get("rows")));

        verify(logger, never()).error(anyString(), anyMap());
        verify(logger, never()).error(anyString(), anyMap(), any());

        verify(session).close();
        verify(tx).close();
    }

    // --- Path 3：批次寫入失敗 -> 不 commit、記錄 error log、run() 正常返回（不往外拋例外） ---
    // 對照 Delphi: try ... except on E: Exception do begin Conn.Rollback;
    //   LogMessage(llError, 'nightly sync failed: ' + E.Message, ['unit_id=user_sync']); end;
    //   （被 except 接住之後就結束 RunNightlySync，不重新 raise）
    //
    // rulebook 已明確決定：UserSyncJob.run() 沿用「內部捕捉、不往外拋」這個行為，
    // 所以本測試斷言 run() 不拋例外，而不是斷言它應該拋例外。
    @Test
    void run_doesNotThrowAndLogsError_whenBatchWriteFails() {
        Map<String, Object> countRow = Map.of("cnt", 0L);
        when(session.fetchOne(anyString(), anyMap())).thenReturn(countRow);
        when(session.fetchAll(anyString(), anyMap())).thenReturn(List.of(countRow));

        Map<String, Object> row1 = Map.of("id", 1L, "name", "Alice");
        when(tx.fetchAll(anyString(), anyMap())).thenReturn(List.of(row1));

        RuntimeException boom = new RuntimeException("boom");
        doThrow(boom).when(tx).execute(anyString(), anyMap());

        assertDoesNotThrow(() -> job.run());

        // corplib-java 0.1.0 的 Database$Transaction 沒有公開的 rollback() 方法：
        // Transaction.close() 只有在「沒呼叫過 commit()」時，才會對底層 JDBC connection 做
        // rollback（見 corplib-java-0.1.0.jar 的 Database$Transaction.close() bytecode）。
        // 所以在 mock 這一層邊界上，「有沒有 rollback」只能透過「commit() 沒被呼叫、
        // close() 有被呼叫（觸發 try-with-resources 的隱含 rollback）」間接驗證，
        // 沒有一個獨立可 verify 的 rollback() 呼叫可供斷言。
        verify(tx, never()).commit();
        verify(tx).close();

        @SuppressWarnings("unchecked")
        ArgumentCaptor<Map<String, Object>> errorParams = ArgumentCaptor.forClass(Map.class);
        ArgumentCaptor<Throwable> errorCause = ArgumentCaptor.forClass(Throwable.class);
        verify(logger).error(eq("nightly sync failed: boom"), errorParams.capture(), errorCause.capture());
        assertEquals("user_sync", String.valueOf(errorParams.getValue().get("unit_id")));
        assertSame(boom, errorCause.getValue());

        verify(logger, never()).info(eq("nightly sync completed"), anyMap());

        verify(session).close();
    }
}
