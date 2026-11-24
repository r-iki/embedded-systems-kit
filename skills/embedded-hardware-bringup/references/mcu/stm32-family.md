# STM32 Family Engineering Reference (F1, F4, G4, L4, H7)

Load this reference when working with STM32 ARM Cortex-M firmware (STM32CubeHAL/LL, CMSIS, FreeRTOS, or bare-metal).

## Series Comparison & Architecture Traps

| Topic | STM32F1 (M3) | STM32F4 (M4F) | STM32G4 / L4 (M4F) | STM32H7 (M7) |
| :--- | :--- | :--- | :--- | :--- |
| **GPIO Alternate Function** | Legacy `AFIO` remap (coarse per-peripheral remap) | Per-pin `AFR[0..1]` (`AF0–AF15`) | Per-pin `AFR` + `DMAMUX` | Per-pin `AFR` + `DMAMUX1/2` |
| **DMA Controller** | Fixed channels (`DMA1/2`) | Streams + Channels (`DMA1/2`) | Flexible `DMAMUX` | `DMA1/2` (D2 SRAM), `BDMA` (D3 SRAM4 only!), `MDMA` |
| **Cache / TCM Hazards** | None | **CCMRAM (`0x10000000`) is NOT DMA-accessible** | Low-power SRAM retention rules | **D-Cache active & DTCM (`0x20000000`) NOT reachable by DMA1/2!** |
| **Flash wait states** | Up to 2 WS (72 MHz) | Up to 5 WS (168/180 MHz) | Up to 4–8 WS + VOS scaling | VOS0–VOS3 + AXI wait states |

## Top STM32 Firmware Pitfalls
1. **STM32H7 DMA + D-Cache Silent Corruption** (most common H7 bug):
   - Default CubeMX linker places `.bss`/`.data` in **DTCMRAM** (`0x20000000`), which `DMA1`/`DMA2` cannot access (transfers read/write zeros or trigger TEIF).
   - Place DMA buffers in an explicit linker section mapped to **AXI SRAM (D1)** or **SRAM1/2 (D2)** (or **SRAM4 (D3)** for BDMA).
   - Either configure that buffer region as non-cacheable via **MPU**, OR align buffers to 32 bytes and call `SCB_CleanDCache_by_Addr()` before TX DMA and `SCB_InvalidateDCache_by_Addr()` after RX DMA.
2. **RCC Peripheral Clock Must Be Enabled First**:
   - Writing peripheral registers before `__HAL_RCC_<PERIPH>_CLK_ENABLE()` is silently ignored (or faults). Insert a dummy read (`__IO uint32_t tmpreg = RCC->...`) or use the HAL macro to satisfy the 2-cycle clock-enable delay.
3. **STM32CubeMX Regeneration Safety**:
   - Never place hand-written code outside `/* USER CODE BEGIN ... */` and `/* USER CODE END ... */` in CubeMX-generated files (`main.c`, `stm32*_it.c`, `stm32*_hal_msp.c`). Better yet, isolate application code in separate `App/` modules called from minimal hooks.
4. **HAL vs LL & `HAL_Delay()` Deadlocks**:
   - Never call `HAL_Delay()` inside an ISR whose preemption priority is `<=` SysTick priority (numerically equal or higher urgency) — `uwTick` stops incrementing and the MCU hangs forever.
   - Use **LL** drivers for high-frequency timer/ADC/SPI ISRs where HAL's generic lock/state-machine overhead adds unacceptable latency.
5. **5 V Tolerance (`FT`) Caveats**:
   - Only pins explicitly labeled `FT` / `FT_f` in the datasheet pinout table tolerate 5 V, and **never** when configured in Analog (`ADC`/`DAC`) mode or when `VDD = 0 V` (unpowered board back-powering).
6. **Debug & Boot Pins**:
   - Keep `PA13` (`SWDIO`) and `PA14` (`SWCLK`) free; on F1 also watch JTAG defaults (`PA15`, `PB3`, `PB4`) until SWJ-DP remapping disables JTAG.
   - Always pull `BOOT0` LOW with a resistor (e.g., 10 kOhm) for deterministic Flash boot.
7. **FreeRTOS + NVIC Priority Grouping**:
   - Set `HAL_NVIC_SetPriorityGrouping(NVIC_PRIORITYGROUP_4)` (4 preemption bits, 0 subpriority bits).
   - Any ISR calling FreeRTOS `*FromISR()` APIs MUST have a numerical priority `>= configLIBRARY_MAX_SYSCALL_INTERRUPT_PRIORITY` (typically `>= 5`). Never use priority `0` for a FreeRTOS-calling ISR!
   - When using FreeRTOS, switch HAL's timebase from `SysTick` to a dedicated hardware timer (`TIM6`/`TIM7`) in CubeMX so FreeRTOS owns `SysTick`.
