# Embedded Low-Power Engineering Checklist

True battery life is dominated by **sleep current x sleep time** + **active burst energy**. An MCU sleeping at 10 uA is wasted if a single forgotten pull-up resistor leaks 1 mA.

## 1. Eliminate Hidden Board & Pin Leakage
- **Unused GPIOs**: Never leave CMOS inputs floating (floating inputs float near mid-rail and cause shoot-through current). Configure unused pins as **Analog mode** (STM32) or input with pull-down/disable input buffer (ESP32 `gpio_reset_pin` / `rtc_gpio_isolate`).
- **Fighting pull resistors**: Before entering sleep, verify output pin levels match external pull-ups/pull-downs (e.g., do not drive an I2C or active-low CS line low against a 4.7 kOhm pull-up during sleep: `3.3V / 4.7k = 700 uA` wasted!).
- **Back-powering through I/O pins**: If cutting power to a sensor via a load switch/MOSFET, first set all MCU I2C/SPI/UART pins connected to that sensor to low/Hi-Z so current does not leak through the sensor's ESD protection diodes.

## 2. Peripheral & Clock Gating
- Disable unused peripherals (ADC, timers, UART, USB PHY, brownout only if safe) before entering Stop/Deep-Sleep.
- Lower system clock or enter tickless idle (`configUSE_TICKLESS_IDLE`) when active workload is light; for bursty workloads (e.g., radio TX), **race-to-sleep** (finish fast, sleep deep) often uses less total energy than running slowly.

## 3. Whole-System Quiescent Current (`I_q`) Audit
Sum all always-on loads in your power budget:
- Voltage regulator / LDO `I_q` (AMS1117 wastes ~5-10 mA! Use low-`I_q` LDOs/bucks like TPS6274x, MCP1700, or AP2112K depending on load).
- Voltage divider resistors on battery ADC sense (use 1 MOhm+ with a 100 nF sampling cap, or gate the divider with a MOSFET).
- Power LEDs (remove or disable on battery boards — a single LED draws 1-10 mA).
- External flash, pull-ups, RTC, and always-on sensors.

## 4. Wake-Up Verification
- Measure real current with a current profiler (PPK2, Otii, Joulescope, or series shunt) in both active and sleep states.
- Confirm RTC retention memory (`RTC_DATA_ATTR` on ESP32, Backup SRAM on STM32) preserves state across deep-sleep cycles without wearing out Flash/NVS.
