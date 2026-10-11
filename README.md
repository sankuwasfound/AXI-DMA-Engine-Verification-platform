# AXI DMA Engine and Verification Platform

**A descriptor-driven DMA RTL project with a Python-based verification environment**

Repository: https://github.com/sankuwasfound/AXI-DMA-Engine-Verification-platform

**Primary technologies:** SystemVerilog, cocotb, Verilator, Python, pytest, AXI protocol monitoring, functional coverage, and Git.

**Project checkpoint:** M16 verification and release-readiness assessment recorded.

**Current engineering status:** The main regression, standalone unit tests, and defined functional scenarios have passed their recorded checks. Reset-recovery issues involving stale AXI responses remain unresolved. This repository is a verification checkpoint, not a production sign-off.

---

## Table of Contents

1. Project Overview
2. Problem Statement
3. Project Objectives
4. Features and Scope
5. System Architecture
6. AXI Interface Overview
7. RTL Design and Transfer Flow
8. Verification Architecture
9. Technology Stack
10. Development Roadmap: M1–M16
11. Current Verification Results
12. Testbench and Verification Components
13. Reset-Recovery Investigation
14. Repository Structure
15. Installation and Setup
16. Running the Regression
17. Running Unit Tests
18. Linting the RTL
19. Debugging and Waveform Analysis
20. Functional Coverage
21. Known Limitations
22. Remaining Engineering Work
23. Reproducibility and Engineering Practices
24. Technical References
25. Final Project Assessment

---

# 1. Project Overview

The AXI DMA Engine and Verification Platform is a hardware design and verification project focused on implementing and systematically testing a Direct Memory Access (DMA) engine using SystemVerilog.

Direct Memory Access allows data to be transferred between memory locations without requiring a processor to handle every individual data movement operation. A DMA engine typically receives transfer information, coordinates memory transactions, manages transaction state, and reports completion or errors.

The objective of this project is to develop a descriptor-driven DMA implementation and a reusable verification environment capable of testing more than basic successful transfers.

The verification effort includes:

- Memory-to-memory data transfers.
- Descriptor validation and queue management.
- Burst transaction testing.
- AXI read and write response handling.
- Address-channel and write-data-channel stalls.
- Delayed responses.
- Seeded randomized transaction testing.
- Reset scenarios.
- Python-based memory-model unit tests.
- AXI protocol monitoring.
- SystemVerilog assertions.
- Functional scenario coverage.
- Diagnostic tests for reset-recovery failures.
- Documented verification results and release-readiness limitations.

The project is structured as an iterative engineering effort. Each milestone adds implementation functionality, verification capability, or evidence about the design's limitations.

The central principle is that a passing regression is evidence for the scenarios tested, not proof that the design is correct for every possible transaction sequence.

# 2. Problem Statement

A DMA engine may appear correct when tested with a single memory copy under ideal conditions. That test alone does not establish that the design behaves correctly when transactions encounter delays, errors, queue pressure, reset events, or channel stalls.

Potential failure conditions include:

- Incorrect source or destination data.
- Invalid transfer descriptors.
- Incorrect burst sequencing.
- Loss or reordering of queued descriptors.
- Premature transaction completion.
- Failure to handle error responses.
- Incorrect behavior when a request channel is stalled.
- Incorrect handling of delayed responses.
- Protocol-monitor violations.
- Responses from transactions issued before reset being associated with transactions issued after reset.

These conditions require a verification environment that can control transaction timing, inspect protocol activity, compare transferred data against expected values, and reproduce failures.

This project addresses those needs through an RTL design and a Python-driven verification platform.

# 3. Project Objectives

The primary objectives are:

1. Implement a descriptor-driven DMA engine in SystemVerilog.
2. Support memory-to-memory transfer operations.
3. Exercise AXI-style read and write transaction channels.
4. Test burst transfers beyond single-word operations.
5. Validate descriptor acceptance and rejection behavior.
6. Exercise descriptor queue ordering and full-queue conditions.
7. Test read and write error responses.
8. Introduce address and data-channel stalls.
9. Introduce delayed read and write responses.
10. Develop reusable Python verification components.
11. Build directed and randomized test scenarios.
12. Check data integrity using expected source and destination data.
13. Add protocol monitoring and selected RTL assertions.
14. Track explicitly defined functional verification scenarios.
15. Investigate reset recovery when transactions remain outstanding.
16. Maintain reproducible test commands and recorded verification evidence.
17. Document unresolved issues and establish concrete criteria for further development.

# 4. Features and Scope

## 4.1 DMA functionality

The project covers the following implemented or tested behavior:

- Descriptor-driven transfer requests.
- Source and destination address handling.
- Transfer-length validation.
- Memory-to-memory data movement.
- Burst transaction scenarios.
- Descriptor queueing.
- FIFO-order verification.
- Queue-full rejection scenarios.
- Read-response error handling.
- Write-response error handling.
- Completion and error observations.
- Reset scenarios during active or queued work.

The exact interface contract and supported AXI subset are determined by the current RTL and associated tests.

## 4.2 Verification functionality

The verification platform includes:

- A Python-side AXI memory model.
- Directed cocotb tests.
- Seeded randomized descriptor testing.
- Configurable response-delay behavior.
- Selected request-channel backpressure scenarios.
- An AXI protocol monitor.
- SystemVerilog simulation assertions.
- Functional scenario tracking.
- Standalone Python unit tests.
- Reset-recovery diagnostic tests.
- Regression and lint commands.
- A release-readiness report documenting test evidence and limitations.

## 4.3 Scope boundaries

The project does not currently claim:

