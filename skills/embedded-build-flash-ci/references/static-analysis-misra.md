# Static Analysis & Embedded C/C++ Hardening

## Recommended Compiler Warning Flags (GCC / Clang)
Enable these on project source files (not third-party vendor HALs if they are noisy):
```text
-Wall -Wextra -Wshadow -Wdouble-promotion -Wformat=2 -Wundef
-Wconversion -Wsign-conversion -fno-common -fstack-usage
```
- **`-fstack-usage`** emits `.su` files showing exact per-function stack frame bytes — invaluable for sizing RTOS tasks and checking ISR stack usage.
- **`-Wdouble-promotion`** catches accidental `double` software emulation on single-precision FPU MCUs (Cortex-M4F, ESP32) when writing `1.5` instead of `1.5f`.
- **`-fno-common`** turns tentative duplicate globals into link errors instead of silent aliasing.

## `cppcheck` Preset for Embedded C/C++
```bash
cppcheck --enable=warning,style,performance,portability \
  --inconclusive --inline-suppr --error-exitcode=1 \
  --suppress=missingIncludeSystem src/
```
Key checks it catches: uninitialized variables, buffer overruns, null dereferences, shift overflow, unreachable code, and unused struct members.

## `clang-tidy` Preset (requires `compile_commands.json`)
Generate `compile_commands.json` via `-DCMAKE_EXPORT_COMPILE_COMMANDS=ON` or `pio run -t compiledb`.
Recommended check groups:
- `bugprone-*` (especially `bugprone-narrowing-conversions`, `bugprone-branch-clone`, `bugprone-suspicious-memset-usage`)
- `cert-err34-c`, `cert-int09-c`, `cert-msc50-cpp`
- `misc-const-correctness`, `readability-implicit-bool-conversion`
- `clang-analyzer-*`

## Pragmatic MISRA-C Subset for High-Reliability Firmware
Even without a formal MISRA certification tool, enforce these highest-value rules:
1. No dynamic heap allocation after startup (`malloc`/`calloc`/`realloc`/`free`).
2. Every `switch` has a `default:` branch; every non-empty `case` ends with `break` or an explicit `/* fallthrough */`.
3. Single-exit or clearly structured cleanup paths; never leave a mutex locked or chip-select asserted on error return.
4. No recursion (breaks static stack bound analysis).
5. Always use explicit unsigned suffixes (`1UL << bit`) for bitmasks and fixed-width types (`uint32_t`).
