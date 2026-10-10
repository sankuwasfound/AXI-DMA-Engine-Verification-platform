# AXI DMA Engine and Verification Platform

A SystemVerilog DMA implementation and Python-based verification environment built around Verilator and cocotb. The project focuses on descriptor-driven transfers, burst behavior, transaction errors, queueing, backpressure, reset behavior, and reproducible verification evidence.

Repository: https://github.com/sankuwasfound/AXI-DMA-Engine-Verification-platform

## Project status

**Current state: M16 verification checkpoint recorded; not production sign-off.**

The implementation and verification environment have progressed beyond a basic DMA demonstration. The repository includes a standard cocotb regression, standalone Python unit tests for reusable verification components, a protocol monitor, functional scenario tracking, and a release-readiness report.

The evidence is encouraging, but there are known reset-recovery limitations involving stale AXI responses after a DMA-only reset. Those findings remain open and must not be treated as fixed.

## At a glance

| Item | Recorded result |
|---|---|
| RTL language | SystemVerilog |
| Simulator | Verilator 5.036 |
| Verification framework | cocotb 2.1.0 |
| Python environment used for the M16 report | Python 3.14.0 |
| Standard regression | 18 passed, 0 failed, 0 skipped |
| Standalone unit tests | 41 passed |
| Defined functional scenarios hit | 14 of 14 |
| Maximum tested burst | 16 beats |
| Recorded simulation duration | 12,766.03 ns |
| Lint | Completed without reported warnings or errors in the recorded run |
| Release assessment | Simulation/verification checkpoint only |

Functional scenario coverage is not RTL statement, branch, toggle, or condition coverage. Simulation and assertions are not a formal proof of correctness.

## Why this project exists

A DMA engine is not adequately evaluated by demonstrating one successful copy. Verification must also exercise transaction sequencing, data integrity, response timing, queue behavior, error handling, and the conditions that occur when an AXI channel is stalled.

This project pairs the RTL with a reusable test environment so that design behavior can be checked repeatedly and failures can be investigated using reproducible tests and recorded evidence.

The current emphasis is on making the behavior observable and documenting limitations honestly, rather than claiming complete AXI4 compliance or production readiness.

## Scope and implemented verification

The recorded regression covers the following areas:

- Basic data transfers and memory-model integration.
- Descriptor validation, including zero-length and unaligned-address rejection scenarios.
- Read and write error responses.
- Burst transfers, including tests up to 16 beats.
- Address-channel and write-data-channel stalls.
- Delayed read and write responses.
- Descriptor queue FIFO ordering and queue-full rejection.
- Seeded randomized descriptor traffic.
- Reset scenarios during active or queued work.
- Protocol-monitor checks for VALID and payload stability while AR, R, AW, W, or B is stalled.

The exact supported AXI subset is determined by the RTL and its tests. The project does not claim complete AXI4 compliance or exhaustive coverage of all legal and illegal protocol combinations.

### Tested configuration recorded in the project README

- Data width: 32 bits.
- Bytes per beat: 4.
- Maximum tested burst: 16 beats.
- Descriptor queue depth: 4.
- Reset: active-low, synchronous.

These values describe the recorded tested configuration; they should not be interpreted as a claim that every parameter is configurable or that every configuration has been verified.

## Conceptual architecture

```text
                    Transfer descriptor
              source / destination / length
                           |
                           v
                  +------------------+
                  |   DMA controller |
                  |   state machine  |
                  +------------------+
                           |
                           v
                  +------------------+
                  |   AXI master     |
                  | read and write   |
                  | transactions     |
                  +------------------+
                           |
                           v
                  +------------------+
                  | AXI memory model |
                  | data, responses, |
                  | delays and stalls|
                  +------------------+
                           ^
                           |
                  +------------------+
                  | cocotb testbench |
                  | checks, monitor, |
                  | reference data,  |
                  | scenario tracking|
                  +------------------+
```

This diagram describes the relationship between the design and its verification environment. It is conceptual and does not imply that every box is a separate synthesizable RTL module.

### AXI channels exercised

| Channel | Purpose |
|---|---|
| AR | Read-address requests |
| R | Read data and read response status |
| AW | Write-address requests |
| W | Write data and byte strobes |
| B | Write response status |

