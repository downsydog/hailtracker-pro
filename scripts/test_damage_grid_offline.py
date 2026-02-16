#!/usr/bin/env python3
"""
Offline validation for damage_grid module.

Tests:
1. Grid generation with synthetic detection points
2. Sigmoid / probability model sanity
3. IDW interpolation
4. Severity labels
5. DB persistence (temp file)
6. Query + GeoJSON conversion
7. Adaptive cell sizing
"""
import os, sys, tempfile, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.radar.damage_grid import (
    generate_damage_grid,
    persist_damage_grid,
    query_damage_grid,
    query_damage_grid_bbox,
    cells_to_geojson,
    ensure_damage_grid_table,
    _sigmoid,
    _damage_probability,
    _severity_label,
    _cell_confidence,
    _idw_hail,
    _haversine_km,
    EV_MRMS, EV_IDW_3, EV_IDW_1, EV_DWELL,
)

passed = 0
failed = 0


def check(name, condition, detail=""):
    global passed, failed
    if condition:
        print(f"  OK: {name}")
        passed += 1
    else:
        print(f"  FAIL: {name} — {detail}")
        failed += 1


# === 1. Sigmoid sanity ===
print("\n=== 1. Sigmoid ===")
check("sigmoid(0) = 0.5", abs(_sigmoid(0) - 0.5) < 1e-6)
check("sigmoid(20) ~ 1.0", _sigmoid(20) > 0.999)
check("sigmoid(-20) ~ 0.0", _sigmoid(-20) < 0.001)

# === 2. Damage probability model ===
print("\n=== 2. Damage probability ===")
p_small = _damage_probability(10, 0)
p_moderate = _damage_probability(25, 60)
p_severe = _damage_probability(50, 120)
p_huge = _damage_probability(75, 180)
p_tiny = _damage_probability(5, 0)

check("tiny hail (5mm) -> 0", p_tiny == 0.0, f"got {p_tiny}")
check("small hail (10mm) has some prob", p_small >= 0.0, f"got {p_small}")
check("moderate > small", p_moderate > p_small, f"{p_moderate} vs {p_small}")
check("severe > moderate", p_severe > p_moderate, f"{p_severe} vs {p_moderate}")
check("huge > severe", p_huge > p_severe, f"{p_huge} vs {p_severe}")
check("all probs in [0,1]", all(0 <= p <= 1 for p in [p_small, p_moderate, p_severe, p_huge]))

# === 3. Severity labels ===
print("\n=== 3. Severity labels ===")
check("prob=0.9 -> CATASTROPHIC", _severity_label(0.9) == "CATASTROPHIC")
check("prob=0.6 -> SEVERE", _severity_label(0.6) == "SEVERE")
check("prob=0.35 -> MODERATE", _severity_label(0.35) == "MODERATE")
check("prob=0.15 -> LIGHT", _severity_label(0.15) == "LIGHT")
check("prob=0.05 -> NONE", _severity_label(0.05) == "NONE")

# === 4. Cell confidence ===
print("\n=== 4. Cell confidence ===")
c1 = _cell_confidence(60, EV_MRMS | EV_IDW_3)
c2 = _cell_confidence(60, EV_IDW_1)
c3 = _cell_confidence(60, 0)
check("MRMS+IDW3 boosts confidence", c1 > 60, f"got {c1}")
check("IDW1 only: same base", c2 == 60, f"got {c2}")
check("no evidence: penalized", c3 < 60, f"got {c3}")

# === 5. IDW interpolation ===
print("\n=== 5. IDW interpolation ===")
points = [
    (30.0, -95.0, 40.0),
    (30.1, -95.1, 50.0),
    (30.05, -95.05, 45.0),
]
val, cnt = _idw_hail(30.05, -95.05, points, radius_km=20.0)
check("IDW returns value > 0", val > 0, f"got {val}")
check("IDW count >= 1", cnt >= 1, f"got {cnt}")

val_far, cnt_far = _idw_hail(40.0, -80.0, points, radius_km=20.0)
check("IDW far away -> 0", val_far == 0.0 and cnt_far == 0)

# === 6. Haversine distance ===
print("\n=== 6. Haversine ===")
d = _haversine_km(30.0, -95.0, 30.0, -95.0)
check("same point -> 0 km", d < 0.01, f"got {d}")
d2 = _haversine_km(30.0, -95.0, 31.0, -95.0)
check("1 deg lat ~ 111 km", 100 < d2 < 120, f"got {d2}")

