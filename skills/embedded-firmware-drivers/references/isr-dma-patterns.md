# ISR & DMA Design Patterns

## Hard Rules for Interrupt Service Routines (ISRs)
1. **Execution budget**: Keep ISRs deterministic and fast (typically microseconds). Defer parsing, floating-point math, logging, and protocol state machines to a task or main loop.
2. **Forbidden inside ISRs**:
   - Blocking delays (`vTaskDelay`, `HAL_Delay`, `delay`, busy-wait loops)
   - Dynamic memory (`malloc`, `free`, `new`, `std::string`)
   - Standard I/O (`printf`, `ESP_LOGI`, `Serial.println`)
   - Mutexes (`xSemaphoreTake` on a mutex has ownership semantics and is illegal in ISRs)
3. **RTOS `FromISR` convention**:
   - In FreeRTOS, use only `*FromISR()` variants (`xTaskNotifyFromISR`, `xQueueSendFromISR`) and call `portYIELD_FROM_ISR(higher_prio_woken)`.
   - On ARM Cortex-M, ensure the interrupt's NVIC priority is numerically `>= configMAX_SYSCALL_INTERRUPT_PRIORITY` (lower urgency) if it calls FreeRTOS APIs.
4. **ESP32 IRAM placement**:
   - Mark ISRs that run while Flash cache is disabled (e.g., NVS/OTA writes) with `IRAM_ATTR`, and keep any called helper functions and lookup tables in IRAM/DRAM.

## `volatile`, Atomicity & Critical Sections
- **`volatile` is NOT atomic**: `volatile` only prevents the compiler from caching a read/write in a register. An operation like `counter++` is still a read-modify-write that an ISR can preempt mid-way.
- **Safe single-word reads**: On 32-bit MCUs (ARM Cortex-M, ESP32, RP2040), naturally aligned 32-bit loads/stores are atomic at the hardware level, but C still requires `<stdatomic.h>` (`atomic_load_explicit` / `atomic_store_explicit`) or a critical section for portability and memory ordering.
- **Multi-byte snapshots**: Copy multi-field structs shared with an ISR inside a brief critical section (`taskENTER_CRITICAL` / `__disable_irq()` with saved PRIMASK) into a local copy, then exit immediately before processing.

## DMA Reliability Checklist
- **Lifetime**: Never pass a stack-allocated buffer to an asynchronous DMA call; the stack frame vanishes when the function returns. Use `static` buffers or statically allocated ring buffers.
- **Double buffering / Ping-Pong**: Use Half-Transfer (`HT`) and Transfer-Complete (`TC`) interrupts to process one half of a circular DMA buffer while hardware fills the other half.
- **Cache coherence (Cortex-M7, ESP32-S3 with PSRAM)**:
  - Align buffers to cache line size (typically 32 bytes).
  - TX: Clean D-cache (`SCB_CleanDCache_by_Addr`) *before* starting DMA.
  - RX: Invalidate D-cache (`SCB_InvalidateDCache_by_Addr`) *after* DMA completes, before CPU reads.
- **Memory region placement**: Ensure DMA buffers are not placed in CPU-only memories (e.g., STM32F4 CCMRAM or STM32H7 DTCM unless using MDMA).
