package com.boogie.sdk.infra;

import com.boogie.sdk.core.InfraException;

import java.time.Duration;
import java.util.List;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CopyOnWriteArrayList;

/**
 * SchedulerClient stub. See boogie-sdk-api.md section 5.2 (infra).
 * Skeleton only — implemented during the Phase 1 TDD loop for the `infra` module.
 */
public class SchedulerClient {

    private final Set<String> heldLocks = ConcurrentHashMap.newKeySet();
    private final List<CronRegistration> registrations = new CopyOnWriteArrayList<>();

    private record CronRegistration(String cronExpr, Runnable task) {
    }

    public Lock lock(String name, Duration ttl) {
        if (!heldLocks.add(name)) {
            throw new InfraException("lock already held: " + name);
        }
        return new NamedLock(name);
    }

    public void scheduleCron(String cronExpr, Runnable task) {
        registrations.add(new CronRegistration(cronExpr, task));
    }

    private final class NamedLock implements Lock {
        private final String name;
        private volatile boolean released = false;

        private NamedLock(String name) {
            this.name = name;
        }

        @Override
        public void release() {
            if (!released) {
                released = true;
                heldLocks.remove(name);
            }
        }
    }
}