- Complete AXI4 compliance.
- Exhaustive verification of all legal and illegal transaction timings.
- Formal proof of correctness.
- Complete RTL statement, branch, toggle, or condition coverage.
- Proven resilience to arbitrary stale responses after DMA-only reset.
- Production-ready handling of every response-channel backpressure scenario.
- FPGA timing closure or hardware validation.
- Production release qualification.

These boundaries are important when interpreting the verification results.

# 5. System Architecture

The project consists of the DMA RTL and its surrounding verification environment.

## 5.1 Conceptual architecture

## System Architecture

The following diagram illustrates the data flow from the Transfer Descriptor through the DMA Controller and AXI interfaces, monitored by the cocotb testbench:

```mermaid
flowchart TD
    %% Input Trigger
    Desc(Transfer Descriptor<br/>Source / Destination / Length)

    %% Architecture Blocks
    DMA[DMA Controller<br/>State Machine]
    AXI_M[AXI Master<br/>Read and Write<br/>Transaction Control]
    AXI_MEM[AXI Memory Model<br/>Data and Responses<br/>Delays and Stalls]
    TB[cocotb Testbench<br/>Data Checks<br/>Protocol Monitoring<br/>Assertions/Checks<br/>Functional Coverage]

    %% Flow Connections
    Desc --> DMA
    DMA --> AXI_M
    AXI_M --> AXI_MEM
    TB -->|Monitors / Drives| AXI_MEM

This is a conceptual representation of the design and verification relationship. It does not imply that every block shown is a separate synthesizable RTL module.

## 5.2 DMA controller

The DMA controller coordinates transfer execution using the supplied transfer information.

The verification environment exercises:

- Descriptor acceptance.
- Transfer initiation.
- Read and write transaction sequencing.
- Burst progression.
- Descriptor queue execution.
- Completion behavior.
- Error behavior.
- Reset scenarios.

The internal implementation should be understood from the current RTL source, particularly `rtl/axi_dma.sv`.

## 5.3 Memory model

The Python memory model provides a controllable environment for testing DMA transactions.

Its verification responsibilities include:

- Representing memory contents.
- Providing source data for reads.
- Recording destination writes.
- Checking data movement.
- Applying byte strobes where supported by the test.
- Modelling response behavior.
- Introducing configurable delays.
- Supporting selected ready/stall scenarios.
- Enabling reproducible test conditions.

The memory model is part of the verification environment, not a replacement for a complete external AXI interconnect or physical memory controller.

## 5.4 Testbench

The cocotb testbench drives and observes the design through the simulator.

The testbench is responsible for arranging transaction scenarios, providing expected data, monitoring completion, checking error behavior, and reporting failures.

The surrounding Python tests also validate reusable verification components independently of the RTL regression.

# 6. AXI Interface Overview

The design and verification environment exercise the five standard AXI channel groups.

| Channel | Function | Verification focus |
|---|---|---|
| AR | Read address | Request issuance and selected stall scenarios |
| R | Read data and response | Returned data, response status, and response timing |
| AW | Write address | Destination request issuance and selected stalls |
| W | Write data | Payload transfer, byte strobes, and selected stalls |
| B | Write response | Response status and completion timing |

## 6.1 Handshake concept

AXI channels use `VALID` and `READY` to indicate when a transfer can take place.

A transfer occurs on a clock edge where both signals are asserted.

When a sender asserts `VALID` but the receiver does not assert `READY`, the sender generally must preserve the transaction information until the transfer can occur, according to the applicable channel protocol.

The verification platform includes protocol-monitor checks for `VALID` and payload stability on AR, R, AW, W, and B while stalled.

The presence of a protocol monitor does not automatically establish full compliance. The implemented checks cover specific invariants, and the complete supported protocol subset must be evaluated against the RTL and the monitor implementation.

## 6.2 Response handling

Read and write responses provide information about the result of AXI transactions.

The project tests selected read and write error responses and delayed response scenarios.

A critical distinction is that a response must be associated with the correct transaction. The reset-recovery diagnostics described later demonstrate that this association is not yet robust against every stale-response scenario.

# 7. RTL Design and Transfer Flow

A typical transfer scenario follows this conceptual sequence:

1. The testbench prepares source memory with known data.
2. A transfer descriptor specifies the source address, destination address, and length.
3. The DMA accepts or rejects the descriptor according to its validation behavior.
4. The DMA issues read requests for source data.
5. The memory model returns read data and response status.
6. The DMA processes the returned data.
7. The DMA issues write requests and transfers destination data.
8. The memory model records the resulting writes.
9. The DMA processes the write response.
10. The testbench checks destination memory and the observed completion or error result.

For queued transfers, the environment submits multiple descriptors and verifies execution order and queue-full behavior.

For error tests, the memory model returns the configured error response and the testbench checks that the observed result differs from a successful transfer.

For timing tests, selected requests or responses are delayed so that the design is exercised under non-zero-wait-state conditions.

This flow describes the intended verification model. Exact internal state transitions and cycle-level behavior are implementation-specific and should be confirmed from RTL and simulation waveforms.

# 8. Verification Architecture

The project uses several complementary verification methods.

## 8.1 Directed testing

Directed tests target specific conditions with controlled inputs.

Examples include:

- A basic memory copy.
- An invalid transfer descriptor.
- A read-response error.
- A write-response error.
- A maximum tested burst.
- A stalled address or data channel.
- A delayed response.
- A queue-full condition.
- Reset during selected transfer states.

Directed tests make failures easier to reproduce and interpret.

## 8.2 Reference-data checking

Tests initialize source memory with known data and compare the destination memory contents against expected values.

This detects incorrect data movement even when a transaction appears to complete successfully.

## 8.3 Randomized testing

Seeded randomized testing varies descriptor scenarios while retaining a reproducible random seed.

The recorded M16 evidence includes 20 randomized descriptors.

A fixed seed makes a particular run easier to reproduce, although passing one seed does not establish exhaustive coverage of the transaction space.

## 8.4 Timing and backpressure testing

Selected tests introduce stalls and delayed responses.

The purpose is to exercise behavior beyond ideal immediate handshakes and to check that transaction data and completion behavior remain consistent with the tested scenarios.

The project also contains an isolated response-channel backpressure harness. Its result must not be confused with proof that the production DMA RTL safely supports arbitrary multi-cycle response-channel stalls.

## 8.5 Protocol monitoring

The reusable protocol monitor checks selected AXI channel invariants, including `VALID` and payload stability while stalled.

The monitor is unit-tested separately from the main DMA regression.

## 8.6 Assertions

SystemVerilog simulation assertions are enabled in the recorded lint and simulation configuration. Additional RTL assertions and verification invariants were introduced during development.

Passing simulation assertions means the enabled properties did not report violations in the scenarios exercised. It does not mean all protocol properties have been proven.

## 8.7 Functional coverage

The functional coverage component records hits against a defined set of scenarios.

The recorded regression reached 14 of 14 defined functional scenarios.

This result describes the current scenario model. It is not equivalent to complete RTL code coverage or formal verification.

# 9. Technology Stack

| Technology | Role |
|---|---|
| SystemVerilog | RTL implementation and selected simulation assertions |
| Verilator 5.036 | RTL linting and simulation |
| cocotb 2.1.0 | Python-driven RTL verification |
| Python | Memory model, testbench logic, diagnostics, and coverage |
| pytest | Standalone unit testing |
| Make | Regression orchestration |
| Git | Source history and checkpoints |
| GitHub | Remote repository and documentation |
| GTKWave | Optional waveform inspection |

The recorded M16 readiness report used Python 3.14.0. Environment differences may affect reproduction, so tool versions should be checked when comparing results.

# 10. Development Roadmap: M1–M16

The milestones below describe the project’s development progression. A milestone may represent completed implementation work, verification infrastructure, an isolated experiment, or a documented diagnostic finding. Those categories are not interchangeable.

The completion claims below reflect the recorded project history and verification evidence. Where the evidence has a limited scope, that scope is stated explicitly.

---

## M1 — Basic DMA Transfer

**Status: Completed**

### Objective

Establish the initial memory-to-memory DMA data path and verify that a basic transfer can move data from a source address to a destination address.

### Work performed

- Implemented the initial DMA transfer behavior.
- Introduced source and destination address handling.
- Established basic transfer initiation and completion behavior.
- Added a basic data-integrity test.
- Connected the RTL to a simulation testbench.

### Verification

The recorded basic test transfers the value `0xDEADBEEF` from source address `0x00001000` to destination address `0x00002000`.

The test checks that the destination contains the expected data.

### Engineering significance

This milestone established the initial functional baseline. It demonstrated the basic transfer path but did not establish robust burst handling, error recovery, queueing, backpressure behavior, or comprehensive AXI compliance.

---

## M2 — Memory Model Integration

**Status: Completed**

### Objective

Introduce a reusable memory model so that the DMA can be tested against controlled memory contents and responses.

### Work performed

- Added Python-side memory-model functionality.
- Initialized source memory with known values.
- Modelled memory transactions used by the testbench.
- Checked destination memory after transfers.
- Began reusing memory behavior across multiple tests.

### Verification

The testbench uses the memory model to provide expected source data and check destination writes.

This approach separates data checking from the internal details of the DMA state machine.

### Engineering significance

The memory model became a foundation for subsequent burst, error, timing, and randomized tests. It also provided an independently testable component that could be strengthened as verification requirements grew.

---

## M3 — Transfer Validation and Error Handling

**Status: Completed**

### Objective

Verify that invalid transfer requests and selected AXI error responses do not behave like successful transfers.

### Work performed

- Added zero-length transfer rejection scenarios.
- Added unaligned source-address rejection scenarios.
- Added read-response error tests.
- Added write-response error tests.
- Checked the observed result of unsuccessful transactions.
- Separated successful transfer checks from error-path checks.

### Verification

The recorded regression includes tests for invalid descriptors and read/write response errors, including `SLVERR` scenarios.

### Engineering significance

Error-path testing matters because a design that handles only successful transactions can still lose data or report false completion when a request or response fails.

The tests establish behavior for the conditions they exercise. They do not establish complete coverage of every possible error code, timing combination, or protocol violation.

---

## M4 — Burst Transfer Verification

**Status: Completed**

### Objective

Extend transfer testing beyond single-word operations and verify multi-beat data movement.

### Work performed

- Added two-beat burst scenarios.
- Added four-beat burst scenarios.
- Added tests for bursts up to 16 beats.
- Checked data for individual transferred beats.
- Expanded data-integrity checking across a transfer rather than a single word.

### Verification

The recorded regression includes burst scenarios up to 16 beats.

### Engineering significance

Burst testing exercises transaction progression and data handling across multiple beats. It creates additional opportunities for sequencing, data-integrity, and completion errors that are not exposed by a single-beat test.

The maximum tested burst length is a verification result, not a claim that every possible burst size, boundary condition, or AXI burst rule has been verified.

---

## M5 — Request-Channel Backpressure

**Status: Completed for selected scenarios**

### Objective

Exercise request and write-data transfers when the receiving side does not immediately accept the transaction.

### Work performed

- Added read-address channel (`AR`) stall scenarios.
- Added write-address channel (`AW`) stall scenarios.
- Added write-data channel (`W`) stall scenarios.
- Added checks for transaction information remaining stable during tested stalls.
- Expanded the testbench beyond ideal immediate-handshake behavior.

### Verification

The recorded regression includes AR, AW, and W stall scenarios.

The reusable protocol monitor also checks selected `VALID` and payload stability invariants.

### Engineering significance

Backpressure testing helps detect bugs that appear when a transfer is delayed. The sender must preserve the relevant transaction information until the handshake occurs.

### Scope limitation

This milestone does not establish that the production DMA safely tolerates every possible response-channel stall. R- and B-channel backpressure require their own production-RTL verification evidence.

---

## M6 — Delayed Response Handling

**Status: Completed for recorded delay scenarios**

### Objective

Introduce non-zero response latency into the memory model and test selected transaction timing behavior.

### Work performed

- Added configurable read-response delay behavior.
- Added configurable write-response delay behavior.
- Exercised transactions with delayed responses.
- Checked data integrity after delayed transfers.
- Added checks related to completion waiting for the required response in the tested scenarios.

### Verification

The standard regression includes delayed read and write response scenarios.

### Engineering significance

Real systems do not guarantee that every response arrives immediately. Delayed responses expose state-management and completion-ordering issues that can remain hidden in a zero-wait-state testbench.

### Scope limitation

Passing these scenarios does not prove correct behavior for every delay length, every ordering of events, or responses that remain outstanding across reset.

---

## M7 — Descriptor Queue

**Status: Completed for recorded queue scenarios**

### Objective

Verify that multiple transfer descriptors can be submitted and processed according to the tested queue behavior.

### Work performed

- Added multi-descriptor test scenarios.
- Exercised FIFO-order execution.
- Added queue-full rejection testing.
- Checked for descriptor loss or reordering in the tested sequences.
- Extended verification beyond one isolated transfer.

### Verification

The recorded regression includes descriptor queue FIFO behavior and full-queue rejection scenarios.

The recorded tested configuration uses a descriptor queue depth of four.

### Engineering significance

Queueing introduces interactions between request acceptance, execution, and completion. Testing multiple descriptors helps reveal errors that are invisible when the DMA processes only one transfer at a time.

### Scope limitation

The recorded tests do not establish correctness for every possible queue occupancy transition, simultaneous queue operation, or reset interaction.

---

## M8 — Seeded Randomized Descriptor Testing

**Status: Completed for the recorded randomized run**

### Objective

Broaden the tested transaction space through repeatable randomized descriptors.

### Work performed

- Introduced seeded randomized descriptor generation.
- Exercised multiple descriptor scenarios.
- Checked transferred data against expected contents.
- Preserved the random seed for reproducibility.
- Added randomized traffic to the verification progression.

### Verification

The recorded M16 report documents 20 randomized descriptors with seed `23063`.

### Engineering significance

Randomized tests can explore combinations that were not individually anticipated when writing directed tests. Preserving the seed makes a specific run easier to reproduce during debugging.

### Scope limitation

Twenty randomized descriptors are a limited sample. Passing the recorded run does not prove exhaustive correctness or eliminate the need for directed corner-case testing.

---

## M9 — Reset-Recovery Testing

**Status: Basic reset scenarios completed; external stale-response recovery remains unresolved**

### Objective

Exercise reset during selected transfer and queue conditions, then check the behavior of subsequent transfers.

### Work performed

- Tested reset during a delayed read scenario.
- Tested reset during a write-burst scenario.
- Tested reset with queued descriptors.
- Checked selected fresh-transfer behavior after reset.
- Added reset scenarios to the standard regression.

### Verification

The recorded standard regression includes reset-related tests.

However, the ordinary reset tests clear pending responses in the memory model. They do not establish that the DMA is immune to stale responses from an external slave that continues operating across a DMA-only reset.

### Engineering significance

Reset is a transaction-lifecycle problem, not simply a matter of returning internal state to an initial value. External transactions may still be outstanding after the DMA itself is reset.

### Remaining issue

Later diagnostics reproduced stale R- and B-response misattribution after DMA-only reset. These findings remain open and are documented under M15 and in `docs/m16_release_readiness.md`.

---

## M10 — Memory Model Unit Tests

**Status: Completed; 16 recorded tests passed**

### Objective

Test the reusable Python memory model independently of the full RTL regression.

### Work performed

- Added standalone memory-model unit tests.
- Tested configuration validation.
- Tested deterministic randomized-ready behavior.
- Tested byte-strobe updates.
- Tested write-response delay configuration.
- Tested seeded-delay reproducibility.

### Verification

Recorded result:

- `test_axi_memory_model_unit.py`: 16 passed.

### Engineering significance

Independent unit tests make it easier to distinguish a memory-model defect from an RTL defect. They also improve confidence that reusable testbench behavior is deterministic under the tested configurations.

---

## M11 — Write-Response Timing Verification

**Status: Completed; recorded standard regression passed**

### Objective

Strengthen write-response timing checks and improve reusable memory-model helpers.

### Work performed

- Extracted byte-strobe handling into a helper.
- Added write-response delay scheduling.
- Tested fixed-delay and seeded-random delay behavior.
- Measured timing between the final write-data beat and `BVALID`.
- Preserved compatibility with the existing regression.

### Verification

The recorded standard regression passed all 18 tests.

### Engineering significance

Write completion depends on more than the final payload beat. The response timing checks provide additional evidence about the relationship between data transfer and write-response behavior.

The measured timing applies to the recorded test configurations; it should not be generalized into a universal performance or compliance claim.

---

## M12 — AXI Response-Channel Backpressure

**Status: Isolated harness tested; production-RTL coverage remains incomplete**

### Objective

Investigate response-channel behavior when the receiver does not immediately accept returned data or a write response.

### Work performed

- Developed an isolated AXI response-channel backpressure harness.
- Added a standalone test for the harness.
- Exercised selected response-stall behavior outside the main production DMA regression.
- Preserved the distinction between harness validation and production RTL validation.

### Verification

The recorded readiness report documents the isolated harness passing one standalone test.

### Engineering significance

The R and B channels are important to transaction lifecycle and completion. A receiver may need to hold off acceptance of a response, and the interaction between response validity, readiness, and internal state must be handled correctly.

### Remaining work

- Integrate appropriate response-channel stall scenarios into the production DMA regression.
- Verify the production RTL's behavior when R-channel and B-channel handshakes are delayed.
- Check response stability and correct completion timing.
- Exercise multiple stall lengths and relevant transaction states.
- Document the legal behavior and integration assumptions.

The isolated harness passing does not prove that the production RTL safely supports every multi-cycle response-channel stall.

---

## M13 — Protocol Assertions and Monitoring

**Status: Assertions and monitor implemented; recorded monitor unit tests passed**

### Objective

Improve observability of protocol invariants and identify transaction behavior that violates selected checks.

### Work performed

- Added RTL assertions for selected DMA invariants.
- Strengthened protocol-monitor reset checks.
- Developed reusable AXI protocol-monitor behavior.
- Checked `VALID` and payload stability while AR, R, AW, W, or B is stalled.
- Added independent unit tests for the protocol monitor.
- Enabled simulation assertions in the recorded Verilator configuration.

### Verification

The recorded standalone unit-test results include:

- `test_axi_protocol_monitor_unit.py`: 25 passed.
- Combined memory-model and protocol-monitor unit tests: 41 passed.

### Engineering significance

Assertions and monitors make verification failures easier to detect and diagnose. They can reveal violations even when the final destination data happens to be correct.

### Scope limitation

The checks cover selected invariants. Passing them does not establish complete AXI protocol compliance, and simulation assertion results are not a formal proof.

---

## M14 — Corner Cases, Fault Diagnostics, and Reset Investigation

**Status: Investigation and diagnostic infrastructure recorded; reset findings remain open**

### Objective

Investigate corner cases that are not adequately covered by ordinary successful-transfer tests, particularly transaction behavior across reset.

### Work performed

- Added targeted diagnostics for stale read responses after reset.
- Added targeted diagnostics for stale write responses after reset.
- Preserved the failing behavioral observations.
- Distinguished reproducing a known failure from fixing it.
- Documented the limitations of the ordinary reset tests.
- Identified the need for an explicit system-level reset and outstanding-transaction contract.

### Verification

The recorded diagnostic results are:

- Stale read-response diagnostic: one test passed by reproducing the targeted issue.
- Stale write-response diagnostic: one test passed by reproducing the targeted issue.

These are diagnostic passes, not evidence that the design is correct in the affected scenarios.

### Engineering significance

A useful verification environment must be capable of exposing failures instead of only reporting successful transfers. A reproducible diagnostic provides concrete evidence of a design limitation and a starting point for regression testing after a fix.

### Remaining work

- Define how outstanding AXI transactions are handled during reset.
- Implement an appropriate recovery strategy.
- Retain or recreate external outstanding responses in the testbench.
- Verify that stale responses cannot be attributed to a fresh transaction.
- Re-run both diagnostics after the RTL change.

---

## M15 — Reset-Recovery Diagnostics and Release-Risk Documentation

**Status: Findings reproduced and documented; not fixed**

### Objective

Characterize the stale-response behavior more precisely and record its impact on readiness.

### Finding 1: Stale read response after DMA-only reset

The diagnostic observed destination data `0xDEADCAFE` when the fresh transfer was expected to deliver `0x12345678`.

The test reproduced a case in which a stale read response was consumed as data for a fresh transfer after DMA reset.

**Result:** The issue remains unresolved.

### Finding 2: Stale write response after DMA-only reset

The diagnostic reproduced a case in which a stale successful B response was accepted as completion of a fresh transaction before the fresh transaction's own response was generated.

**Result:** The issue remains unresolved.

### Why these findings matter

If the DMA is reset while an external AXI slave or interconnect retains an outstanding transaction, a response from the earlier transaction may arrive after the DMA starts a new transaction.

Without a suitable transaction-lifecycle strategy, the DMA may associate the old response with the new operation. That can corrupt transferred data or cause premature completion.

The ordinary reset tests do not prove immunity to this condition because they clear pending memory-model responses.

### Potential system-level strategies

Depending on the integration contract, possible approaches include:

- Coordinated reset of the DMA and relevant transaction endpoints.
- Quiescing new traffic and waiting for outstanding transactions to drain before reset.
- An explicit transaction-draining protocol.
- A suitable transaction-epoch mechanism, where compatible with the interface and system architecture.

These are possible design directions, not implemented or validated fixes in the current checkpoint.

### Engineering significance

This milestone makes the project's readiness assessment evidence-driven. The stale-response findings are explicit engineering risks and must remain visible until a corrective implementation is tested.

---

## M16 — Final Verification and Release Readiness

**Status: Verification checkpoint recorded; production sign-off not achieved**

### Objective

Consolidate the available verification evidence, document known limitations, and establish the work required before the project can claim stronger readiness.

### Work performed

- Recorded the standard cocotb regression results.
- Recorded standalone Python unit-test results.
- Recorded the functional scenario coverage result.
- Documented lint configuration and results.
- Recorded the isolated response-backpressure harness result.
- Documented the stale read-response finding.
- Documented the stale write-response finding.
- Identified the limits of the ordinary reset tests.
- Published the M16 release-readiness report.
- Recorded remaining work and integration assumptions.

### Standard regression result

| Metric | Result |
|---|---:|
| Tests | 18 |
| Passed | 18 |
| Failed | 0 |
| Skipped | 0 |
| Simulation duration | 12,766.03 ns |

### Standalone unit-test result

| Suite | Result |
|---|---:|
| Memory-model unit tests | 16 passed |
| Protocol-monitor unit tests | 25 passed |
| Total | 41 passed |

### Functional scenario result

The standard regression reported 14 of 14 defined functional scenarios hit.

This is 100% of the currently defined scenario set. It is not 100% RTL code coverage, exhaustive verification, or formal proof.

### Lint result

The recorded Verilator lint run completed without reported warnings or errors using the project's recorded lint command.

### Readiness assessment

The project has a documented simulation and verification checkpoint. However, the stale R and B response diagnostics demonstrate unresolved reset-recovery risks.

**M16 does not mean every engineering milestone has achieved production-level closure.** It means the current evidence and outstanding limitations have been consolidated and recorded.

The detailed evidence is available in:

`docs/m16_release_readiness.md`

### Exit criteria for stronger release readiness

Before claiming robust reset recovery or production readiness, the project needs to:

1. Define the reset and outstanding-transaction integration contract.
2. Implement a recovery strategy that prevents stale responses from being misattributed.
3. Add or update tests that retain external responses across a DMA-only reset.
4. Demonstrate corrected behavior in both stale-response diagnostics.
5. Integrate response-channel backpressure tests for the production RTL.
6. Re-run the standard regression and standalone unit tests.
7. Re-run lint and review any warnings.
8. Record the updated evidence and remaining limitations.
9. Establish acceptance criteria appropriate to the intended integration.
10. Make a release decision only after the required evidence is available.

---

# 11. Current Verification Results

The following table consolidates the recorded evidence from the M16 readiness checkpoint.

| Verification area | Recorded result | Interpretation |
|---|---|---|
| Basic transfers | Included in standard regression | Basic data movement tested |
| Memory-model integration | Included in standard regression | Data movement checked against model contents |
| Invalid descriptors | Included in standard regression | Selected invalid requests tested |
| Read/write error responses | Included in standard regression | Selected AXI error cases tested |
| Burst transfers | Up to 16 beats | Tested burst length, not exhaustive burst compliance |
| AR/AW/W stalls | Included in regression | Selected request/data backpressure tested |
| Delayed responses | Included in regression | Selected response-delay scenarios tested |
| Descriptor FIFO behavior | Included in regression | Selected queue ordering tested |
| Queue-full rejection | Included in regression | Full-queue condition tested |
| Randomized descriptors | 20 recorded descriptors | Seeded sample, not exhaustive testing |
| Basic reset scenarios | Included in regression | Selected reset scenarios tested |
| Memory-model unit tests | 16 passed | Python component tests passed |
| Protocol-monitor unit tests | 25 passed | Monitor component tests passed |
| Combined unit tests | 41 passed | All recorded unit tests passed |
| Functional scenarios | 14/14 hit | All defined scenarios hit |
| Isolated response harness | 1/1 passed | Harness tested separately from production RTL |
| Stale read response after reset | Failure reproduced | Unresolved design limitation |
| Stale write response after reset | Failure reproduced | Unresolved design limitation |
| Production sign-off | Not achieved | Outstanding limitations remain |

These results should be treated as recorded evidence for the stated environment and test configurations. Re-run the relevant checks after code or environment changes.

# 12. Testbench and Verification Components

The main verification environment is organized around reusable components and scenario-specific tests.

## 12.1 AXI memory model

The memory model provides data and response behavior for the RTL testbench.

The unit tests cover recorded behaviors including configuration validation, byte-strobe updates, ready behavior, response-delay configuration, and seeded delay reproducibility.

## 12.2 AXI protocol monitor

The protocol monitor provides reusable checks for selected AXI channel invariants.

The recorded unit tests exercise the monitor independently, helping separate monitor behavior from DMA behavior.

## 12.3 Functional coverage

The functional coverage component tracks explicitly defined scenarios and reports which ones were hit.

The recorded standard regression reached all 14 defined scenarios.

## 12.4 Directed and randomized tests

Directed tests provide controlled scenarios for specific behaviors. Randomized tests broaden the set of transactions while preserving a seed for reproducibility.

## 12.5 Reset diagnostics

The reset diagnostics deliberately reproduce stale-response issues. Their successful execution indicates that the failure condition was observed, not that the RTL has passed the affected behavior.

# 13. Reset-Recovery Investigation

Reset recovery is the most important unresolved correctness issue recorded in this checkpoint.

## 13.1 The underlying transaction-lifecycle problem

Consider the following conceptual sequence:

1. The DMA issues an AXI read.
2. The external slave or interconnect retains a response that has not yet been consumed.
3. The DMA alone is reset.
4. The DMA starts a new transfer after reset.
5. The earlier response arrives.
6. The DMA incorrectly associates the earlier response with the new transaction.

The stale write-response case is similar: an old B response may be accepted as completion of a new write.

The issue is not necessarily solved by resetting the DMA's internal state. The external transaction endpoint may continue operating and may still deliver responses for previously accepted requests.

## 13.2 Integration contract

The design needs an explicit answer to the following questions:

- Can the DMA reset independently of the AXI slave or interconnect?
- Are outstanding transactions guaranteed to be drained before reset completes?
- Is the external endpoint also reset?
- Can responses from before reset still arrive afterward?
- How is a fresh transaction distinguished from an old outstanding transaction?
- What behavior is required if a response arrives after the DMA has abandoned the original operation?

The answers determine the appropriate recovery strategy.

## 13.3 Required corrective verification

A future fix should be validated by retaining outstanding external responses across a DMA-only reset and checking that the DMA does not:

- Use stale read data for a new transfer.
- Treat a stale write response as new transaction completion.
- Report success before the new transaction's own response has been handled.
- Corrupt destination data.
- Lose synchronization with subsequent transactions.

Both previously failing diagnostics should become regression tests that pass only when the corrected behavior is observed.

# 14. Repository Structure

The following is a high-level guide to the principal project files. The exact file inventory may evolve, so consult the repository for the current layout.

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
│       ├── test_axi_memory_model_unit.py
│       └── test_axi_protocol_monitor_unit.py
├── docs/
│   └── m16_release_readiness.md
├── Makefile
├── .gitignore
└── README.md
```

