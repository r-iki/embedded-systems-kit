# Embedded Toolchains CLI Cheat Sheet

## PlatformIO (`pio`)
- Build all / specific env: `pio run` / `pio run -e esp32dev`
- Flash: `pio run -e esp32dev -t upload --upload-port COM5`
- Size report: `pio run -e esp32dev -t size`
- Native unit tests: `pio test -e native`
- List serial ports: `pio device list`
- Clean build: `pio run -t clean`

## ESP-IDF (`idf.py`)
- Set chip target: `idf.py set-target esp32s3`
- Build: `idf.py build`
- Size breakdown: `idf.py size` / `idf.py size-components` / `idf.py size-files`
- Flash only (never append `monitor` in an agent shell): `idf.py -p COM5 -b 460800 flash`
- Erase flash: `idf.py -p COM5 erase-flash`
- Partition table check: `idf.py partition-table`

## CMake + ARM GCC (`arm-none-eabi-gcc`) / STM32
- Configure: `cmake -B build -G Ninja -DCMAKE_TOOLCHAIN_FILE=cmake/arm-none-eabi.cmake -DCMAKE_EXPORT_COMPILE_COMMANDS=ON`
- Build: `cmake --build build`
- Flash via OpenOCD (ST-Link):
  `openocd -f interface/stlink.cfg -f target/stm32f4x.cfg -c "program build/firmware.elf verify reset exit"`
- Flash via STM32CubeProgrammer CLI:
  `STM32_Programmer_CLI -c port=SWD -w build/firmware.elf -v -rst`
- Flash via `st-flash` (binary):
  `st-flash --reset write build/firmware.bin 0x08000000`

## RP2040 / RP2350 (Pico SDK)
- Configure & build: `cmake -B build -G Ninja -DPICO_BOARD=pico && cmake --build build`
- Flash via `picotool` (BOOTSEL mode): `picotool load -f -x build/app.uf2`
- Flash via OpenOCD (Debug Probe / CMSIS-DAP):
  `openocd -f interface/cmsis-dap.cfg -f target/rp2040.cfg -c "adapter speed 5000" -c "program build/app.elf verify reset exit"`

## Arduino CLI (`arduino-cli`)
- List connected boards: `arduino-cli board list`
- Compile: `arduino-cli compile --fqbn esp32:esp32:esp32 --output-dir build .`
- Upload: `arduino-cli upload -p COM5 --fqbn esp32:esp32:esp32 --input-dir build`

## Generating Linker Map Files
Add to linker flags to inspect section placement and symbol bloat:
- GCC / ARM GCC / ESP-IDF: `-Wl,-Map=firmware.map,--cref`
- Enable dead-code elimination: compile with `-ffunction-sections -fdata-sections` and link with `-Wl,--gc-sections`.
