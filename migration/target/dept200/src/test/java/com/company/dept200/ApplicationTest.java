package com.company.dept200;

import com.company.dept200.job.UserSyncJob;
import org.junit.jupiter.api.Test;
import org.springframework.boot.CommandLineRunner;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertSame;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;

/**
 * 對照 Delphi 原始碼 migration/legacy/App.dpr（{@code program App; uses Dept200Data,
 * Dept200Log, UserSync; begin UserSync.RunNightlySync; end.}）推論而來的行為測試。
 *
 * <p>Ground truth tier: INFERENCE（見 migration/ground-truth-strategy.md）——這台機器沒有
 * Delphi 執行環境，本檔案所有斷言都是「讀 Delphi 原始碼 + java-corplib / domain-200-delphi-java
 * skill 的模板規則」推論出的行為，沒有實際執行 Delphi 程式驗證過。不過 {@code App.dpr} 本身
 * 只有一行邏輯（呼叫 {@code UserSync.RunNightlySync}），這裡的斷言風險主要不是來自 Delphi
 * 語意本身，而是來自「java-corplib 模板規定的批次 process 骨架」該怎麼組裝——見下方個別
 * 測試方法上的標記。
 *
 * <p><b>本測試假設的 {@code Application} 介面（轉換 agent 請依此實作）：</b>
 * <pre>
 *   {@literal @}SpringBootApplication
 *   public class Application implements CommandLineRunner {
 *       public Application(UserSyncJob userSyncJob) { ... }   // 建構子注入，方便測試直接 new
 *       public static void main(String[] args) {
 *           SpringApplication.run(Application.class, args);
 *       }
 *       {@literal @}Override
 *       public void run(String... args) throws Exception {
 *           userSyncJob.run();   // 依序呼叫各 job；目前只有一個 job
 *       }
 *   }
 * </pre>
 *
 * <p>刻意選擇「直接 {@code new Application(mockJob)}」而不是 {@code @SpringBootTest} 啟動
 * 完整 Spring context：{@code CorplibConfig} 組 {@code UserSyncJob} bean 時會呼叫
 * {@code Database.fromEnv()}，這個方法會讀 {@code CORPLIB_DB_DSN} 環境變數並嘗試建立
 * HikariCP 連線池；測試環境沒有這個環境變數、也沒有可連的 DB，啟動完整 context 會很脆弱
 * （或需要額外 mock 整個 Spring context，殺雞用牛刀）。這裡只驗證
 * {@code Application.run(String...)} 這個方法本身的組裝/例外傳播邏輯，不驗證 Spring
 * wiring 本身——Spring wiring（{@code CorplibConfig} 怎麼組 bean）不在這個 unit 的測試範圍，
 * 屬於 {@code config} 那個檔案的責任。
 */
class ApplicationTest {

    // --- Application 要實作 CommandLineRunner，才會被 Spring Boot 在啟動後自動呼叫 run() ---
    // 對照模板規則：「Application.java # 進入點：SpringApplication.run，實作
    // CommandLineRunner，依序執行各 job 後結束（不是常駐服務）」。
    @Test
    void application_implementsCommandLineRunner() {
        UserSyncJob job = mock(UserSyncJob.class);
        Application app = new Application(job);

        assertTrue(app instanceof CommandLineRunner,
                "Application 必須實作 CommandLineRunner 才會被 Spring Boot 啟動流程呼叫 run()");
    }

    // --- run() 呼叫注入的 UserSyncJob.run()，且不吞掉/不改寫任何行為 ---
    // 對照 Delphi: begin UserSync.RunNightlySync; end. —— App.dpr 本身除了呼叫這一個
    // 動作之外沒有任何其他邏輯（沒有額外的 log、沒有額外的條件判斷）。
    @Test
    void run_invokesUserSyncJobExactlyOnce() {
        UserSyncJob job = mock(UserSyncJob.class);
        Application app = new Application(job);

        assertDoesNotThrow(() -> app.run());

        verify(job, times(1)).run();
    }

    // --- run() 用不同的 varargs 呼叫（模擬 Spring Boot 實際傳入的 command-line args）
    // 仍然正常呼叫 job，不因為有沒有 args 而改變行為 ---
    // INFERRED, NOT VERIFIED: Delphi 的 App.dpr 是一個沒有參數的 program，原始行為完全沒有
    // "命令列參數" 這個概念；這裡假設轉換後 Application.run(String... args) 忽略 args，
    // 純粹是因為 CommandLineRunner 介面簽名要求，不是因為讀到任何舊行為要求要處理參數。
    @Test
    void run_ignoresArgsAndStillInvokesJob() {
        UserSyncJob job = mock(UserSyncJob.class);
        Application app = new Application(job);

        assertDoesNotThrow(() -> app.run("--some-flag", "value"));

        verify(job, times(1)).run();
    }

    // --- run() 不能吞掉 job 拋出的未捕捉例外：模板規則明講「CommandLineRunner.run() 裡任何
    // 一個 job 拋出未捕捉的例外，要讓整個 process 以非 0 exit code 結束，不要吞掉錯誤讓
    // process 看起來正常結束」。
    //
    // 注意：真正的 UserSyncJob.run()（已經過審查）保證不會拋例外——這是 user_sync 專屬、
    // 已拍板的營運決策，這裡不是要反過來要求 UserSyncJob 拋例外。這個測試用一個「假想會拋
    // 例外的 job」（用 mock 的 UserSyncJob 讓 run() 拋例外）驗證的是 Application 這一層
    // 本身有沒有畫蛇添足地包一個 try/catch 吞掉例外——如果之後這批應用加了其他真的會拋例外
    // 的 Job，Application 的組裝邏輯不應該擋住例外往外傳。
    @Test
    void run_doesNotSwallowExceptionThrownByJob() {
        UserSyncJob job = mock(UserSyncJob.class);
        RuntimeException boom = new RuntimeException("boom from a hypothetical future job");
        doThrow(boom).when(job).run();

        Application app = new Application(job);

        RuntimeException thrown = assertThrows(RuntimeException.class, () -> app.run());
        assertSame(boom, thrown,
                "Application.run() 不應該包 try/catch 吞掉 job 拋出的例外或換成別的例外物件，"
                        + "應該讓原始例外原封不動往外傳，交給 Spring Boot / JVM 的預設未捕捉例外"
                        + "處理機制去讓 process 以非 0 exit code 結束");
    }
}