Some diagnostic tests, backup files, and local simulation artifacts may exist outside this summarized tree. The diagram is a guide, not an exhaustive file listing.

## Main components

| Path | Purpose |
|---|---|
| `rtl/axi_dma.sv` | DMA RTL implementation |
| `tb/axi_memory_model.py` | Python memory and response model |
| `tb/axi_protocol_monitor.py` | Reusable protocol-monitor checks |
| `tb/functional_coverage.py` | Functional scenario tracking |
| `tb/tests/` | Directed, randomized, diagnostic, and unit tests |
| `docs/m16_release_readiness.md` | Recorded verification evidence and unresolved findings |
| `Makefile` | Simulation and regression entry point |
| `.gitignore` | Excludes Python artifacts and named simulation build products |
| `README.md` | Project overview, milestone history, and verification status |

# 15. Installation and Setup

The following commands reflect the recorded local environment. Paths may need adjustment on another machine.

## 15.1 Enter the project directory

```bash
cd ~/axi_dma
```

## 15.2 Activate the Python environment

```bash
source ~/cocotb-env/bin/activate
```

## 15.3 Configure the recorded Verilator installation

```bash
export PATH="$HOME/opt/verilator-5.036/bin:$PATH"
```

## 15.4 Check the available tools

```bash
python --version
verilator --version
```

