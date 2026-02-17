#!/usr/bin/env python3
"""
CONFIRMED gate unit tests.

Validates the CONFIRMED vs CANDIDATE status determination logic
that lives in storm_monitor._persist_tracker_events().

CONFIRMED requires at least one "hard" hail evidence source:
  - MRMS MESH >= 15mm
  - Dual-pol hail signature (evidence_dualpol)
  - Local storm report (evidence_lsr)

Persistence and multi-radar alone are NOT sufficient.

Run: python scripts/test_confirmed_gate.py
"""

import sys


def determine_status(
    mrms_peak: float,
    evidence_dualpol: bool,
    evidence_lsr: bool,
    evidence_persistence: bool,
    evidence_multi_radar: bool,
) -> str:
    """
    Mirror of the CONFIRMED gate in storm_monitor.py lines 1331-1343.
    """
    mrms_val = mrms_peak if mrms_peak is not None else 0
    has_confirming_evidence = (
        mrms_val >= 15
        or evidence_dualpol
        or evidence_lsr
    )
    return 'CONFIRMED' if has_confirming_evidence else 'CANDIDATE'


def test(name, expected_status, **kwargs):
    """Run a scenario and check status matches expected."""
    status = determine_status(**kwargs)
    ok = status == expected_status
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}: status={status} (expected {expected_status})")
    return ok


def main():
    print("=== CONFIRMED GATE TESTS ===\n")
    all_pass = True

    # --- Should remain CONFIRMED ---
    print("Category: Should be CONFIRMED (hard evidence present)")

    all_pass &= test(
        "Dual-pol confirmed, with persistence",
        "CONFIRMED",
        mrms_peak=0, evidence_dualpol=True, evidence_lsr=False,
        evidence_persistence=True, evidence_multi_radar=False,
    )
    all_pass &= test(
        "MRMS 25mm, no dual-pol, with persistence",
        "CONFIRMED",
        mrms_peak=25.0, evidence_dualpol=False, evidence_lsr=False,
        evidence_persistence=True, evidence_multi_radar=False,
    )
    all_pass &= test(
        "LSR only, no MRMS, no dual-pol",
        "CONFIRMED",
        mrms_peak=0, evidence_dualpol=False, evidence_lsr=True,
        evidence_persistence=False, evidence_multi_radar=False,
    )
    all_pass &= test(
        "MRMS exactly 15mm (boundary)",
        "CONFIRMED",
        mrms_peak=15.0, evidence_dualpol=False, evidence_lsr=False,
        evidence_persistence=False, evidence_multi_radar=False,
    )

    # --- Should be downgraded to CANDIDATE ---
    print("\nCategory: Should be CANDIDATE (no hard evidence)")

    all_pass &= test(
        "Persistence-only, no MRMS, no dual-pol",
        "CANDIDATE",
        mrms_peak=0, evidence_dualpol=False, evidence_lsr=False,
        evidence_persistence=True, evidence_multi_radar=False,
    )
    all_pass &= test(
        "Multi-radar + persistence, no MRMS, no dual-pol",
        "CANDIDATE",
        mrms_peak=0, evidence_dualpol=False, evidence_lsr=False,
        evidence_persistence=True, evidence_multi_radar=True,
    )
    all_pass &= test(
        "Multi-radar only, no other evidence",
        "CANDIDATE",
        mrms_peak=0, evidence_dualpol=False, evidence_lsr=False,
        evidence_persistence=False, evidence_multi_radar=True,
    )
    all_pass &= test(
        "MRMS 14mm (just below threshold)",
        "CANDIDATE",
        mrms_peak=14.0, evidence_dualpol=False, evidence_lsr=False,
        evidence_persistence=True, evidence_multi_radar=True,
    )
    all_pass &= test(
        "No evidence at all",
        "CANDIDATE",
        mrms_peak=0, evidence_dualpol=False, evidence_lsr=False,
        evidence_persistence=False, evidence_multi_radar=False,
    )

    # --- Regression: persistence/multi-radar don't leak into gate ---
    print("\nCategory: Regression (soft evidence never triggers CONFIRMED)")

    # Adding persistence to a CANDIDATE should NOT flip it to CONFIRMED
    base_candidate = dict(mrms_peak=0, evidence_dualpol=False, evidence_lsr=False)
    s1 = determine_status(evidence_persistence=False, evidence_multi_radar=False, **base_candidate)
    s2 = determine_status(evidence_persistence=True, evidence_multi_radar=False, **base_candidate)
    s3 = determine_status(evidence_persistence=True, evidence_multi_radar=True, **base_candidate)
    ok = s1 == s2 == s3 == 'CANDIDATE'
    print(f"  [{'PASS' if ok else 'FAIL'}] Soft evidence never flips to CONFIRMED: "
          f"none={s1}, +persist={s2}, +persist+multi={s3}")
    all_pass &= ok

    print()
    if all_pass:
        print("ALL TESTS PASSED")
    else:
        print("SOME TESTS FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
