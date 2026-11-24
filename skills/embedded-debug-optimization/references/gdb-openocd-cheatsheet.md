# Non-Interactive GDB & OpenOCD Cheat Sheet

Always run GDB with `--batch` so commands execute cleanly and exit without blocking an AI agent session.

## One-Shot ARM Cortex-M Fault Dump via GDB + OpenOCD
Start OpenOCD in the background or use piped gdb (`target extended-remote | openocd ...`):

```bash
arm-none-eabi-gdb -q --batch build/firmware.elf \
  -ex "target extended-remote | openocd -f interface/stlink.cfg -f target/stm32f4x.cfg -c 'gdb_port pipe; log_output openocd.log'" \
  -ex "monitor halt" \
  -ex "info registers" \
  -ex "bt full" \
  -ex "x/4wx 0xE000ED28" \
  -ex "detach"
```
- `x/4wx 0xE000ED28` reads `CFSR`, `HFSR`, `DFSR`, and `MMFAR` (read `x/6wx 0xE000ED28` to include `BFAR` and `AFSR`).

## Inspect Stacked HardFault Frame
If `LR` (`EXC_RETURN`) has bit 2 = 0, read `$msp`; if bit 2 = 1, read `$psp`:
```bash
-ex "x/8wx $psp"
-ex "info line *(void**)((uint32_t)$psp + 24)"
```
Offset `+24` is the faulting `PC`; offset `+20` is `LR`.

## Reset, Flash & Verify Without Interactive Prompt
```bash
openocd -f interface/stlink.cfg -f target/stm32f4x.cfg \
  -c "program build/firmware.elf verify reset exit"
```

## Disassemble a Specific Fault Address Offline
```bash
arm-none-eabi-objdump -d -S --start-address=0x08004100 --stop-address=0x08004180 build/firmware.elf
```

## ESP32 Core Dump / Offline Backtrace
```bash
xtensa-esp32-elf-addr2line -pfiaC -e build/firmware.elf 0x400d1234 0x400d5678
```
For ESP32-C3 / C6 / H2 (RISC-V), substitute `riscv32-esp-elf-addr2line`.
For ESP32-S3, substitute `xtensa-esp32s3-elf-addr2line`.