The recorded M16 environment used Python 3.14.0 and Verilator 5.036. Check the installed cocotb version using:

```bash
python -m pip show cocotb
```

The recorded project environment used cocotb 2.1.0.

The commands above inspect the active environment; they do not install or change any packages.

# 16. Running the Regression

Run the standard cocotb regression from the repository root.

```bash
cd ~/axi_dma
source ~/cocotb-env/bin/activate
export PATH="$HOME/opt/verilator-5.036/bin:$PATH"

PYTHONPATH="$PWD/tb/tests:$PWD/tb${PYTHONPATH:+:$PYTHONPATH}" \
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 make
```

The recorded regression passed 18 tests with no failures or skips.

When rerunning the suite:

- Inspect the final test summary.
- Read the full traceback for any failure.
- Preserve the random seed for reproducibility.
- Inspect generated waveforms when timing or state sequencing is unclear.
- Distinguish ordinary regression tests from diagnostic tests designed to reproduce known failures.

A previous successful run does not guarantee a future run will pass after code or environment changes.

# 17. Running Unit Tests

The standalone unit tests validate the reusable Python memory model and protocol monitor.

Run both suites:

```bash
cd ~/axi_dma
source ~/cocotb-env/bin/activate

PYTHONPATH="$PWD/tb:$PWD/tb/tests${PYTHONPATH:+:$PYTHONPATH}" \
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
python -m pytest -v \
  tb/tests/test_axi_memory_model_unit.py \
  tb/tests/test_axi_protocol_monitor_unit.py
```

