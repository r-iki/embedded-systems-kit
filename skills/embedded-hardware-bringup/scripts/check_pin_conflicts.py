#!/usr/bin/env python3
"""Validate an embedded MCU pinmap JSON file for conflicts, hardware gotchas, and voltage mismatches."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

MCU_RULES: dict[str, dict[str, object]] = {
    "esp32": {
        "max_voltage": 3.3,
        "reserved_flash": {"GPIO6", "GPIO7", "GPIO8", "GPIO9", "GPIO10", "GPIO11"},
        "input_only": {"GPIO34", "GPIO35", "GPIO36", "GPIO39"},
        "strapping": {"GPIO0", "GPIO2", "GPIO12", "GPIO15"},
        "adc2": {"GPIO0", "GPIO2", "GPIO4", "GPIO12", "GPIO13", "GPIO14", "GPIO15", "GPIO25", "GPIO26", "GPIO27"},
    },
    "esp32-s3": {
        "max_voltage": 3.3,
        "reserved_flash": {"GPIO26", "GPIO27", "GPIO28", "GPIO29", "GPIO30", "GPIO31", "GPIO32"},
        "octal_psram_reserved": {"GPIO33", "GPIO34", "GPIO35", "GPIO36", "GPIO37"},
        "input_only": set(),
        "strapping": {"GPIO0", "GPIO3", "GPIO45", "GPIO46"},
        "adc2": {"GPIO11", "GPIO12", "GPIO13", "GPIO14", "GPIO15", "GPIO16", "GPIO17", "GPIO18", "GPIO19", "GPIO20"},
    },
    "esp32-c3": {
        "max_voltage": 3.3,
        "reserved_flash": {"GPIO12", "GPIO13", "GPIO14", "GPIO15", "GPIO16", "GPIO17"},
        "input_only": set(),
        "strapping": {"GPIO2", "GPIO8", "GPIO9"},
        "adc2": {"GPIO5"},
    },
    "esp32-c6": {
        "max_voltage": 3.3,
        "reserved_flash": {"GPIO24", "GPIO25", "GPIO26", "GPIO27", "GPIO28", "GPIO29", "GPIO30"},
        "input_only": set(),
        "strapping": {"GPIO4", "GPIO5", "GPIO8", "GPIO9", "GPIO15"},
        "adc_pins": {"GPIO0", "GPIO1", "GPIO2", "GPIO3", "GPIO4", "GPIO5", "GPIO6"},
    },
    "stm32": {
        "max_voltage": 3.3,
        "swd_pins": {"PA13", "PA14"},
        "boot_pins": {"BOOT0"},
    },
    "stm32f1": {
        "max_voltage": 3.3,
        "swd_pins": {"PA13", "PA14"},
        "jtag_pins": {"PA15", "PB3", "PB4"},
        "boot_pins": {"BOOT0", "PB2"},
    },
    "stm32f4": {
        "max_voltage": 3.3,
        "swd_pins": {"PA13", "PA14"},
        "boot_pins": {"BOOT0", "PB2"},
    },
    "stm32g4": {
        "max_voltage": 3.3,
        "swd_pins": {"PA13", "PA14"},
        "boot_pins": {"PB8", "BOOT0"},
    },
    "stm32h7": {
        "max_voltage": 3.3,
        "swd_pins": {"PA13", "PA14"},
        "boot_pins": {"BOOT0"},
    },
    "rp2040": {
        "max_voltage": 3.3,
        "adc_pins": {"GPIO26", "GPIO27", "GPIO28", "GPIO29"},
        "pico_w_reserved": {"GPIO23", "GPIO24", "GPIO25", "GPIO29"},
    },
    "rp2350a": {
        "max_voltage": 3.3,
        "adc_pins": {"GPIO26", "GPIO27", "GPIO28", "GPIO29"},
        "pico_w_reserved": {"GPIO23", "GPIO24", "GPIO25", "GPIO29"},
    },
    "rp2350b": {
        "max_voltage": 3.3,
        "adc_pins": {"GPIO40", "GPIO41", "GPIO42", "GPIO43", "GPIO44", "GPIO45", "GPIO46", "GPIO47"},
    },
    "avr-5v": {
        "max_voltage": 5.0,
        "analog_only": {"A6", "A7"},
        "uart_boot_pins": {"D0", "D1"},
    },
}


def normalize_pin(pin: str) -> str:
    p = pin.strip().upper()
    if p.isdigit():
        return f"GPIO{p}"
    if p.startswith("GP") and p[2:].isdigit():
        return f"GPIO{p[2:]}"
    if p.startswith("IO") and p[2:].isdigit():
        return f"GPIO{p[2:]}"
    return p


def validate_pinmap(data: dict[str, object]) -> dict[str, list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    mcu = str(data.get("mcu", "")).strip().lower()
    features = {str(f).strip().lower() for f in data.get("features", [])}  # type: ignore[union-attr]
    pins = data.get("pins", [])
    if not isinstance(pins, list):
        return {"errors": ["`pins` must be a JSON array."], "warnings": []}

    rules = MCU_RULES.get(mcu)
    if rules is None and mcu.startswith("stm32"):
        rules = MCU_RULES["stm32"]
    if rules is None:
        warnings.append(f"Unknown MCU family '{mcu}'; running generic duplicate & voltage checks only.")
        rules = {}

    mcu_v = float(data.get("logic_voltage", rules.get("max_voltage", 3.3)))  # type: ignore[arg-type]
    seen_pins: dict[str, str] = {}

    for entry in pins:
        if not isinstance(entry, dict):
            errors.append("Pin entry must be an object.")
            continue

        raw_pin = str(entry.get("pin", ""))
        pin = normalize_pin(raw_pin)
        signal = str(entry.get("signal", "<unnamed>"))
        direction = str(entry.get("direction", "inout")).strip().lower()
        function = str(entry.get("function", "gpio")).strip().lower()
        pull = str(entry.get("pull", "none")).strip().lower()
        allow_shared = bool(entry.get("shared_bus", False))
        ext_v = entry.get("external_voltage")
        five_v_tolerant = bool(entry.get("five_v_tolerant", False))

        if not pin:
            errors.append(f"Signal '{signal}' is missing a `pin` value.")
            continue

        if pin in seen_pins and not allow_shared:
            errors.append(f"Duplicate pin assignment on {pin}: '{seen_pins[pin]}' and '{signal}'.")
        else:
            seen_pins[pin] = signal

        if ext_v is not None:
            ext_vf = float(ext_v)
            if ext_vf > mcu_v + 0.3 and not five_v_tolerant:
                errors.append(
                    f"Voltage mismatch on {pin} ({signal}): external {ext_vf} V exceeds MCU {mcu_v} V without level shifter or 5V tolerance."
                )
            elif ext_vf > mcu_v + 0.3 and five_v_tolerant and function == "adc":
                errors.append(
                    f"Analog voltage hazard on {pin} ({signal}): 5V-tolerant pins are NOT 5V-tolerant in ADC/analog mode."
                )
            elif ext_vf < mcu_v - 0.8:
                warnings.append(
                    f"Low logic voltage on {pin} ({signal}): external {ext_vf} V vs MCU {mcu_v} V (verify V_IH threshold / level shifting)."
                )

        if pin in rules.get("reserved_flash", set()):  # type: ignore[operator]
            errors.append(f"{pin} ({signal}) is connected to internal SPI flash on {mcu} — do not use.")

        if "octal_psram" in features and pin in rules.get("octal_psram_reserved", set()):  # type: ignore[operator]
            errors.append(f"{pin} ({signal}) is reserved by Octal PSRAM/Flash on {mcu}.")

        if ("pico_w" in features or "wifi" in features) and pin in rules.get("pico_w_reserved", set()):  # type: ignore[operator]
            errors.append(f"{pin} ({signal}) is used internally by CYW43 Wi-Fi/BLE on Pico W / Pico 2 W.")

        if pin in rules.get("input_only", set()):  # type: ignore[operator]
            if direction in {"output", "out", "inout", "od", "open_drain"}:
                errors.append(f"{pin} ({signal}) is input-only on {mcu}; cannot be configured as '{direction}'.")
            if pull in {"up", "down", "pullup", "pulldown"}:
                errors.append(f"{pin} ({signal}) has no internal pull-up/pull-down on {mcu}; use an external resistor.")

        if pin in rules.get("analog_only", set()) and function != "adc":  # type: ignore[operator]
            errors.append(f"{pin} ({signal}) is analog-input-only on {mcu}; digital GPIO is not supported.")

        if pin in rules.get("strapping", set()):  # type: ignore[operator]
            warnings.append(
                f"{pin} ({signal}) is a boot strapping pin on {mcu}; verify external pulls do not alter boot mode or flash voltage."
            )

        if function == "adc":
            if "wifi" in features and pin in rules.get("adc2", set()):  # type: ignore[operator]
                errors.append(f"{pin} ({signal}) uses ADC2 on {mcu}, which conflicts with Wi-Fi; move to an ADC1 pin.")
            if "adc_pins" in rules and pin not in rules["adc_pins"]:  # type: ignore[operator]
                errors.append(f"{pin} ({signal}) does not support ADC on {mcu} (valid: {sorted(rules['adc_pins'])}).")

        if pin in rules.get("swd_pins", set()) and function != "swd":  # type: ignore[operator]
            warnings.append(f"{pin} ({signal}) reassigns an SWD debug pin on {mcu}; flashing/debugging may require connect-under-reset.")

        if pin in rules.get("jtag_pins", set()) and function != "jtag":  # type: ignore[operator]
            warnings.append(f"{pin} ({signal}) defaults to JTAG on {mcu}; ensure SWJ-DP remap disables JTAG before GPIO use.")

        if pin in rules.get("boot_pins", set()):  # type: ignore[operator]
            warnings.append(f"{pin} ({signal}) is a BOOT pin on {mcu}; ensure boot state is deterministic.")

        if pin in rules.get("uart_boot_pins", set()) and function != "uart":  # type: ignore[operator]
            warnings.append(f"{pin} ({signal}) shares the UART bootloader bus on {mcu}; external loads can block flashing.")

    return {"errors": errors, "warnings": warnings}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate an MCU pinmap JSON file for hardware conflicts.")
    parser.add_argument("--pinmap", required=True, help="Path to pinmap JSON file")
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    args = parser.parse_args()

    path = Path(args.pinmap)
    if not path.is_file():
        print(f"Error: pinmap file not found: {path}", file=sys.stderr)
        return 2

    data = json.loads(path.read_text(encoding="utf-8"))
    report = validate_pinmap(data)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"Pinmap check for {path.name}: {len(report['errors'])} error(s), {len(report['warnings'])} warning(s)")
        for err in report["errors"]:
            print(f"  [ERROR] {err}")
        for warn in report["warnings"]:
            print(f"  [WARN]  {warn}")

    return 1 if report["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
