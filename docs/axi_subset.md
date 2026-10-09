# AXI DMA Engine — Initial Protocol Contract

## 1. Project objective

Implement reusable SystemVerilog DMA RTL and an automated
verification environment using Cocotb and Verilator.

The engine will copy data between memory locations through
AXI4 read and write channels.

## 2. Initial implementation scope

- Protocol: AXI4 memory-mapped master
- Address width: 32 bits
- Data width: 32 bits
- Transfer unit: 4 bytes per beat
- Burst type: INCR
- Maximum burst length: 16 beats
- Initial addresses: 4-byte aligned
- Initial transfer lengths: non-zero multiples of 4 bytes
- AXI IDs: fixed to zero
- Outstanding transactions: at most one read burst and
  one write burst at a time
- Burst splitting: do not cross a 4 KiB boundary
- Reset: active-low synchronous reset in the initial prototype

These are implementation constraints, not a claim of complete
AXI4 compliance.

## 3. AXI channels

### Read address (AR)
ARADDR, ARLEN, ARSIZE, ARBURST, ARVALID, ARREADY

### Read data (R)
RDATA, RRESP, RLAST, RVALID, RREADY

### Write address (AW)
AWADDR, AWLEN, AWSIZE, AWBURST, AWVALID, AWREADY

### Write data (W)
WDATA, WSTRB, WLAST, WVALID, WREADY

### Write response (B)
BRESP, BVALID, BREADY

The RTL must hold channel payload and VALID stable while
VALID is asserted and READY is low.

## 4. Initial control interface

The first prototype will use a simple control interface:

- start: request a transfer
- src_addr: source byte address
- dst_addr: destination byte address
- length_bytes: transfer length in bytes
- busy: transfer in progress
- done: successful completion indication
- error: transfer failed indication

The control interface may evolve as descriptor support is added.

## 5. Error handling

The engine must detect AXI read and write error responses.
Invalid initial transfer parameters must be rejected.
Completion and error signaling must be deterministic.

Detailed recovery behavior will be specified and tested in
later milestones.

## 6. Verification requirements

- Cocotb-based tests and a software memory model
- Destination-memory comparison against expected data
- Directed tests before randomized tests
- Backpressure on every AXI channel
- Reset injection and error-response tests
- Protocol assertions and functional coverage
- Reproducible logs, waveforms, and test summaries

## 7. Compliance statement

The project implements a documented AXI4 subset.
Protocol compliance claims must be supported by applicable
specification checks and verification evidence.
