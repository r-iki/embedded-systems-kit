# Deterministic Finite State Machine (FSM) Architecture

## Why Explicit FSMs Beat Boolean Flag Soup
When firmware tracks device lifecycle with ad-hoc flags (`connected`, `calibrating`, `retry_pending`, `low_battery`), `N` booleans create `2^N` implicit states — most of them untested and invalid. An explicit FSM restricts behavior to a small set of valid states and well-defined transitions.

## Core Design Rules
1. **Single event queue / dispatch point**: Feed hardware events (button press, sensor ready, packet RX, timeout tick) into one `fsm_dispatch(fsm, event)` entry point.
2. **Entry & Exit actions**: Put peripheral enable/disable and timer start/stop in `on_enter` and `on_exit` hooks so resources are always cleaned up regardless of which transition leaves a state.
3. **Every waiting state has a timeout**: Any state waiting for external hardware or network (`WAIT_ACK`, `CONNECTING`, `CALIBRATING`) must arm a timeout event that transitions cleanly to `RETRY` or `FAULT`.
4. **No blocking inside state handlers**: State handlers compute the next state, trigger non-blocking I/O, and return immediately.
5. **Log transitions**: Emit compact state-transition traces (`STATE_IDLE --[EVT_START]--> STATE_MEASURE`) during bring-up for instant debugging.

## When to Use Table-Driven vs Switch-Based FSM
- **Switch-based (`switch (fsm->state)`)**: Best for 3-8 states with simple guards; minimal boilerplate and easy to read.
- **Table-driven (`{current_state, event, guard, action, next_state}`)**: Best for protocol parsers or 8+ states where a concise transition matrix makes missing combinations obvious during code review.