Recorded results:

- Memory-model unit tests: 16 passed.
- Protocol-monitor unit tests: 25 passed.
- Combined total: 41 passed.

These unit tests do not replace the full RTL regression. They provide independent evidence about the Python components.

# 18. Linting the RTL

The recorded lint command is:

```bash
cd ~/axi_dma

verilator --lint-only --assert -Wall -Wno-fatal \
  --top-module axi_dma rtl/axi_dma.sv
```

The recorded run completed without reported warnings or errors.

The `--assert` option enables assertion support for the applicable Verilator flow. The `-Wall` option enables broad warning reporting, while `-Wno-fatal` prevents warnings from automatically being treated as fatal.

Because `-Wno-fatal` is present, inspect the actual diagnostics rather than treating the process exit status alone as proof that the RTL is warning-free.

Linting does not establish functional correctness, complete protocol compliance, timing closure, or successful FPGA implementation.

# 19. Debugging and Waveform Analysis

When a test fails, the objective is to identify the earliest point where observed behavior diverges from expected behavior.

A useful debugging sequence is:

1. Identify the exact test that failed.
2. Record the test's random seed, if applicable.
3. Read the first relevant assertion or data mismatch.
4. Determine which transaction was active at the failure.
5. Inspect AR and AW request timing.
6. Inspect R and W payloads and handshake timing.
7. Inspect B response timing and completion behavior.
8. Check reset timing and the state of outstanding transactions.
9. Inspect the memory model's pending requests and responses.
10. Reproduce the issue with the smallest useful test case.