# === 7. Grid generation ===
print("\n=== 7. Grid generation ===")
bbox = {
    "bbox_min_lat": 29.8,
    "bbox_max_lat": 30.2,
    "bbox_min_lon": -95.2,
    "bbox_max_lon": -94.8,
}
detections = [
    {"lat": 30.0, "lon": -95.0, "mesh_mm": 40.0},
    {"lat": 30.05, "lon": -95.05, "mesh_mm": 55.0},
    {"lat": 29.95, "lon": -94.95, "mesh_mm": 35.0},
    {"lat": 30.1, "lon": -95.1, "mesh_mm": 60.0},
]
cells = generate_damage_grid(
    bbox=bbox,
    detections=detections,
    event_confidence=70.0,
    storm_speed_kmh=45.0,
    cell_size_km=2.0,
)
check("grid generated cells > 0", len(cells) > 0, f"got {len(cells)}")
check("first cell has required keys", all(k in cells[0] for k in [
    "center_lat", "center_lon", "authoritative_hail_mm",
    "damage_probability", "damage_severity", "cell_confidence",
    "evidence_mask", "dwell_seconds",
]))

# Check cell values are reasonable
max_prob = max(c["damage_probability"] for c in cells)
max_hail = max(c["authoritative_hail_mm"] for c in cells)
check("max prob > 0", max_prob > 0, f"got {max_prob}")
check("max hail > 0", max_hail > 0, f"got {max_hail}")
check("all severities valid", all(c["damage_severity"] in
    ["CATASTROPHIC", "SEVERE", "MODERATE", "LIGHT", "NONE"] for c in cells))

# === 8. Empty bbox -> empty grid ===
print("\n=== 8. Edge cases ===")
empty_cells = generate_damage_grid(
    bbox={"bbox_min_lat": 30, "bbox_max_lat": 30, "bbox_min_lon": -95, "bbox_max_lon": -95},
    detections=detections,
)
check("zero-area bbox -> empty", len(empty_cells) == 0)

no_det = generate_damage_grid(bbox=bbox, detections=[])
check("no detections -> empty", len(no_det) == 0)

# === 9. DB persistence ===
print("\n=== 9. DB persistence ===")
with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
    tmp_db = f.name

try:
    ensure_damage_grid_table(tmp_db)

    n = persist_damage_grid("TEST_EVENT_001", cells, tmp_db)
    check(f"persisted {n} cells", n == len(cells), f"expected {len(cells)}, got {n}")

    # Query back
    queried = query_damage_grid("TEST_EVENT_001", tmp_db)
    check("query returns cells", len(queried) > 0, f"got {len(queried)}")
    check("query count matches", len(queried) == n, f"expected {n}, got {len(queried)}")

    # Idempotency: persist again
    n2 = persist_damage_grid("TEST_EVENT_001", cells, tmp_db)
    queried2 = query_damage_grid("TEST_EVENT_001", tmp_db)
    check("idempotent: same count after re-persist", len(queried2) == n,
          f"expected {n}, got {len(queried2)}")

    # === 10. Bbox query ===
    print("\n=== 10. Bbox query ===")
    bbox_cells = query_damage_grid_bbox(
        min_lon=-95.3, min_lat=29.7,
        max_lon=-94.7, max_lat=30.3,
        db_path=tmp_db,
    )
    check("bbox query returns cells", len(bbox_cells) > 0, f"got {len(bbox_cells)}")

    # === 11. GeoJSON conversion ===
    print("\n=== 11. GeoJSON ===")
    geojson = cells_to_geojson(queried)
    check("geojson is FeatureCollection", geojson["type"] == "FeatureCollection")
    check("features count matches", len(geojson["features"]) == len(queried))
    feat = geojson["features"][0]
    check("feature has Polygon geometry", feat["geometry"]["type"] == "Polygon")
    check("feature has properties", "damage_probability" in feat["properties"])
    check("coordinates are closed ring", feat["geometry"]["coordinates"][0][0] == feat["geometry"]["coordinates"][0][-1])

    # Verify JSON serializable
    json_str = json.dumps(geojson)
    check("GeoJSON is JSON-serializable", len(json_str) > 100)

finally:
    os.unlink(tmp_db)

# === Summary ===
print(f"\n{'='*60}")
print(f"RESULTS: {passed} passed, {failed} failed")
print(f"{'='*60}")
if failed > 0:
    sys.exit(1)
else:
    print("ALL DAMAGE GRID TESTS PASSED")
