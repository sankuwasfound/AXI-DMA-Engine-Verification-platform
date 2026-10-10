# M15 — Reset and Recovery Verification Findings

## Status

**Diagnostic finding reproduced; RTL recovery fix not implemented.**

M15 investigates DMA reset during active transfers, descriptor-queue cleanup,
recovery after reset, and the possibility of stale AXI responses affecting a
subsequent transfer.

## Existing reset-recovery tests

The following tests passed in the isolated reset suite:

- `reset_aborts_delayed_read_and_recovers`
- `reset_aborts_write_burst_and_recovers`
- `reset_clears_queued_descriptors`

Result: **3/3 passed**.

These tests verify internal DMA reset behavior and successful fresh transfers
after the test also clears the simulated memory model's pending response state.
They do not establish immunity to stale responses from an external slave that
continues operating across a DMA-only reset.

## Stale read-response diagnostic

File: `tb/tests/test_m15_late_response_diagnostic.py`

The diagnostic injects a successful one-beat read response while a fresh
transfer is in `READ_DATA`, after resetting the DMA and clearing the memory
model's scheduled response.

- Expected fresh source data: `0x12345678`
- Injected stale data: `0xDEADCAFE`
- Observed destination data at `0x4000`: `0xDEADCAFE`

Result: **The suspected stale-read-response limitation was reproduced.**

The diagnostic uses controlled response injection. It does not model a
complete external slave naturally returning an outstanding response.

## Stale write-response diagnostic

File: `tb/tests/test_m15_stale_write_response_diagnostic.py`

The diagnostic delays the old write response, resets the DMA, suppresses the
memory model's scheduled response, and injects a successful `BVALID` while a
fresh transfer is in `WRITE_RESP`.

Result: **The suspected stale-write-response limitation was reproduced.**
The DMA asserted `done` after accepting the injected response, before the
fresh transaction's own write response was generated.

This is a controlled diagnostic, not a complete external-slave integration
test.

## Technical interpretation

The DMA reset clears its internal FSM, descriptor queue, counters, and status
registers. It does not itself cancel a transaction already accepted by an
external AXI slave.

The current RTL has no transaction IDs or retained recovery state that lets it
distinguish a response from an earlier transaction from a response belonging
to a fresh transaction. `RVALID/RREADY` can be accepted in `READ_DATA`, and
`BVALID/BREADY` can be accepted in `WRITE_RESP`, without that distinction.

Therefore, reset recovery is **not proven safe when an external slave may
return responses from transactions outstanding before the DMA reset**.

## Limitations and next work

- No production RTL fix has been made as part of these diagnostics.
- The diagnostics pass when they reproduce the known limitation; they are not
  passing safety tests for stale-response immunity.
- The current memory model is a simplified model of the DMA's documented AXI
  subset, not a complete AXI4-compliant slave.
- A recovery design must define how outstanding reads and writes are handled,
  including delayed or missing responses, partially completed writes, and
  when new descriptors may safely start.
- An integration-level reset/quiescence contract is an alternative, but must
  be explicit and verified at system level.

## Regression context

The existing reset suite passed 3/3 tests, and each standalone stale-response
diagnostic passed 1/1 by reproducing its target behavior. These results are
separate from the full regression result. Run the full regression again before
closing M15, and report its result independently.

The diagnostics are intentionally not added to the normal regression list.
