#!/usr/bin/env python3
"""Validate embedded-systems-kit plugin structure, frontmatter, links, and helper scripts."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent

ALLOWED_PLUGIN_FIELDS = {
    "name",
    "displayName",
    "version",
    "description",
    "logo",
    "suggestedPrompts",
    "author",
    "homepage",
    "repository",
    "disabled",
}


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def parse_frontmatter(md_text: str) -> dict[str, str]:
    match = re.match(r"^---\r?\n(.*?)\r?\n---", md_text, re.DOTALL)
    assert_true(match is not None, "Missing YAML frontmatter block")
    block = match.group(1)
    result: dict[str, str] = {}
    current_key: str | None = None
    for line in block.splitlines():
        if re.match(r"^[a-zA-Z0-9_-]+:\s*", line):
            key, val = line.split(":", 1)
            current_key = key.strip()
            result[current_key] = val.strip()
        elif current_key and line.startswith((" ", "\t")):
            result[current_key] = (result[current_key] + " " + line.strip()).strip()
    return result


def validate_manifest() -> None:
    manifest_path = PLUGIN_ROOT / "plugin.json"
    assert_true(manifest_path.is_file(), "plugin.json is missing")
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    unknown = set(data.keys()) - ALLOWED_PLUGIN_FIELDS
    assert_true(not unknown, f"Unknown top-level plugin.json fields: {sorted(unknown)}")
    assert_true(re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", data["name"]) is not None, "plugin.json name must be kebab-case")
    assert_true(bool(data.get("description")), "plugin.json description must be non-empty")

    if "logo" in data:
        logo_path = PLUGIN_ROOT / data["logo"]
        assert_true(logo_path.is_file(), f"Logo path does not exist: {logo_path}")
        assert_true(logo_path.suffix.lower() in {".svg", ".png", ".jpg", ".jpeg", ".webp"}, "Invalid logo extension")

    prompts = data.get("suggestedPrompts", [])
    assert_true(isinstance(prompts, list) and 1 <= len(prompts) <= 3, "suggestedPrompts should have 1-3 items")
    print("[PASS] plugin.json manifest schema and assets")


def validate_rules_and_agents() -> None:
    rules_path = PLUGIN_ROOT / "rules" / "AGENTS.md"
    assert_true(rules_path.is_file(), "rules/AGENTS.md missing")
    rules_text = rules_path.read_text(encoding="utf-8")
    assert_true(not rules_text.lstrip().startswith("---"), "rules/AGENTS.md must not have YAML frontmatter")
    assert_true(len(rules_text.strip()) > 100, "rules/AGENTS.md seems unexpectedly short")

    agents_dir = PLUGIN_ROOT / "agents"
    agent_files = sorted(agents_dir.glob("*.md"))
    assert_true(len(agent_files) >= 1, "Expected at least one agent markdown file")
    for agent_file in agent_files:
        fm = parse_frontmatter(agent_file.read_text(encoding="utf-8"))
        assert_true(bool(fm.get("name")), f"{agent_file.name}: missing frontmatter name")
        assert_true(bool(fm.get("description")), f"{agent_file.name}: missing frontmatter description")
    print(f"[PASS] rules/AGENTS.md and {len(agent_files)} agent definition(s)")


def validate_skills() -> None:
    skills_dir = PLUGIN_ROOT / "skills"
    skill_dirs = sorted(p for p in skills_dir.iterdir() if p.is_dir())
    assert_true(len(skill_dirs) == 5, f"Expected 5 skills, found {len(skill_dirs)}")

    rel_link_re = re.compile(r"\[[^\]]+\]\((\./[^)#]+)\)")
    total_links = 0
    for sdir in skill_dirs:
        skill_md = sdir / "SKILL.md"
        assert_true(skill_md.is_file(), f"Missing SKILL.md in {sdir.name}")
        text = skill_md.read_text(encoding="utf-8")
        fm = parse_frontmatter(text)
        assert_true(fm.get("name") == sdir.name, f"Frontmatter name '{fm.get('name')}' != folder '{sdir.name}'")
        assert_true(len(fm.get("description", "")) >= 30, f"Skill '{sdir.name}' description is too short")

        for rel in rel_link_re.findall(text):
            target = (sdir / rel).resolve()
            assert_true(target.exists(), f"Broken link '{rel}' in {skill_md}")
            total_links += 1

    print(f"[PASS] {len(skill_dirs)} skills validated ({total_links} relative links verified)")


def run_py(script: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_scripts() -> None:
    # 1. detect_project.py
    detect_script = PLUGIN_ROOT / "skills/embedded-build-flash-ci/scripts/detect_project.py"
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        (tmp_path / "platformio.ini").write_text("[env:esp32dev]\nplatform = espressif32\n", encoding="utf-8")
        res = run_py(detect_script, ["--path", str(tmp_path), "--json"])
        assert_true(res.returncode == 0, f"detect_project failed: {res.stderr}")
        payload = json.loads(res.stdout)
        ecos = [e["ecosystem"] for e in payload["ecosystems"]]
        assert_true("platformio" in ecos, f"Expected platformio in {ecos}")
        assert_true("esp32dev" in payload["ecosystems"][0]["environments"], "Missing env esp32dev")

        esp_dir = tmp_path / "esp"
        esp_dir.mkdir()
        (esp_dir / "sdkconfig").write_text("CONFIG_IDF_TARGET=\"esp32s3\"\n", encoding="utf-8")
        res2 = run_py(detect_script, ["--path", str(esp_dir), "--json"])
        assert_true(res2.returncode == 0 and json.loads(res2.stdout)["ecosystems"][0]["ecosystem"] == "esp-idf", "ESP-IDF detection failed")

    # 2. analyze_size.py (using synthetic .map file)
    size_script = PLUGIN_ROOT / "skills/embedded-build-flash-ci/scripts/analyze_size.py"
    with tempfile.TemporaryDirectory() as tmp:
        map_file = Path(tmp) / "firmware.map"
        map_file.write_text(
            " .text.sensor_loop 0x08001000 0x400 build/sensor.o\n"
            " .bss.rx_buffer   0x20000100 0x800 build/uart.o\n",
            encoding="utf-8",
        )
        res = run_py(size_script, ["--map", str(map_file), "--json"])
        assert_true(res.returncode == 0, f"analyze_size failed: {res.stderr}")
        payload = json.loads(res.stdout)
        assert_true(len(payload["top_symbols"]) == 2, "Expected 2 parsed map sections")
        assert_true(payload["top_symbols"][0]["size_bytes"] == 0x800, "Top symbol sort mismatch")

    # 3. serial_capture.py (--dry-run)
    serial_script = PLUGIN_ROOT / "skills/embedded-build-flash-ci/scripts/serial_capture.py"
    res = run_py(serial_script, ["--port", "COM99", "--timeout", "1", "--dry-run"])
    assert_true(res.returncode == 0, f"serial_capture dry-run failed: {res.stderr}")

    # 4. run_static_analysis.py (--help & dry-run)
    lint_script = PLUGIN_ROOT / "skills/embedded-build-flash-ci/scripts/run_static_analysis.py"
    res = run_py(lint_script, ["--help"])
    assert_true(res.returncode == 0, f"run_static_analysis --help failed: {res.stderr}")

    # 5. decode_crash.py (ESP32 + Cortex-M parsing)
    decode_script = PLUGIN_ROOT / "skills/embedded-debug-optimization/scripts/decode_crash.py"
    with tempfile.TemporaryDirectory() as tmp:
        crash_log = Path(tmp) / "crash.txt"
        crash_log.write_text(
            "Guru Meditation Error: Core 0 panic'ed (LoadProhibited). Exception was unhandled.\n"
            "EXCVADDR: 0x00000004\n"
            "Backtrace: 0x400d1234:0x3ffb1200 0x400d5678:0x3ffb1240\n"
            "CFSR: 0x00001200\n",
            encoding="utf-8",
        )
        res = run_py(decode_script, ["--log", str(crash_log), "--json"])
        assert_true(res.returncode == 0, f"decode_crash failed: {res.stderr}")
        payload = json.loads(res.stdout)
        assert_true("0x400d1234" in payload["addresses"], "Missed ESP32 backtrace address")
        hints_joined = " ".join(payload["hints"])
        assert_true("NULL pointer" in hints_joined, f"Missed NULL pointer hint: {hints_joined}")
        assert_true("STKERR" in hints_joined and "PRECISERR" in hints_joined, f"Missed CFSR flags: {hints_joined}")

    # 6. power_budget_calc.py
    power_script = PLUGIN_ROOT / "skills/embedded-rtos-lowpower/scripts/power_budget_calc.py"
    res = run_py(
        power_script,
        [
            "--battery-mah", "1000",
            "--derating", "1.0",
            "--state", "sleep:0.1:9",
            "--state", "active:9.1:1",
            "--json",
        ],
    )
    assert_true(res.returncode == 0, f"power_budget_calc failed: {res.stderr}")
    payload = json.loads(res.stdout)
    assert_true(abs(payload["average_current_ma"] - 1.0) < 1e-6, f"Expected 1.0 mA avg, got {payload['average_current_ma']}")
    assert_true(abs(payload["estimated_hours"] - 1000.0) < 1e-3, f"Expected 1000 h, got {payload['estimated_hours']}")

    # 7. check_pin_conflicts.py (clean template + broken fixture)
    pin_script = PLUGIN_ROOT / "skills/embedded-hardware-bringup/scripts/check_pin_conflicts.py"
    template_pinmap = PLUGIN_ROOT / "skills/embedded-hardware-bringup/templates/pinmap_template.json"
    res_ok = run_py(pin_script, ["--pinmap", str(template_pinmap), "--json"])
    assert_true(res_ok.returncode == 0, f"pinmap_template.json should pass cleanly: {res_ok.stdout}")

    with tempfile.TemporaryDirectory() as tmp:
        bad_pinmap = Path(tmp) / "bad.json"
        bad_pinmap.write_text(
            json.dumps({
                "mcu": "esp32",
                "logic_voltage": 3.3,
                "features": ["wifi"],
                "pins": [
                    {"pin": "GPIO6", "signal": "BAD_FLASH", "direction": "output"},
                    {"pin": "GPIO34", "signal": "BAD_OUT", "direction": "output", "pull": "up"},
                    {"pin": "GPIO12", "signal": "WIFI_ADC2", "function": "adc", "direction": "input"},
                    {"pin": "GPIO18", "signal": "SIG_A", "external_voltage": 5.0},
                    {"pin": "GPIO18", "signal": "SIG_B"},
                ],
            }),
            encoding="utf-8",
        )
        res_bad = run_py(pin_script, ["--pinmap", str(bad_pinmap), "--json"])
        assert_true(res_bad.returncode == 1, "Expected check_pin_conflicts to fail on bad pinmap")
        report = json.loads(res_bad.stdout)
        err_text = " | ".join(report["errors"])
        for needle in ("internal SPI flash", "input-only", "no internal pull-up", "ADC2", "Voltage mismatch", "Duplicate"):
            assert_true(needle in err_text, f"Expected '{needle}' in errors: {err_text}")
        assert_true(any("strapping" in w for w in report["warnings"]), "Expected strapping warning on GPIO12")

        # Additional MCU families: ESP32-S3 Octal PSRAM, STM32H7 5V-ADC hazard, RP2040 Pico W, AVR A6
        for fname, doc, expected_err in [
            (
                "s3.json",
                {"mcu": "esp32-s3", "features": ["octal_psram"], "pins": [{"pin": "GPIO35", "signal": "LED"}]},
                "Octal PSRAM",
            ),
            (
                "h7.json",
                {"mcu": "stm32h7", "pins": [{"pin": "PA0", "signal": "VIN", "function": "adc", "external_voltage": 5.0, "five_v_tolerant": True}]},
                "ADC/analog mode",
            ),
            (
                "picow.json",
                {"mcu": "rp2040", "features": ["pico_w"], "pins": [{"pin": "GP25", "signal": "MY_LED"}]},
                "CYW43",
            ),
            (
                "avr.json",
                {"mcu": "avr-5v", "pins": [{"pin": "A6", "signal": "BTN", "function": "gpio"}]},
                "analog-input-only",
            ),
        ]:
            pfile = Path(tmp) / fname
            pfile.write_text(json.dumps(doc), encoding="utf-8")
            r = run_py(pin_script, ["--pinmap", str(pfile), "--json"])
            assert_true(r.returncode == 1, f"Expected error for {fname}")
            errs = " | ".join(json.loads(r.stdout)["errors"])
            assert_true(expected_err in errs, f"Expected '{expected_err}' in {fname} errors: {errs}")

    # 8. query_svd.py (CMSIS-SVD XML + STM32CubeMX .ioc export round-trip)
    svd_script = PLUGIN_ROOT / "skills/embedded-hardware-bringup/scripts/query_svd.py"
    with tempfile.TemporaryDirectory() as tmp:
        svd_file = Path(tmp) / "sample.svd"
        svd_file.write_text(
            """<device>
  <peripherals>
    <peripheral>
      <name>I2C1</name>
      <description>I2C interface 1</description>
      <baseAddress>0x40005400</baseAddress>
      <registers>
        <register>
          <name>CR1</name>
          <description>Control register 1</description>
          <addressOffset>0x00</addressOffset>
          <size>32</size>
          <resetValue>0x00000000</resetValue>
          <fields>
            <field>
              <name>PE</name>
              <description>Peripheral enable</description>
              <bitOffset>0</bitOffset>
              <bitWidth>1</bitWidth>
            </field>
            <field>
              <name>DNF</name>
              <description>Digital noise filter</description>
              <bitRange>[11:8]</bitRange>
            </field>
          </fields>
        </register>
      </registers>
    </peripheral>
    <peripheral derivedFrom="I2C1">
      <name>I2C2</name>
      <baseAddress>0x40005800</baseAddress>
    </peripheral>
  </peripherals>
