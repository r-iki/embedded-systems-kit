# FreeRTOS Architecture Patterns

## Task Design & Priority Rules
- **Rate-Monotonic guideline**: Shorter deadlines / faster periodic tasks get higher priorities; slow background tasks (logging, telemetry, OTA) get lower priorities.
- **Never spin-wait in a task**: Every task loop must block on `xQueueReceive`, `ulTaskNotifyTake`, `xEventGroupWaitBits`, or `vTaskDelayUntil`. A busy-looping high-priority task starves lower-priority tasks and triggers the IDLE task watchdog.
- **Use `vTaskDelayUntil` for periodic control loops**: Unlike `vTaskDelay`, it compensates for execution jitter and avoids cumulative timing drift.
- **Stack sizing**: Measure real headroom with `uxTaskGetStackHighWaterMark(NULL)` under worst-case paths (including error logging and deep call chains) and keep >= 25% safety margin. Note that FreeRTOS `usStackDepth` is in **words** on STM32/upstream FreeRTOS, but in **bytes** on ESP-IDF!

## Synchronization Primitives — Which to Choose
| Need | Best Primitive | Why |
| :--- | :--- | :--- |
| Wake a single task from ISR | `xTaskNotifyFromISR` | Fastest, zero extra RAM beyond TCB |
| Pass fixed-size events/structs | `xQueueSend` / `xQueueReceive` | Copies by value, decoupled, ISR-safe |
| Wait on multiple conditions (AND/OR) | `EventGroupHandle_t` | Clean multi-flag synchronization |
| Protect shared resource across tasks | `xSemaphoreCreateMutex` | Supports **priority inheritance** (never use binary semaphore as a lock!) |
| Serialize access to an SPI/I2C bus | Gatekeeper task + request queue | Eliminates cross-task lock ordering deadlocks |

## Avoiding Deadlocks & Priority Inversion
1. **Priority inversion**: Always use a **Mutex** (not binary semaphore) for shared resources so FreeRTOS temporarily boosts the holder's priority.
2. **Lock ordering**: If two mutexes must ever be held simultaneously, enforce one global acquisition order everywhere and use finite timeouts (`pdMS_TO_TICKS(...)`) instead of `portMAX_DELAY` when recovery is possible.
3. **Timer daemon caution**: Software timer callbacks execute in the `Tmr Svc` task context — never block indefinitely inside a timer callback, or every software timer in the system freezes.
