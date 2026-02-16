#!/usr/bin/env python3
"""
Confidence model unit tests.

Validates the commercial confidence scoring formula against known scenarios.
Run: python scripts/test_confidence_model.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def compute_confidence(
    auth_hail_inches: float,
    ev_mrms_peak: float | None,
    ev_hs_peak: float,
    radar_ids: list,
    duration_minutes: float,
    cluster_cids: list,
) -> int:
    """
    Mirror of the commercial confidence formula in storm_cell_tracker.py
    lines 891-955.
    """
    # Evidence flags
    ev_evidence_mrms = ev_mrms_peak is not None and ev_mrms_peak > 0
    ev_evidence_dualpol = ev_hs_peak >= 0.35
    ev_evidence_multi_radar = len(radar_ids) >= 2
    ev_evidence_persistence = duration_minutes >= 10 or len(cluster_cids) >= 2

    # Hail size: two-stage curve
    if auth_hail_inches <= 0:
        hail_size_sc = 0.0
    elif auth_hail_inches <= 2.0:
        hail_size_sc = auth_hail_inches * 0.375
    elif auth_hail_inches <= 4.0:
        hail_size_sc = 0.75 + (auth_hail_inches - 2.0) * 0.125
    else:
        hail_size_sc = 1.0

    mrms_sc = 0.0
    if ev_evidence_mrms and ev_mrms_peak is not None:
        mrms_sc = max(0.0, min(1.0, (ev_mrms_peak - 15.0) / 35.0))
    dualpol_sc = min(1.0, ev_hs_peak / 0.7) if ev_evidence_dualpol else 0.0
    agree_sc = 1.0 if len(radar_ids) >= 3 else (0.6 if len(radar_ids) >= 2 else 0.0)
    persist_sc = min(1.0, duration_minutes / 20.0) if ev_evidence_persistence else 0.0

    # Independent evidence count (multi-radar excluded)
    evidence_count = sum([
        ev_evidence_mrms,
        ev_evidence_dualpol,
        ev_evidence_persistence and duration_minutes >= 15,
    ])
    corroboration_sc = min(1.0, max(0.0, (evidence_count - 1) / 2.0))

    commercial_conf = round(
        hail_size_sc * 30
        + mrms_sc * 20
        + dualpol_sc * 20
        + agree_sc * 10
        + persist_sc * 10
        + corroboration_sc * 10
    )

    # Floors require direct hail evidence (dual-pol or MRMS)
    has_direct_hail_evidence = ev_evidence_dualpol or ev_evidence_mrms
    if has_direct_hail_evidence:
        if auth_hail_inches >= 3.0 and evidence_count >= 2:
            commercial_conf = max(commercial_conf, 75)
        elif auth_hail_inches >= 2.0 and evidence_count >= 2:
            commercial_conf = max(commercial_conf, 60)
        elif auth_hail_inches >= 1.0 and evidence_count >= 1:
            commercial_conf = max(commercial_conf, 35)

    return max(0, min(100, commercial_conf))


def test_scenario(name, expected_range, **kwargs):
    """Run a scenario and check confidence falls in expected range."""
    conf = compute_confidence(**kwargs)
    lo, hi = expected_range
    status = "PASS" if lo <= conf <= hi else "FAIL"
    print(f"  [{status}] {name}: conf={conf}  (expected {lo}-{hi})")
    if status == "FAIL":
        return False
    return True


def main():
    print("=== CONFIDENCE MODEL TESTS ===\n")
    all_pass = True

    # --- Single-scan noise: 0-20 ---
    print("Category: Single-scan noise (target: 0-20)")
    all_pass &= test_scenario(
        "0.3\" weak, 1 scan, no evidence",
        (0, 15),
        auth_hail_inches=0.3, ev_mrms_peak=None, ev_hs_peak=0.1,
        radar_ids=["KTLX"], duration_minutes=0, cluster_cids=["c1"],
    )
    all_pass &= test_scenario(
        "0.5\" marginal, 1 scan, no dual-pol",
        (0, 20),
        auth_hail_inches=0.5, ev_mrms_peak=None, ev_hs_peak=0.2,
        radar_ids=["KTLX"], duration_minutes=0, cluster_cids=["c1"],
    )
    all_pass &= test_scenario(
        "0.0\" no hail detected",
        (0, 5),
        auth_hail_inches=0.0, ev_mrms_peak=None, ev_hs_peak=0.0,
        radar_ids=["KTLX"], duration_minutes=0, cluster_cids=["c1"],
    )

    # --- Developing storms: 30-60 ---
    print("\nCategory: Developing storms (target: 30-60)")
    all_pass &= test_scenario(
        "1.0\" hail, dual-pol confirmed, 10min track",
        (30, 55),
        auth_hail_inches=1.0, ev_mrms_peak=None, ev_hs_peak=0.5,
        radar_ids=["KTLX"], duration_minutes=10, cluster_cids=["c1", "c2"],
    )
    all_pass &= test_scenario(
        "1.5\" hail, MRMS 25mm, no dual-pol, short track",
        (30, 50),
        auth_hail_inches=1.5, ev_mrms_peak=25.0, ev_hs_peak=0.2,
        radar_ids=["KTLX"], duration_minutes=5, cluster_cids=["c1"],
    )
    all_pass &= test_scenario(
        "1.0\" hail, dual-pol, MRMS 20mm, 15min, 1 radar",
        (35, 60),
        auth_hail_inches=1.0, ev_mrms_peak=20.0, ev_hs_peak=0.4,
        radar_ids=["KTLX"], duration_minutes=15, cluster_cids=["c1", "c2"],
    )

    # --- Big hail + corroboration: 70-100 ---
    print("\nCategory: Big hail + corroboration (target: 70-100)")
    all_pass &= test_scenario(
        "4.72\" softball, dual-pol, 30min track, 30 detections",
        (70, 100),
        auth_hail_inches=4.72, ev_mrms_peak=None, ev_hs_peak=0.5,
        radar_ids=["KVNX"], duration_minutes=30,
        cluster_cids=[f"c{i}" for i in range(30)],
    )
    all_pass &= test_scenario(
        "2.5\" hail, MRMS 40mm, dual-pol, 25min, 2 radars",
        (70, 100),
        auth_hail_inches=2.5, ev_mrms_peak=40.0, ev_hs_peak=0.6,
        radar_ids=["KTLX", "KVNX"], duration_minutes=25,
        cluster_cids=["c1", "c2", "c3"],
    )
    all_pass &= test_scenario(
        "3.5\" hail, MRMS 50mm, dual-pol, 20min, 3 radars",
        (80, 100),
        auth_hail_inches=3.5, ev_mrms_peak=50.0, ev_hs_peak=0.7,
        radar_ids=["KTLX", "KVNX", "KFDR"], duration_minutes=20,
        cluster_cids=["c1", "c2"],
    )

    # --- Edge cases ---
    print("\nCategory: Edge cases")
    all_pass &= test_scenario(
        "2.0\" hail, ONLY dual-pol (1 evidence), no floor bump to 60",
        (25, 59),
        auth_hail_inches=2.0, ev_mrms_peak=None, ev_hs_peak=0.5,
        radar_ids=["KTLX"], duration_minutes=5, cluster_cids=["c1"],
    )
    all_pass &= test_scenario(
        "2.0\" hail, dual-pol + 20min persistence (2 evidence), floor 60",
        (60, 80),
        auth_hail_inches=2.0, ev_mrms_peak=None, ev_hs_peak=0.5,
        radar_ids=["KTLX"], duration_minutes=20, cluster_cids=["c1", "c2"],
    )
    all_pass &= test_scenario(
        "0.8\" hail, MRMS only, no dual-pol, short",
        (5, 25),
        auth_hail_inches=0.8, ev_mrms_peak=20.0, ev_hs_peak=0.1,
        radar_ids=["KTLX"], duration_minutes=3, cluster_cids=["c1"],
    )

    # --- Monotonicity: more evidence -> higher score ---
    print("\nCategory: Monotonicity (more evidence -> higher score)")
    base = dict(auth_hail_inches=1.5, ev_hs_peak=0.5, cluster_cids=["c1", "c2"])
    c1 = compute_confidence(ev_mrms_peak=None, radar_ids=["KTLX"], duration_minutes=10, **base)
    c2 = compute_confidence(ev_mrms_peak=30.0, radar_ids=["KTLX"], duration_minutes=10, **base)
    c3 = compute_confidence(ev_mrms_peak=30.0, radar_ids=["KTLX", "KVNX"], duration_minutes=20, **base)
    ok = c1 < c2 < c3
    print(f"  [{'PASS' if ok else 'FAIL'}] dp-only({c1}) < +mrms({c2}) < +multi+time({c3})")
    all_pass &= ok

    # --- Regression: corroboration independence ---
    print("\nCategory: Regression (scoring integrity)")

    # R1: Multi-radar alone does NOT increase evidence_count / corroboration_sc
    base_r1 = dict(auth_hail_inches=1.5, ev_mrms_peak=None, ev_hs_peak=0.5,
                   duration_minutes=10, cluster_cids=["c1", "c2"])
    c_1radar = compute_confidence(radar_ids=["KTLX"], **base_r1)
    c_2radar = compute_confidence(radar_ids=["KTLX", "KVNX"], **base_r1)
    # 2-radar adds agree_sc (0.6*10=6 pts) but NOT corroboration_sc
    delta = c_2radar - c_1radar
    ok_r1 = delta == 6  # exactly agree_sc bump, no corroboration leak
    print(f"  [{'PASS' if ok_r1 else 'FAIL'}] R1: multi-radar adds agree only: "
          f"1-radar={c_1radar}, 2-radar={c_2radar}, delta={delta} (expect 6)")
    all_pass &= ok_r1

    # R2: Persistence + multi-radar WITHOUT dualpol/mrms does NOT trigger floors
    c_no_floor = compute_confidence(
        auth_hail_inches=2.5, ev_mrms_peak=None, ev_hs_peak=0.1,
        radar_ids=["KTLX", "KVNX"], duration_minutes=25,
        cluster_cids=["c1", "c2", "c3"],
    )
    # No dual-pol, no MRMS -> has_direct_hail_evidence=False -> no floor
    # Raw: hail_size_sc=0.75+(0.5*0.125)=0.8125 -> 0.8125*30=24.375,
    #       agree_sc=0.6*10=6, persist_sc=1.0*10=10, corroboration: persist only=1 ev -> 0
    # Total raw ~ 40
    ok_r2 = c_no_floor < 60  # must NOT get the >=2.0" floor of 60
    print(f"  [{'PASS' if ok_r2 else 'FAIL'}] R2: persist+multi w/o dualpol/mrms, no floor: "
          f"conf={c_no_floor} (must be <60)")
    all_pass &= ok_r2

    # R3: 3.5" scores higher than 2.0" under identical evidence
    ev = dict(ev_mrms_peak=30.0, ev_hs_peak=0.5,
              radar_ids=["KTLX"], duration_minutes=20, cluster_cids=["c1", "c2"])
    c_2in = compute_confidence(auth_hail_inches=2.0, **ev)
    c_3_5in = compute_confidence(auth_hail_inches=3.5, **ev)
    ok_r3 = c_3_5in > c_2in
    print(f"  [{'PASS' if ok_r3 else 'FAIL'}] R3: 3.5\" > 2.0\" same evidence: "
          f"2.0\"={c_2in}, 3.5\"={c_3_5in}")
    all_pass &= ok_r3

    print()
    if all_pass:
        print("ALL TESTS PASSED")
    else:
        print("SOME TESTS FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
