package com.company.dept200;

import com.company.dept200.job.UserSyncJob;
import org.springframework.boot.CommandLineRunner;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * 進入點，對照 Delphi 原始碼 migration/legacy/App.dpr：
 * {@code program App; uses Dept200Data, Dept200Log, UserSync; begin UserSync.RunNightlySync; end.}
 *
 * <p>依 RULEBOOK.md「Unit -> Java 類別對應」：{@code app} 對應本類別，實作
 * {@link CommandLineRunner}，依序呼叫各 job（目前只有一個 {@link UserSyncJob}）後結束
 * （批次 process，不是常駐服務）。
 *
 * <p>{@link UserSyncJob} 用建構子注入，方便測試不啟動完整 Spring context 直接
 * {@code new Application(mockJob)}；真正的 wiring（{@code Database.fromEnv()} /
 * {@code Loggers.get(...)} 組裝 {@link UserSyncJob}）由 {@link
 * com.company.dept200.config.CorplibConfig} 負責，不在本類別。
 */
@SpringBootApplication
public class Application implements CommandLineRunner {

    private final UserSyncJob userSyncJob;

    public Application(UserSyncJob userSyncJob) {
        this.userSyncJob = userSyncJob;
    }

    public static void main(String[] args) {
        SpringApplication.run(Application.class, args);
    }

    /**
     * 對照 Delphi {@code begin UserSync.RunNightlySync; end.} —— 除了呼叫這一個動作之外
     * 沒有任何其他邏輯（沒有額外的 log、沒有額外的條件判斷）。
     *
     * <p>刻意不包 try/catch：job 拋出的未捕捉例外必須原封不動往外傳給 Spring Boot 的
     * {@link CommandLineRunner} 執行機制，讓 process 以非 0 exit code 結束，不要吞掉錯誤讓
     * process 看起來正常結束。
     */
    @Override
    public void run(String... args) throws Exception {
        userSyncJob.run();
    }
}
