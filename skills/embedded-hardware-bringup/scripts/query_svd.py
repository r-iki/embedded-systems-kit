#!/usr/bin/env python3
"""Query CMSIS-SVD (.svd) register maps and parse STM32CubeMX (.ioc) pinouts accurately."""

from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def _txt(elem: ET.Element | None, tag: str, default: str = "") -> str:
    if elem is None:
        return default
    child = elem.find(tag)
    if child is None or child.text is None:
        return default
    return child.text.strip()


def _parse_int(val: str, default: int = 0) -> int:
    if not val:
        return default
    val = val.strip()
    if val.startswith("#"):
        return int(val[1:], 2)
    return int(val, 0)


def _parse_bit_range(field: ET.Element) -> tuple[int, int]:
    bit_range = _txt(field, "bitRange")
    if bit_range:
        m = re.match(r"\[(\d+):(\d+)\]", bit_range)
        if m:
            return int(m.group(1)), int(m.group(2))
    lsb_txt = _txt(field, "lsb")
    msb_txt = _txt(field, "msb")
    if lsb_txt and msb_txt:
        return int(msb_txt), int(lsb_txt)
    offset = _parse_int(_txt(field, "bitOffset"), 0)
    width = _parse_int(_txt(field, "bitWidth"), 1)
    return offset + width - 1, offset


def load_svd(svd_path: Path) -> dict[str, dict[str, object]]:
    tree = ET.parse(svd_path)
    root = tree.getroot()
    raw_periphs: dict[str, ET.Element] = {}
    periphs: dict[str, dict[str, object]] = {}

    for p in root.findall("./peripherals/peripheral"):
        name = _txt(p, "name")
        if name:
            raw_periphs[name] = p

    def resolve_registers(p_elem: ET.Element) -> list[dict[str, object]]:
        regs: list[dict[str, object]] = []
        derived = p_elem.attrib.get("derivedFrom")
        if derived and derived in raw_periphs:
            regs.extend(resolve_registers(raw_periphs[derived]))
        regs_elem = p_elem.find("registers")
        if regs_elem is not None:
            for r in regs_elem.findall("register"):
                r_name = _txt(r, "name")
                offset = _parse_int(_txt(r, "addressOffset"), 0)
                size = _parse_int(_txt(r, "size"), 32)
                reset_val = _txt(r, "resetValue", "")
                access = _txt(r, "access", "")
                desc = " ".join(_txt(r, "description", "").split())
                fields = []
                fields_elem = r.find("fields")
                if fields_elem is not None:
                    for f in fields_elem.findall("field"):
                        msb, lsb = _parse_bit_range(f)
                        width = msb - lsb + 1
                        mask = ((1 << width) - 1) << lsb
                        fields.append({
                            "name": _txt(f, "name"),
                            "msb": msb,
                            "lsb": lsb,
                            "bits": f"[{msb}:{lsb}]" if msb != lsb else f"[{lsb}]",
                            "mask_hex": f"0x{mask:08X}",
                            "access": _txt(f, "access", access),
                            "description": " ".join(_txt(f, "description", "").split()),
                        })
                fields.sort(key=lambda item: int(item["lsb"]))
                regs.append({
                    "name": r_name,
                    "offset": offset,
                    "offset_hex": f"0x{offset:X}",
                    "size_bits": size,
                    "reset_value": reset_val,
                    "access": access,
                    "description": desc,
                    "fields": fields,
                })
        return regs

    for name, p_elem in raw_periphs.items():
        base_addr = _parse_int(_txt(p_elem, "baseAddress"), 0)
        desc = " ".join(_txt(p_elem, "description", "").split())
        regs = resolve_registers(p_elem)
        for reg in regs:
            reg["address_hex"] = f"0x{base_addr + int(reg['offset']):08X}"
        periphs[name] = {
            "name": name,
            "base_address_hex": f"0x{base_addr:08X}",
            "description": desc,
            "registers": regs,
        }
    return periphs