GTKWave can be used to inspect generated waveform files when the simulator configuration produces them.

The `.gitignore` file excludes common waveform and simulation build artifacts. Local generated output should generally remain separate from the committed source and documentation.

# 20. Functional Coverage

Functional coverage records whether defined verification scenarios have been exercised.

The recorded regression reached:

**14 of 14 defined functional scenarios.**

The defined scenario groups include:

- Transfer-length scenarios.
- Invalid-request scenarios.
- Read-response error handling.
- Write-response error handling.
- Address-channel backpressure.
- Write-data backpressure.
- Descriptor FIFO ordering.
- Queue-full rejection.
- Seeded randomized stress.

This result indicates that all scenarios currently represented in the functional coverage model were hit during the recorded run.

It does not mean:

- 100% statement coverage.
- 100% branch coverage.
- 100% toggle coverage.
- 100% condition coverage.
- Exhaustive verification of all transaction sequences.
- Formal proof of correctness.
- Complete AXI4 compliance.

Coverage quality depends on how well the scenario model represents the requirements. Future work should expand the coverage model alongside the implementation and the verification plan.

# 21. Known Limitations

The following limitations remain relevant to the recorded checkpoint.

## 21.1 Stale AXI responses after DMA-only reset

Outstanding R and B responses can be misattributed to a post-reset transaction. The stale-response diagnostics reproduced both read and write cases.

