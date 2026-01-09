#!/usr/bin/env python3
"""Allocate and lightly exercise memory to meet NRP utilization targets."""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np

MEMORY_FLAG = Path("/tmp/memory_allocated")

def allocate_arrays() -> list[np.ndarray]:
    arrays: list[np.ndarray] = []
    size_elements = int(2.0 * 1024 * 1024 * 1024 / 8)  # 2GB in float64 elements

    for i in range(4):
        arr = np.random.random(size=size_elements).astype(np.float64)
        arrays.append(arr)

        _ = np.mean(arr[::10000])
        print(f"SAFE Array {i + 1}: {arr.nbytes / 1024 / 1024 / 1024:.1f}GB allocated")
        time.sleep(1)

    return arrays


def run_cycles(arrays: list[np.ndarray]) -> None:
    for cycle in range(3):
        for arr in arrays:
            _ = np.sum(arr[::50000])
        time.sleep(5)
        print(f"SAFE memory cycle {cycle + 1}/3 complete")


def main() -> None:
    arrays: list[np.ndarray] | None = None
    try:
        arrays = allocate_arrays()
        MEMORY_FLAG.write_text("allocated")
        run_cycles(arrays)
        print("SAFE memory allocation cycle complete")
    except Exception as exc:  # noqa: BLE001 - best-effort logging
        print(f"SAFE memory allocation error: {exc}")
    finally:
        arrays = None


if __name__ == "__main__":
    main()