def parse_ioc(ioc_path: Path) -> dict[str, object]:
    kv: dict[str, str] = {}
    for line in ioc_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        kv[key.strip()] = val.strip()

    mcu_name = kv.get("Mcu.Name", kv.get("Mcu.UserName", "stm32"))
    mcu_family = kv.get("Mcu.Family", "STM32").lower()

    pin_signals: dict[str, dict[str, str]] = {}
    pin_re = re.compile(r"^(P[A-K]\d+(?:-[A-Za-z0-9_]+)?)\.([A-Za-z0-9_]+)$")
    for key, val in kv.items():
        m = pin_re.match(key)
        if not m:
            continue
        raw_pin = m.group(1).split("-")[0]
        prop = m.group(2)
        entry = pin_signals.setdefault(raw_pin, {"pin": raw_pin})
        entry[prop] = val

    pins_out: list[dict[str, object]] = []
    for pin_name in sorted(pin_signals):
        info = pin_signals[pin_name]
        signal = info.get("Signal", "")
        if not signal:
            continue
        label = info.get("GPIO_Label", signal)
        sig_low = signal.lower()
        if "swd" in sig_low or "sys_jt" in sig_low:
            func = "swd"
        elif "i2c" in sig_low:
            func = "i2c"
        elif "spi" in sig_low:
            func = "spi"
        elif "usart" in sig_low or "uart" in sig_low:
            func = "uart"
        elif "adc" in sig_low:
            func = "adc"
        elif "tim" in sig_low:
            func = "pwm"
        else:
            func = "gpio"

        direction = "output" if "output" in sig_low else ("input" if "input" in sig_low or func == "adc" else "inout")
        pins_out.append({
            "pin": pin_name,
            "signal": label,
            "cube_signal": signal,
            "function": func,
            "direction": direction,
            "external_voltage": 3.3,
        })

    return {
        "mcu": mcu_family if mcu_family.startswith("stm32") else "stm32",
        "mcu_part": mcu_name,
        "logic_voltage": 3.3,
        "features": [],
        "pins": pins_out,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect CMSIS-SVD (.svd) registers or STM32CubeMX (.ioc) pinouts.")
    parser.add_argument("--svd", help="Path to CMSIS-SVD XML file (.svd)")
    parser.add_argument("--list-peripherals", action="store_true", help="List peripherals in the SVD file")
    parser.add_argument("--peripheral", help="Peripheral name (e.g., GPIOA, I2C1, USART2)")
    parser.add_argument("--register", help="Register name within --peripheral (e.g., CR1, MODER)")
    parser.add_argument("--ioc", help="Path to STM32CubeMX .ioc file")
    parser.add_argument("--export-pinmap", help="Optional output path to export parsed .ioc pinmap JSON")
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    args = parser.parse_args()

    if not args.svd and not args.ioc:
        parser.error("Provide --svd <file.svd> or --ioc <file.ioc>")

    if args.ioc:
        ioc_path = Path(args.ioc)
        if not ioc_path.is_file():
            print(f"Error: .ioc file not found: {ioc_path}", file=sys.stderr)
            return 2
        parsed = parse_ioc(ioc_path)
        if args.export_pinmap:
            Path(args.export_pinmap).write_text(json.dumps(parsed, indent=2) + "\n", encoding="utf-8")
        if args.json:
            print(json.dumps(parsed, indent=2))
        else:
            print(f"STM32CubeMX MCU: {parsed['mcu_part']} (family: {parsed['mcu']})")
            print(f"Configured pins ({len(parsed['pins'])}):")  # type: ignore[arg-type]
            for p in parsed["pins"]:  # type: ignore[union-attr]
                print(f"  {p['pin']:<6} -> {p['signal']:<20} ({p['cube_signal']}, {p['function']})")
            if args.export_pinmap:
                print(f"\nExported pinmap JSON to: {args.export_pinmap}")
        return 0

    svd_path = Path(args.svd)
    if not svd_path.is_file():
        print(f"Error: .svd file not found: {svd_path}", file=sys.stderr)
        return 2

    periphs = load_svd(svd_path)

    if args.list_peripherals or not args.peripheral:
        listing = [
            {"name": name, "base_address_hex": p["base_address_hex"], "register_count": len(p["registers"])}  # type: ignore[arg-type]
            for name, p in sorted(periphs.items())
        ]
        if args.json:
            print(json.dumps(listing, indent=2))
        else:
            print(f"Peripherals in {svd_path.name} ({len(listing)}):")
            for item in listing:
                print(f"  {item['name']:<16} {item['base_address_hex']}  ({item['register_count']} regs)")
        return 0

    target_p = periphs.get(args.peripheral) or next(
        (v for k, v in periphs.items() if k.lower() == args.peripheral.lower()), None
    )
    if target_p is None:
        print(f"Error: peripheral '{args.peripheral}' not found in {svd_path.name}", file=sys.stderr)
        return 1

    if args.register:
        regs = target_p["registers"]  # type: ignore[assignment]
        target_r = next((r for r in regs if str(r["name"]).lower() == args.register.lower()), None)
        if target_r is None:
            print(f"Error: register '{args.register}' not found in {target_p['name']}", file=sys.stderr)
            return 1
        if args.json:
            print(json.dumps({"peripheral": target_p["name"], **target_r}, indent=2))
        else:
            print(
                f"{target_p['name']}.{target_r['name']} @ {target_r['address_hex']} "
                f"(offset {target_r['offset_hex']}, reset={target_r['reset_value'] or 'n/a'})"
            )
            if target_r["description"]:
                print(f"  {target_r['description']}")
            for f in target_r["fields"]:  # type: ignore[union-attr]
                print(f"  {f['bits']:<8} {f['name']:<18} mask={f['mask_hex']}  {f['description']}")
        return 0

    if args.json:
        print(json.dumps(target_p, indent=2))
    else:
        print(f"{target_p['name']} @ {target_p['base_address_hex']} — {target_p['description']}")
        for r in target_p["registers"]:  # type: ignore[union-attr]
            print(f"  {r['name']:<16} {r['address_hex']} (+{r['offset_hex']:<6}) reset={r['reset_value'] or 'n/a':<10} {r['description']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
