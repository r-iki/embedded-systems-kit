# Hardware Bring-Up Checklist

- **Board / Revision:**
- **MCU / Module:**
- **Date / Engineer:**

## Stage 0 — Unpowered Inspection
- [ ] Visual inspection passed (no solder bridges, correct polarity on diodes/caps/ICs)
- [ ] Resistance to GND checked on all rails:
  - `VBUS / VIN`: _____ Ohm
  - `5V`: _____ Ohm
  - `3V3`: _____ Ohm
  - `1V8 / VDDA`: _____ Ohm

## Stage 1 — Current-Limited Power-Up
- [ ] Bench supply limit set to _____ mA; idle current measured: _____ mA
- [ ] No abnormal heating observed
- [ ] Rail voltages verified within tolerance:
  - `5V`: _____ V | `3V3`: _____ V | `VDDA`: _____ V
- [ ] `NRST / EN` voltage verified high: _____ V

## Stage 2 — Debug / Bootloader Attach
- [ ] SWD / JTAG / UART bootloader connected (`chip_id` read successfully)
- [ ] Pinout validated with `check_pin_conflicts.py` (0 errors)

## Stage 3 — Proof-of-Life Firmware
- [ ] Minimal blink firmware flashed; 1 Hz blink period verified (clock tree OK)
- [ ] UART / RTT console banner received at expected baud rate

## Stage 4 — Peripheral & Sensor Smoke Tests
- [ ] I2C scan detected expected 7-bit addresses: _______________
- [ ] SPI `WHO_AM_I` / ID read verified for each slave: _______________
- [ ] ADC reference reading verified against multimeter

## Stage 5 — Load & Fault Tests
- [ ] Actuators / radio TX tested under current limit; 3V3 rail droop < _____ mV
- [ ] Watchdog & brownout reset behavior verified
