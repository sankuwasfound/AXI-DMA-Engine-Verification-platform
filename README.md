# 🚀 AXI DMA Engine & Verification Platform

![SystemVerilog](https://img.shields.io/badge/SystemVerilog-RTL-blue)
![Python](https://img.shields.io/badge/Python-Verification-yellow)
![cocotb](https://img.shields.io/badge/cocotb-2.1.0-orange)
![Verilator](https://img.shields.io/badge/Verilator-5.036-green)
![Tests](https://img.shields.io/badge/Regression-18%2F18%20Passing-brightgreen)
![Coverage](https://img.shields.io/badge/Functional%20Scenarios-14%2F14-blueviolet)
![Status](https://img.shields.io/badge/Current%20Milestone-M11-blue)

A SystemVerilog-based Direct Memory Access (DMA) engine supported by a Python-driven verification environment using cocotb, Verilator, randomized testing, protocol monitoring, and functional coverage.

**Repository:** [AXI-DMA-Engine-Verification-platform](https://github.com/sankuwasfound/AXI-DMA-Engine-Verification-platform)

**Current progress:** M11 completed · M12–M16 planned

---

## 📌 Project Overview

This project aims to develop a reusable DMA engine and a verification platform that tests data integrity, burst transfers, backpressure, descriptor queuing, error handling, reset recovery, and response timing.

Rather than validating only basic transfers, the project progressively builds a verification environment that exercises difficult transaction scenarios and produces reproducible results.

### 🎯 Objectives

- Implement a memory-to-memory DMA engine in SystemVerilog.
- Verify AXI-style read and write handshakes.
- Support and test burst transfers.
- Handle backpressure and delayed responses.
- Test descriptor queuing and error recovery.
- Build reusable Python-based verification components.
- Introduce randomized testing and functional coverage.
- Extend the platform with protocol assertions and additional corner-case testing.

---

## 📊 Current Verification Results

| Metric | Latest recorded result |
|---|---:|
| Regression tests passed | 18/18 |
| Failed tests | 0 |
| Skipped tests | 0 |
| Defined functional scenarios hit | 14/14 |
| Randomized descriptors checked | 20 |
| Maximum tested burst | 16 beats |
| Simulation time | 12,766.03 ns |

The latest recorded regression passed all 18 tests, with 14 of 14 defined functional coverage scenarios hit.

**Note:** Functional scenario coverage is not RTL code coverage or formal proof of correctness.

---

## 🏗️ Architecture

```text
                 Transfer Descriptor
            Source / Destination / Length
                         |
                         v
                +------------------+
                |   DMA Controller |
                |   State Machine  |
                +------------------+
                         |
                         v
                +------------------+
                |   AXI Master     |
                | Read / Write     |
                | Transactions     |
                +------------------+
                         |
                         v
                +------------------+
                |  AXI Memory Model|
                | Data / Responses |
                | Delays / Stalls  |
                +------------------+
                         ^
                         |
                +------------------+
                | cocotb Testbench |
                | Assertions /     |
                | Checks / Coverage|
                +------------------+
```

This is a conceptual view of the verification environment, not a claim that each block is a separate synthesizable RTL module.

### ⚙️ Current tested configuration

- Data width: 32 bits
- Bytes per beat: 4
- Maximum tested burst: 16 beats
- Descriptor queue depth: 4
- Reset: active-low, synchronous

### 🔌 AXI channel groups

- **AR — Read Address:** Issues read requests.
- **R — Read Data:** Receives source data and response status.
- **AW — Write Address:** Issues destination write requests.
- **W — Write Data:** Transfers payload data and byte strobes.
- **B — Write Response:** Receives write transaction responses.

The verification environment checks handshakes and selected stall and response-timing scenarios. Complete AXI protocol compliance has not yet been established.

---

## 🧪 Technology Stack

| Technology | Purpose |
|---|---|
| SystemVerilog | DMA RTL implementation |
| Verilator 5.036 | RTL simulation |
| cocotb 2.1.0 | Python-based hardware verification |
| Python | Memory model, tests, and coverage |
| pytest | Memory-model unit tests |
| Make | Regression execution |
| Git and GitHub | Version control and collaboration |
| GTKWave | Optional waveform debugging |

---

# 🗺️ Development Roadmap: M1–M16

The first eleven milestones summarize the existing development progression. M12–M16 are planned and should only be marked complete when implementation and verification evidence are available.

## ✅ M1 — Basic DMA Transfer

Implemented the initial memory-to-memory transfer.

- Single-word data movement.
- Source and destination addressing.
- Basic start and completion behavior.
- Destination data verification.

**Verification:** The test copies `0xDEADBEEF` from `0x00001000` to `0x00002000`.

## ✅ M2 — Memory Model Integration

Introduced a reusable Python memory model.

- Initialize source memory.
- Model memory transactions.
- Check destination contents.
- Reuse memory-model behavior across tests.

## ✅ M3 — Transfer Validation and Error Handling

Added tests for invalid transfers and AXI errors.

- Zero-length transfer rejection.
- Unaligned source-address rejection.
- Read-response `SLVERR`.
- Write-response `SLVERR`.
- Error versus successful completion checks.

## ✅ M4 — Burst Transfers

Expanded testing beyond single-word transactions.

- Two-beat bursts.
- Four-beat bursts.
- Maximum 16-beat burst.
- Per-beat destination data checks.

## ✅ M5 — Backpressure Handling

Added stalls to selected AXI channels.

- Read-address (`AR`) stalls.
- Write-address (`AW`) stalls.
- Write-data (`W`) stalls.
- Checks for stable transaction information during tested stalls.

Dedicated response-channel backpressure testing remains future work.

## ✅ M6 — Delayed Response Handling

Extended the memory model to delay read and write responses.

- Configurable read-response delay.
- Configurable write-response delay.
- Checks that completion waits for responses.
- Data integrity verification after delayed responses.

## ✅ M7 — Descriptor Queue

Added queued-transfer verification.

- Multiple descriptors.
- FIFO-order execution.
- Full-queue rejection.
- Checks against descriptor loss or reordering.

## ✅ M8 — Randomized Descriptor Testing

Introduced repeatable randomized transactions.

- Seeded randomized descriptors.
- Data-integrity checks.
- Reproducible test execution.
- Debug output containing the random seed.

**Latest recorded evidence:** 20 randomized descriptors passed with seed `23063`.

## ✅ M9 — Reset Recovery

Tested recovery from reset during active work.

- Reset during a delayed read.
- Reset during a write burst.
- Reset with queued descriptors.
- Fresh transfers after reset.

## ✅ M10 — Memory Model Unit Tests

Strengthened independent testing of the Python memory model.

- Configuration validation.
- Deterministic randomized-ready behavior.
- Byte-strobe updates.
- Write-response delay configuration.
- Seeded delay reproducibility.

**Recorded result:** 16 unit tests passed.

## ✅ M11 — Write-Response Timing Verification

Strengthened response timing checks and memory-model helpers.

- Extracted byte-strobe handling into a helper.
- Added write-response delay scheduling.
- Tested fixed and seeded-random delay behavior.
- Measured final write-beat to `BVALID` timing.
- Preserved regression compatibility.

**Recorded result:** All 18 regression tests passed.

## 🔄 M12 — AXI Response-Channel Backpressure

**Planned**

- Verify `RVALID/RREADY` handshake behavior.
- Verify `BVALID/BREADY` handshake behavior.
- Test responses held while the receiver is not ready.
- Ensure completion does not occur before the required handshake.
- Add dedicated response-channel stall tests.

## 🔄 M13 — Protocol Assertions

**Planned**

- Add reusable protocol invariants.
- Check payload stability during stalls.
- Check transaction sequencing.
- Detect unexpected state transitions.
- Evaluate SystemVerilog assertions and cocotb monitors.

## 🔄 M14 — Corner Cases and Fault Injection

**Planned**

- Expand reset and error timing scenarios.
- Test additional boundary conditions.
- Inject controlled transaction faults.
- Exercise randomized legal stalls.
- Preserve seeds and debug information for reproducibility.

## 🔄 M15 — Performance Metrics and Coverage Expansion

**Planned**

- Measure transfer latency.
- Count stall cycles by channel.
- Track bytes transferred and effective throughput.
- Expand functional coverage bins.
- Produce reproducible regression summaries.

## 🔄 M16 — Final Verification and Release Readiness

**Planned**

- Run the complete regression from a clean build.
- Review warnings and known limitations.
- Document the implemented AXI subset.
- Add formal verification only where the tool flow supports it and the properties are actually proven.
- Explore synthesis reports where appropriate.
- Publish final verification evidence.
- Tag a release after acceptance criteria are met.

---

## 📁 Repository Structure

```text
axi_dma/
├── rtl/
│   └── axi_dma.sv
├── tb/
│   ├── axi_memory_model.py
│   ├── axi_protocol_monitor.py
│   ├── functional_coverage.py
│   └── tests/
│       ├── test_axi_dma.py
│       ├── test_axi_dma_model.py
│       ├── test_axi_dma_errors.py
│       ├── test_axi_dma_bursts.py
│       ├── test_axi_dma_backpressure.py
│       ├── test_axi_dma_response_delays.py
│       ├── test_axi_dma_queue.py
│       ├── test_axi_dma_randomized.py
│       ├── test_axi_dma_reset.py
│       └── test_axi_memory_model_unit.py
├── Makefile
└── README.md
```

This is a summary of the main project files; the exact repository structure may evolve.

---

## 🛠️ Setup and Execution

### 1. Activate the Python environment

```bash
cd ~/axi_dma
source ~/cocotb-env/bin/activate
export PATH="$HOME/opt/verilator-5.036/bin:$PATH"
```

### 2. Run the full regression

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 make
```

### 3. Run memory-model unit tests

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
PYTHONPATH="$PWD/tb:$PWD/tb/tests" \
python -m pytest -q tb/tests/test_axi_memory_model_unit.py
```

Review the final regression summary, test failures, random seed, and coverage report.

---

## 📈 Verification Methodology

### Directed testing
Exercises specific scenarios such as single-word copies, maximum bursts, invalid requests, and reset recovery.

### Reference data checking
Compares destination memory contents with expected source data.

### Randomized testing
Broadens the transaction space using reproducible random seeds.

### Timing and stall testing
Introduces backpressure and delayed responses to exercise non-zero-wait-state behavior.

### Unit testing
Tests reusable memory-model functionality independently of the RTL regression.

### Functional coverage
Tracks explicitly defined verification scenarios and reports which scenarios were observed.

These methods complement each other; none alone proves complete protocol compliance.

---

## ⚠️ Known Limitations

- Full AXI compliance has not been established.
- Functional coverage does not equal RTL code coverage.
- Randomized testing is not exhaustive.
- Formal correctness has not been established merely by simulation.
- FPGA synthesis and timing closure have not been demonstrated by the current regression.
- Dedicated response-channel backpressure verification remains planned.
- Performance claims should be based on measured results from a documented methodology.

---

## 📚 References

- [Arm AMBA Specifications](https://developer.arm.com/Architectures/AMBA)
- [SystemVerilog Standards](https://standards.ieee.org/)
- [Verilator Documentation](https://verilator.org/guide/latest/)
- [cocotb Documentation](https://docs.cocotb.org/)
- [GTKWave](https://gtkwave.github.io/gtkwave/)
- [Yosys Documentation](https://yosyshq.readthedocs.io/)
- [SymbiYosys Documentation](https://symbiyosys.readthedocs.io/)
- [AMD Vivado Documentation](https://docs.amd.com/)

---

## 🎯 Project Goal

Build a reusable DMA IP and a robust verification platform that goes beyond basic data movement through systematic testing of timing, backpressure, error handling, reset recovery, and transaction corner cases.

**Current milestone:** M11 — Write-Response Timing Verification  
**Next milestone:** M12 — AXI Response-Channel Backpressure  
**Target milestone:** M16 — Final Verification and Release Readiness
