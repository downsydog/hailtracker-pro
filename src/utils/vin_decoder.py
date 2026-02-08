"""
VIN Decoder Utility
Uses free NHTSA API to decode Vehicle Identification Numbers.
Auto-detects vehicle tier and aluminum panels for PDR estimating.
"""

import requests
from typing import Dict, List

NHTSA_API_URL = "https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVin/{vin}?format=json"

LUXURY_MAKES = [
    "BMW", "MERCEDES-BENZ", "AUDI", "LEXUS", "INFINITI", "ACURA",
    "GENESIS", "CADILLAC", "LINCOLN", "PORSCHE", "LAND ROVER",
    "JAGUAR", "VOLVO", "MASERATI", "ALFA ROMEO"
]
EV_MAKES = ["TESLA", "RIVIAN", "LUCID", "POLESTAR"]
ECONOMY_MAKES = ["KIA", "HYUNDAI", "NISSAN", "MITSUBISHI"]
PREMIUM_MAKES = ["MAZDA", "SUBARU", "VOLKSWAGEN", "BUICK", "CHRYSLER"]

ALUMINUM_VEHICLES = {
    "FORD": ["F-150", "F150", "EXPEDITION"],
    "TESLA": ["MODEL S", "MODEL 3", "MODEL X", "MODEL Y"],
    "JAGUAR": ["XE", "XF", "F-TYPE", "F-PACE"],
    "LAND ROVER": ["RANGE ROVER", "DEFENDER", "DISCOVERY"],
    "AUDI": ["A8", "R8"],
    "CHEVROLET": ["CORVETTE"],
}


def decode_vin(vin: str) -> Dict:
    if not vin:
        return {"error": "VIN is required", "valid": False}
    vin = vin.strip().upper()
    if len(vin) != 17:
        return {"error": f"VIN must be 17 characters", "valid": False}
    
    try:
        response = requests.get(NHTSA_API_URL.format(vin=vin), timeout=10)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        return {"error": str(e), "valid": False, "vin": vin}
    
    results = {item["Variable"]: item["Value"] for item in data.get("Results", [])}
    make = (results.get("Make") or "").strip().upper()
    model = (results.get("Model") or "").strip()
    year = results.get("Model Year")
    
    decoded = {
        "valid": True,
        "vin": vin,
        "year": int(year) if year and year.isdigit() else None,
        "make": results.get("Make"),
        "model": model,
        "trim": results.get("Trim"),
        "body_class": results.get("Body Class"),
        "drive_type": results.get("Drive Type"),
        "fuel_type": results.get("Fuel Type - Primary"),
        "vehicle_type": results.get("Vehicle Type"),
    }
    
    decoded["vehicle_tier"] = _determine_tier(make, model, results)
    decoded["aluminum_panels"] = _detect_aluminum_panels(make, model)
    decoded["has_aluminum"] = len(decoded["aluminum_panels"]) > 0
    
    fuel_upper = (results.get("Fuel Type - Primary") or "").upper()
    decoded["is_ev"] = "ELECTRIC" in fuel_upper or make in EV_MAKES
    
    adas = []
    if results.get("Adaptive Cruise Control (ACC)") == "Standard": adas.append("ACC")
    if results.get("Forward Collision Warning") == "Standard": adas.append("FCW")
    if results.get("Lane Departure Warning") == "Standard": adas.append("LDW")
    if results.get("Backup Camera") == "Standard": adas.append("Backup Camera")
    decoded["adas_features"] = adas
    decoded["has_adas"] = len(adas) > 0
    
    return decoded


def _determine_tier(make: str, model: str, nhtsa_data: Dict) -> str:
    make_upper = make.upper()
    fuel_type = (nhtsa_data.get("Fuel Type - Primary") or "").upper()
    if make_upper in EV_MAKES or "ELECTRIC" in fuel_type:
        return "ev_adas"
    if make_upper in LUXURY_MAKES:
        return "luxury"
    if make_upper in PREMIUM_MAKES:
        return "premium"
    if make_upper in ECONOMY_MAKES:
        return "economy"
    return "standard"


def _detect_aluminum_panels(make: str, model: str) -> List[str]:
    make_upper = make.upper()
    model_upper = (model or "").upper()
    if make_upper not in ALUMINUM_VEHICLES:
        return []
    for pattern in ALUMINUM_VEHICLES[make_upper]:
        if pattern.upper() in model_upper:
            if make_upper == "FORD" and "F-150" in model_upper:
                return ["hood", "fenders", "doors", "tailgate", "bed_sides"]
            elif make_upper == "TESLA":
                return ["hood", "doors", "trunk_lid", "fenders"]
            else:
                return ["hood", "fenders", "doors", "trunk_lid"]
    return []


def get_tier_multiplier(tier: str) -> float:
    return {"economy": 0.85, "standard": 1.0, "premium": 1.15, "luxury": 1.35, "ev_adas": 1.25}.get(tier, 1.0)


def format_vehicle_string(decoded: Dict) -> str:
    if not decoded.get("valid"): return "Unknown"
    parts = [str(decoded.get("year", "")), decoded.get("make", ""), decoded.get("model", "")]
    return " ".join(p for p in parts if p)
