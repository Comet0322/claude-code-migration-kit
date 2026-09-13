package com.company.dept200.job;

import com.company.corplib.db.Database;
import com.company.corplib.logging.Loggers;

import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.List;
import java.util.Map;

/**
 * 對照 Delphi 原始碼 migration/legacy/UserSync.pas 的 RunNightlySync / SyncPendingUsers。
 *
 * <p>行為對照（逐項見 migration/RULEBOOK.md、migration/inventory.tsv 的 user_sync 條目）：
 * <ul>
 *   <li>今天已經跑過同步（sync_log 的 COUNT(*) > 0）就記一筆 info log 然後直接返回，
 *       不開交易、不做任何寫入。這段查詢在 Delphi 裡沒有被 BeginTransaction 包住，
 *       所以用 {@code db.session()}，不是 {@code db.transaction()}。</li>
 *   <li>還沒跑過的話開交易：撈 staging_users 待同步列（這段在 Delphi 裡是在
 *       BeginTransaction 之後執行的，所以也用同一個 transaction 的
 *       {@code tx.fetchAll(...)}，不是額外開一個 session），逐列 UPDATE users，
 *       全部成功才 commit，並記一筆 info log。</li>
 *   <li>批次寫入任何一步丟例外：rulebook 已明確決定沿用 Delphi 原始行為——捕捉例外、
 *       不 commit（讓 try-with-resources 對還沒 commit 的 transaction 做隱含
 *       rollback）、記一筆 error log，然後 {@code run()} 正常返回，不重新拋出。</li>
 * </ul>
 */
public class UserSyncJob {

    private static final DateTimeFormatter SYNC_DATE_FORMAT = DateTimeFormatter.ofPattern("yyyy-MM-dd");

    private final Database db;
    private final Loggers.Logger logger;

    public UserSyncJob(Database db, Loggers.Logger logger) {
        this.db = db;
        this.logger = logger;
    }

    public void run() {
        String today = LocalDate.now().format(SYNC_DATE_FORMAT);

        long existingCount;
        try (Database.Session session = db.session()) {
            Map<String, Object> countRow = session.fetchOne(
                    "SELECT COUNT(*) AS Cnt FROM sync_log WHERE dept = :dept AND sync_date = :d",
                    Map.of("dept", "200", "d", today));
            // rulebook 決定：fetchOne 的結果視為一定非 null（COUNT(*) 保證回傳一列），
            // 不包 Optional 判斷，直接轉型 long 比較。
            existingCount = (Long) countRow.get("cnt");
        }

        if (existingCount > 0) {
            logger.info("sync already ran today, skipping", Map.of("dept", "200"));
            return;
        }

        try (Database.Transaction tx = db.transaction()) {
            try {
                int rowCount = syncPendingUsers(tx);
                tx.commit();
                logger.info("nightly sync completed",
                        Map.of("unit_id", "user_sync", "rows", rowCount));
            } catch (Exception e) {
                // 不重新拋出：這是舊系統既有的營運決策（同步失敗不視為批次致命錯誤，
                // 下一輪排程會重試），遷移不改變既有行為（見 inventory.tsv exception_contract）。
                // 不呼叫 tx.commit()，讓 try-with-resources 關閉 transaction 時做隱含 rollback。
                logger.error("nightly sync failed: " + e.getMessage(),
                        Map.of("unit_id", "user_sync"), e);
            }
        }
    }

    private int syncPendingUsers(Database.Transaction tx) {
        List<Map<String, Object>> rows = tx.fetchAll(
                "SELECT id, name FROM staging_users WHERE dept = :dept", Map.of("dept", "200"));

        int count = 0;
        for (Map<String, Object> row : rows) {
            // rulebook 型別窄化決定：id 一律當 long、name 一律當 String，不額外做 null 檢查。
            long id = (Long) row.get("id");
            String name = (String) row.get("name");
            tx.execute("UPDATE users SET name = :name WHERE id = :id",
                    Map.of("name", name, "id", id));
            count++;
        }
        return count;
    }
}
