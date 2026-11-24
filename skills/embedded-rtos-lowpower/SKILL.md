---
name: embedded-rtos-lowpower
description: >-
  Design FreeRTOS task architectures, deterministic C/C++ finite state machines
  (FSM), inter-task synchronization (queues, notifications, mutexes), and
  battery-powered low-power sleep workflows. Use when architecting concurrent
  firmware, preventing deadlocks/priority inversion, implementing state machines,
  or estimating battery life and power budgets.
---

# Embedded RTOS Architecture, State Machines & Low-Power Design

Use this workflow to design deterministic, deadlock-free, and power-efficient embedded software architectures.

## Workflow

1. **Choose the simplest concurrency model that meets timing requirements**
   - Use a superloop + interrupt-driven [FSM template](./templates/fsm_template.h) when a single core runs a few periodic/event-driven tasks without complex networking stacks.
   - Use FreeRTOS when concurrent I/O stacks (Wi-Fi/BLE/LwIP/USB/GUI) require independent blocking flows and priority preemption.

2. **Architect RTOS tasks & inter-task communication safely**
   - Read [FreeRTOS Architecture Patterns](./references/freertos-patterns.md) before defining tasks, priorities, queues, or mutexes.
   - Prefer **static allocation** (`xTaskCreateStatic`, `xQueueCreateStatic`) or start from [rtos_module_template.c](./templates/rtos_module_template.c) to guarantee deterministic RAM budgets.
   - Assign **one owner task per shared peripheral** (gatekeeper pattern) instead of scattering mutexes across the codebase.
   - Use **Direct-to-Task Notifications** (`xTaskNotifyFromISR`) for lightweight ISR-to-task signaling instead of binary semaphores.

3. **Model complex control logic as an explicit Finite State Machine**
   - Read [FSM Architecture Guide](./references/fsm-architecture.md) to avoid tangled boolean flags (`is_connected`, `is_retrying`, `is_error`).
   - Guarantee explicit entry/exit actions, timeout transitions, and safe fallback/fault states.

4. **Design for low power and verify battery budget**
   - Follow [Low-Power Checklist](./references/low-power-checklist.md) to eliminate sleep leakage (floating GPIOs, pull resistors fighting external states, un-gated peripherals, high-frequency polling).
   - Quantify battery life early using [power_budget_calc.py](./scripts/power_budget_calc.py):
     ```bash
     python scripts/power_budget_calc.py --battery-mah 1200 --derating 0.85 \
       --state "deep_sleep:0.015:59.2" --state "sensor_read:8.0:0.3" --state "tx_burst:120.0:0.5"
     ```
   - Verify active duty cycle, wake-up latency, and quiescent current (`I_q`) of LDOs/sensors — not just MCU datasheet sleep current.