</device>""",
            encoding="utf-8",
        )
        res_svd = run_py(svd_script, ["--svd", str(svd_file), "--peripheral", "I2C2", "--register", "CR1", "--json"])
        assert_true(res_svd.returncode == 0, f"query_svd SVD failed: {res_svd.stderr}")
        reg = json.loads(res_svd.stdout)
        assert_true(reg["address_hex"] == "0x40005800", f"Derived baseAddress mismatch: {reg}")
        dnf = next(f for f in reg["fields"] if f["name"] == "DNF")
        assert_true(dnf["mask_hex"] == "0x00000F00", f"Bitmask mismatch: {dnf}")

        ioc_file = Path(tmp) / "board.ioc"
        ioc_file.write_text(
            "Mcu.Family=STM32F4\n"
            "Mcu.Name=STM32F407VGTx\n"
            "PA13.Signal=SYS_JTMS-SWDIO\n"
            "PA14.Signal=SYS_JTCK-SWCLK\n"
            "PB6.Signal=I2C1_SCL\n"
            "PB6.GPIO_Label=SENS_SCL\n"
            "PB7.Signal=I2C1_SDA\n"
            "PB7.GPIO_Label=SENS_SDA\n",
            encoding="utf-8",
        )
        exported_pinmap = Path(tmp) / "from_ioc.json"
        res_ioc = run_py(svd_script, ["--ioc", str(ioc_file), "--export-pinmap", str(exported_pinmap), "--json"])
        assert_true(res_ioc.returncode == 0, f"query_svd IOC failed: {res_ioc.stderr}")
        ioc_data = json.loads(res_ioc.stdout)
        assert_true(ioc_data["mcu"] == "stm32f4" and len(ioc_data["pins"]) == 4, f"Unexpected IOC parse: {ioc_data}")

        res_check = run_py(pin_script, ["--pinmap", str(exported_pinmap), "--json"])
        assert_true(res_check.returncode == 0, f"Exported IOC pinmap failed conflict check: {res_check.stdout}")

    print("[PASS] All 8 Python helper scripts passed unit tests")


def check_c_templates() -> None:
    cc = shutil.which("gcc") or shutil.which("clang")
    if not cc:
        print("[SKIP] C syntax check skipped (neither gcc nor clang found on PATH)")
        return
    c_files = [
        PLUGIN_ROOT / "skills/embedded-firmware-drivers/templates/driver_template.c",
    ]
    h_files = [
        PLUGIN_ROOT / "skills/embedded-firmware-drivers/templates/ring_buffer.h",
        PLUGIN_ROOT / "skills/embedded-rtos-lowpower/templates/fsm_template.h",
    ]
    for cf in c_files:
        res = subprocess.run([cc, "-std=c11", "-Wall", "-Wextra", "-Werror", "-fsyntax-only", str(cf)], capture_output=True, text=True, check=False)
        assert_true(res.returncode == 0, f"C syntax error in {cf.name}: {res.stderr}")
    for hf in h_files:
        res = subprocess.run([cc, "-std=c11", "-Wall", "-Wextra", "-Werror", "-x", "c", "-fsyntax-only", str(hf)], capture_output=True, text=True, check=False)
        assert_true(res.returncode == 0, f"Header syntax error in {hf.name}: {res.stderr}")
    print(f"[PASS] C templates compiled cleanly with {Path(cc).name}")


def main() -> int:
    validate_manifest()
    validate_rules_and_agents()
    validate_skills()
    test_scripts()
    check_c_templates()
    print("\nALL VALIDATIONS PASSED.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