This is an unresolved correctness issue.

## 21.2 Reset integration assumptions

The system needs a defined policy for outstanding transactions when the DMA is reset independently of its external transaction endpoints.

A recovery strategy must be designed and verified against that policy.

## 21.3 Incomplete AXI compliance evidence

The testbench exercises selected AXI channel and transaction scenarios. It does not establish complete AXI4 compliance.

## 21.4 Limited functional coverage scope

The 14/14 result applies to the currently defined functional scenarios. It is not equivalent to complete RTL code coverage.

## 21.5 No formal proof

The regression, simulation assertions, and protocol-monitor checks are not a formal proof of correctness.

## 21.6 Response-channel backpressure

The isolated response-backpressure harness is not proof that the production DMA safely handles every response-channel stall scenario.

## 21.7 No FPGA sign-off

The recorded verification results do not establish FPGA synthesis success, timing closure, resource utilization, or hardware validation.

## 21.8 Performance characterization

The project should not make throughput or latency claims without documented measurement methodology and actual measurements. The recorded simulation duration is not a standalone measure of DMA throughput.

# 22. Remaining Engineering Work

The next development phase should prioritize correctness and evidence.

## Priority 1: Define reset semantics

Document the system contract for reset, outstanding transactions, external response behavior, and recovery.

## Priority 2: Correct stale-response handling

