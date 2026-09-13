package com.company.dept200.config;

import com.company.corplib.db.Database;
import com.company.corplib.logging.Loggers;
import com.company.dept200.job.UserSyncJob;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * corplib wiring：組裝 {@link Database} 跟各個 job bean。
 *
 * <p>依 RULEBOOK.md 種子規則，{@code TDBConnection.Create(ReadIniConnString('app.ini'))}
 * 對應 {@code Database.fromEnv()}——DSN 來源改成環境變數 {@code CORPLIB_DB_DSN}，轉換後不再
 * 讀 ini。{@code application.yml} 裡的 {@code corplib.db.dsn} 欄位是給人類/部署設定看的說明性
 * 配置，{@code Database.fromEnv()} 本身直接讀環境變數，不需要這裡額外解析 yml。
 *
 * <p>{@code Database.fromEnv()} 跟 {@code Loggers.get(...)} 各自在這裡剛好呼叫一次，
 * 不在別的地方重複呼叫（與 {@code user_sync} unit 審查對齊的組裝層決策）。
 */
@Configuration
public class CorplibConfig {

    @Bean
    public Database database() {
        return Database.fromEnv();
    }

    @Bean
    public UserSyncJob userSyncJob(Database database) {
        return new UserSyncJob(database, Loggers.get(UserSyncJob.class));
    }
}
