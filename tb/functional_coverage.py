"""Functional coverage tracker for the AXI DMA regression."""

import json
from pathlib import Path

COVERAGE_POINTS = (
    "transfer.single_beat",
    "transfer.short_burst_2_to_4",
    "transfer.long_burst_5_to_15",
    "transfer.maximum_16_beat_burst",
    "error.zero_length",
    "error.unaligned_source",
    "error.axi_read_slverr",
    "error.axi_write_slverr",
    "backpressure.ar",
    "backpressure.aw",
    "backpressure.w",
    "queue.fifo_order",
    "queue.full_rejection",
    "randomized.seeded_stress",
)

_hits = {point: 0 for point in COVERAGE_POINTS}


def hit(point):
    if point not in _hits:
        raise ValueError(f"Unknown coverage point: {point}")
    _hits[point] += 1


def hit_transfer_length(beats):
    if beats == 1:
        hit("transfer.single_beat")
    elif 2 <= beats <= 4:
        hit("transfer.short_burst_2_to_4")
    elif 5 <= beats <= 15:
        hit("transfer.long_burst_5_to_15")
    elif beats == 16:
        hit("transfer.maximum_16_beat_burst")
    else:
        raise ValueError(f"Unsupported transfer length: {beats}")


def write_report(path="functional_coverage.json"):
    covered = [p for p, count in _hits.items() if count > 0]
    uncovered = [p for p, count in _hits.items() if count == 0]
    total = len(COVERAGE_POINTS)
    percentage = 100.0 * len(covered) / total if total else 100.0

    report = {
        "coverage_type": "functional scenario coverage",
        "covered_points": len(covered),
        "total_points": total,
        "coverage_percent": round(percentage, 2),
        "hits": dict(_hits),
        "uncovered_points": uncovered,
    }

    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")

    print("\n=== AXI DMA Functional Coverage ===")
    print(f"Covered: {len(covered)}/{total} ({percentage:.2f}%)")
    for point, count in _hits.items():
        print(f"[{'HIT' if count else 'MISS'}] {point}: {count}")
    print(f"JSON report: {output.resolve()}")
    return report