Choose and implement a strategy appropriate to the system integration. Possible approaches include coordinated reset, quiescence, draining outstanding transactions, or a suitable transaction-epoch mechanism.

These are candidate strategies, not a claim that any has already been implemented successfully.

## Priority 3: Turn diagnostics into regression protection

Retain the stale-R and stale-B cases as tests that verify corrected behavior after the RTL fix.

The tests should preserve the external pending response across the DMA-only reset where required to reproduce the original condition.

## Priority 4: Verify production response backpressure

Integrate R- and B-channel stall scenarios into the production DMA regression. Check handshake stability, data integrity, and completion timing.

## Priority 5: Expand corner-case testing

Add scenarios based on the documented interface requirements, including relevant combinations of stalls, delayed responses, queue activity, error conditions, and reset timing.

## Priority 6: Improve coverage

Review the current functional coverage definitions, identify missing requirement-driven scenarios, and add bins that provide useful verification evidence.

## Priority 7: Re-run all checks

After RTL or testbench changes:

- Run lint.
- Run the standard cocotb regression.
- Run the standalone unit tests.
- Run the reset diagnostics.
- Inspect assertion output.
- Preserve random seeds and failure logs.
- Update the release-readiness report.

## Priority 8: Assess release readiness

Only make stronger readiness claims after the documented correctness issues have been addressed and retested, and after the required integration and verification acceptance criteria have been met.

# 23. Reproducibility and Engineering Practices

Reproducibility is a core part of this project.

## Randomized tests

Record seeds and preserve failing seeds so that a failure can be investigated with the same generated transaction sequence.

## Test evidence

Record the exact test command, tool versions, test summary, and any known limitations associated with a result.

## Failure diagnosis

A test designed to reproduce a known bug must be labelled as a diagnostic. Its passing status should never be confused with a successful correctness check.

## Source control

Use Git commits to preserve implementation and verification checkpoints. Keep generated simulation output separate from source deliverables, and preserve local backups until they are no longer needed.

## Documentation

Update the README and readiness report when the actual implementation, supported behavior, or recorded verification evidence changes.

## Release claims

State exactly what was tested and what remains unverified. A strong engineering report is more useful when its limitations are explicit.

# 24. Technical References

The following official resources provide background and technical documentation relevant to the project.

- Arm AMBA specifications: https://developer.arm.com/Architectures/AMBA
- IEEE Standards: https://standards.ieee.org/
- Verilator documentation: https://verilator.org/guide/latest/
- cocotb documentation: https://docs.cocotb.org/
- GTKWave documentation: https://gtkwave.github.io/gtkwave/
- Accellera: https://www.accellera.org/
- Yosys documentation: https://yosyshq.readthedocs.io/
- SymbiYosys documentation: https://symbiyosys.readthedocs.io/
- AMD Vivado documentation: https://docs.amd.com/

The applicable AXI specification revision and the exact protocol subset supported by the RTL should be documented as the design evolves.

# 25. Final Project Assessment

The AXI DMA Engine and Verification Platform has progressed from a basic memory-to-memory transfer to a more structured RTL verification project.

The recorded work includes descriptor and queue scenarios, burst testing, selected AXI errors, request-channel stalls, delayed responses, seeded randomized descriptors, reusable Python unit tests, protocol monitoring, assertions, functional scenario coverage, and reset-recovery diagnostics.

The recorded M16 checkpoint includes:

- 18 of 18 standard regression tests passed.
- 41 of 41 standalone unit tests passed.
- 14 of 14 defined functional scenarios hit.
- A lint run completed without reported warnings or errors.
- Two stale-response reset-recovery limitations reproduced and documented.

The most important outstanding issue is the handling of AXI responses that remain outstanding across a DMA-only reset. Until the system reset contract and recovery behavior are implemented and verified, the design should not be described as having robust reset recovery or production readiness.

The objective is to develop a reusable DMA implementation whose supported behavior is explicit, whose failure modes are reproducible, whose verification evidence is reviewable, and whose readiness claims are supported by actual results.

**Current checkpoint:** M16 verification and release-readiness assessment recorded.

**Next engineering priority:** Resolve stale-response handling across reset and verify production-RTL response-channel backpressure behavior.

**Release status:** Not production sign-off.