The verification environment includes checks for selected handshake, stall, and response-timing scenarios. The unresolved reset findings described below are important to interpreting those results.

## Verification results

### Standard cocotb regression

The recorded M16 run used Verilator with simulation assertions enabled.

| Metric | Result |
|---|---:|
| Tests | 18 |
| Passed | 18 |
| Failed | 0 |
| Skipped | 0 |
| Simulation duration | 12,766.03 ns |

The regression includes transfer, error, burst, stall, delayed-response, queue, randomized-traffic, and reset scenarios.

Run the regression from the project directory:

```bash
cd ~/axi_dma
source ~/cocotb-env/bin/activate
export PATH="$HOME/opt/verilator-5.036/bin:$PATH"
PYTHONPATH="$PWD/tb/tests:$PWD/tb${PYTHONPATH:+:$PYTHONPATH}" \
  PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 make
```

Review the actual command output when rerunning the suite. The numbers above are the recorded M16 results, not a guarantee that every future checkout or environment will produce identical results without changes.

### Standalone Python unit tests

The reusable memory-model and protocol-monitor unit tests passed independently of the main RTL regression.

| Test suite | Result |
|---|---:|
| `test_axi_memory_model_unit.py` | 16 passed |
| `test_axi_protocol_monitor_unit.py` | 25 passed |
| **Total** | **41 passed** |

Run them with:

```bash
cd ~/axi_dma
source ~/cocotb-env/bin/activate
PYTHONPATH="$PWD/tb:$PWD/tb/tests${PYTHONPATH:+:$PYTHONPATH}" \
  PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
  python -m pytest -v \
  tb/tests/test_axi_memory_model_unit.py \
  tb/tests/test_axi_protocol_monitor_unit.py
```

### RTL lint

The recorded lint command was:

```bash
cd ~/axi_dma
verilator --lint-only --assert -Wall -Wno-fatal \
  --top-module axi_dma rtl/axi_dma.sv
```

The recorded run completed without reported warnings or errors. Because `-Wno-fatal` is enabled, lint cleanliness should be judged from the emitted diagnostics, not from the exit status alone.

### Functional scenario coverage

The regression reported **14 of 14 defined functional scenarios hit**.

The defined scenarios include transfer lengths, invalid requests, AXI read/write error responses, address and write-data backpressure, queue FIFO ordering, queue-full rejection, and seeded randomized stress.

This is coverage of the scenarios defined by the project. It is not evidence of 100% RTL code coverage, exhaustive input-space exploration, or formal correctness.

### Isolated response-backpressure harness

A separate response-channel backpressure harness passed its standalone test (1 of 1 in the recorded report). It is an isolated harness, not proof that the production DMA RTL safely supports every possible multi-cycle R- or B-channel stall. Keep this distinction in mind when interpreting the result.

## Reset-recovery findings

Two diagnostic tests reproduced unresolved problems. A passing diagnostic means the test successfully reproduced the targeted issue; it does not mean the issue was fixed.

### Stale read response after DMA-only reset

The diagnostic observed destination data `0xDEADCAFE` where the fresh transfer was expected to deliver `0x12345678`.

**Finding:** A stale read response could be consumed as data for a fresh transfer after the DMA was reset.

### Stale write response after DMA-only reset

The diagnostic found that an old successful B response could be accepted as completion of a fresh transaction before the fresh transaction's own response was generated.

**Finding:** A stale write response could be misattributed to a new transaction.

### Why this matters

The ordinary reset tests clear pending responses in the memory model. They therefore do not prove that the DMA is safe when an external AXI slave or interconnect continues operating across a DMA-only reset.

A robust solution needs an explicit reset and transaction-lifecycle contract. Depending on the system, possible approaches include coordinated reset, quiescing traffic before reset, draining outstanding transactions, or a suitable transaction-epoch mechanism. The correct design depends on the integration requirements and must be implemented and retested before claiming robust reset recovery.

The detailed evidence is recorded in [M16 Release Readiness](docs/m16_release_readiness.md).

## Known limitations

1. **Stale response handling remains unresolved.** R and B responses from before a DMA-only reset can be misattributed to a post-reset transfer.
2. **Reset integration assumptions need to be explicit.** External AXI transactions may outlive a reset applied only to the DMA.
3. **Complete AXI4 compliance has not been established.** The tested subset is not exhaustive protocol certification.
4. **Functional coverage is limited to defined scenarios.** The 14/14 result is not RTL code coverage.
5. **Formal proof has not been established.** Simulation assertions and regression results are not a formal verification result.
6. **Response backpressure evidence is limited.** The isolated harness does not establish arbitrary response-stall robustness in the production RTL.
7. **FPGA readiness has not been demonstrated.** No claim of synthesis sign-off, timing closure, or hardware validation is made here.
8. **Performance characterization is incomplete.** Throughput and latency claims require a documented measurement methodology and measured results.

## Repository guide

The main areas of the repository are:

```text
axi_dma/
├── rtl/
│   └── axi_dma.sv
├── tb/
│   ├── axi_memory_model.py
│   ├── axi_protocol_monitor.py
│   ├── functional_coverage.py
│   └── tests/
├── docs/
│   └── m16_release_readiness.md
├── Makefile
├── .gitignore
└── README.md
```

This is a high-level guide to the main components, not a guarantee that every test file is listed. Consult the repository for the current file inventory.

- **`rtl/`** — DMA RTL.
- **`tb/axi_memory_model.py`** — Python-side memory and response behavior used by verification.
- **`tb/axi_protocol_monitor.py`** — reusable protocol-monitor checks.
- **`tb/functional_coverage.py`** — functional scenario tracking.
- **`tb/tests/`** — directed, randomized, diagnostic, and unit tests.
- **`docs/m16_release_readiness.md`** — recorded test evidence, reset diagnostics, and readiness assessment.
- **`.gitignore`** — excludes Python artifacts and simulation build products, including the named local build directories.

Generated simulation output and local backup files are not part of the intended source deliverables.

## Reproducibility notes

- Use the tool versions recorded in the readiness report when comparing results.
- Keep random seeds in test output and retain failing seeds.
- Read diagnostic test names and descriptions carefully; some diagnostics are designed to reproduce known failures.
- Inspect waveforms and logs when a test fails rather than relying only on a summary count.
- Re-run lint and regression after RTL or testbench changes.
- Keep the documentation aligned with the actual implementation and most recent test evidence.

## Development priorities

The next work should focus on correctness gaps rather than simply adding more tests or increasing headline coverage.

1. Define the system-level reset contract for outstanding AXI transactions.
2. Design a recovery strategy that prevents pre-reset responses from being attributed to post-reset transactions.
3. Add regression tests that retain outstanding external responses across a DMA-only reset.
4. Re-run the stale-R and stale-B diagnostics and demonstrate that the corrected behavior passes.
5. Integrate response-channel backpressure scenarios into the production RTL regression, with clear assumptions about legal AXI behavior.
6. Re-run the full regression, unit tests, and lint; preserve tool versions, logs, and random seeds.
7. Reassess release readiness only after the findings are closed with evidence.

## Technical references

Prefer specifications and official tool documentation over informal summaries. The exact applicable AXI specification revision and implementation subset should be documented as the design evolves.

- [Arm AMBA specifications](https://developer.arm.com/Architectures/AMBA) — AXI protocol semantics.
- [IEEE Standards](https://standards.ieee.org/) — SystemVerilog language standards.
- [Verilator documentation](https://verilator.org/guide/latest/) — linting, simulation, and supported language features.
- [cocotb documentation](https://docs.cocotb.org/) — Python-based hardware verification.
- [GTKWave documentation](https://gtkwave.github.io/gtkwave/) — waveform inspection.
- [Accellera](https://www.accellera.org/) — verification methodology resources.
- [Yosys documentation](https://yosyshq.readthedocs.io/) — optional synthesis and RTL exploration.
- [SymbiYosys documentation](https://symbiyosys.readthedocs.io/) — optional formal-verification workflows.
- [AMD Vivado documentation](https://docs.amd.com/) — optional FPGA implementation and timing analysis.

## Engineering standard

The goal is not to present the DMA as finished merely because a regression passes. The goal is to build a reusable RTL component whose supported behavior is specified, whose important failure modes are tested, whose limitations are visible, and whose readiness claims are backed by reproducible evidence.

**Current checkpoint:** regression, unit-test, lint, and functional-scenario evidence recorded; stale-response reset-recovery findings remain open.
