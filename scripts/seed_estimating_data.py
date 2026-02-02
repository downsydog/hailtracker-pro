"""
PDR Pro Estimating System - Seed Data
Populates R/I operations, panel associations, vehicle times, labor rates,
insurance companies, alert rules, and photo checklists.

Run this after schema creation:
    python scripts/seed_estimating_data.py
"""

import sqlite3
import json
import os
import sys
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# =============================================================================
# R/I OPERATIONS CATALOG (60+ operations)
# =============================================================================

RI_OPERATIONS = [
    # Electrical - Front
    {"name": "R/I Headlight Assembly (L)", "code": "RI-HDLT-L", "category": "electrical", "default_hours": 0.5, "labor_type": "body"},
    {"name": "R/I Headlight Assembly (R)", "code": "RI-HDLT-R", "category": "electrical", "default_hours": 0.5, "labor_type": "body"},
    {"name": "R/I Fog Light (L)", "code": "RI-FOG-L", "category": "electrical", "default_hours": 0.3, "labor_type": "body"},
    {"name": "R/I Fog Light (R)", "code": "RI-FOG-R", "category": "electrical", "default_hours": 0.3, "labor_type": "body"},
    {"name": "R/I Turn Signal (L)", "code": "RI-TURN-L", "category": "electrical", "default_hours": 0.3, "labor_type": "body"},
    {"name": "R/I Turn Signal (R)", "code": "RI-TURN-R", "category": "electrical", "default_hours": 0.3, "labor_type": "body"},

    # Electrical - Rear
    {"name": "R/I Tail Light Assembly (L)", "code": "RI-TAIL-L", "category": "electrical", "default_hours": 0.4, "labor_type": "body"},
    {"name": "R/I Tail Light Assembly (R)", "code": "RI-TAIL-R", "category": "electrical", "default_hours": 0.4, "labor_type": "body"},
    {"name": "R/I Third Brake Light", "code": "RI-3BRAKE", "category": "electrical", "default_hours": 0.3, "labor_type": "body"},
    {"name": "R/I License Plate Lights", "code": "RI-LICLT", "category": "electrical", "default_hours": 0.2, "labor_type": "body"},

    # Trim - Exterior
    {"name": "R/I Fender Liner (L)", "code": "RI-FLIN-L", "category": "trim", "default_hours": 0.4, "labor_type": "body"},
    {"name": "R/I Fender Liner (R)", "code": "RI-FLIN-R", "category": "trim", "default_hours": 0.4, "labor_type": "body"},
    {"name": "R/I Grille Assembly", "code": "RI-GRILLE", "category": "trim", "default_hours": 0.5, "labor_type": "body"},
    {"name": "R/I Front Bumper Cover", "code": "RI-FBUMP", "category": "trim", "default_hours": 1.0, "labor_type": "body"},
    {"name": "R/I Rear Bumper Cover", "code": "RI-RBUMP", "category": "trim", "default_hours": 0.8, "labor_type": "body"},
    {"name": "R/I Hood Insulation", "code": "RI-HOODIN", "category": "trim", "default_hours": 0.2, "labor_type": "body"},
    {"name": "R/I Cowl Panel/Cover", "code": "RI-COWL", "category": "trim", "default_hours": 0.4, "labor_type": "body"},
    {"name": "R/I Wiper Arms", "code": "RI-WIPER", "category": "trim", "default_hours": 0.3, "labor_type": "body"},
    {"name": "R/I Roof Rails (L)", "code": "RI-RRAIL-L", "category": "trim", "default_hours": 0.5, "labor_type": "body"},
    {"name": "R/I Roof Rails (R)", "code": "RI-RRAIL-R", "category": "trim", "default_hours": 0.5, "labor_type": "body"},
    {"name": "R/I Antenna/Shark Fin", "code": "RI-ANT", "category": "electrical", "default_hours": 0.3, "labor_type": "body"},
    {"name": "R/I Rear Spoiler", "code": "RI-SPOILER", "category": "trim", "default_hours": 0.5, "labor_type": "body"},
    {"name": "R/I Fuel Door", "code": "RI-FUEL", "category": "trim", "default_hours": 0.2, "labor_type": "body"},
    {"name": "R/I Emblem/Badge", "code": "RI-EMBLEM", "category": "trim", "default_hours": 0.1, "labor_type": "body"},

    # Trim - Interior (THE MONEY ITEMS)
    {"name": "R/I Headliner", "code": "RI-HDLNR", "category": "interior", "default_hours": 2.5, "labor_type": "body"},
    {"name": "R/I Headliner (with sunroof)", "code": "RI-HDLNR-SR", "category": "interior", "default_hours": 3.5, "labor_type": "body"},
    {"name": "R/I Door Trim Panel (LF)", "code": "RI-DTRM-LF", "category": "interior", "default_hours": 0.5, "labor_type": "body"},
    {"name": "R/I Door Trim Panel (RF)", "code": "RI-DTRM-RF", "category": "interior", "default_hours": 0.5, "labor_type": "body"},
    {"name": "R/I Door Trim Panel (LR)", "code": "RI-DTRM-LR", "category": "interior", "default_hours": 0.5, "labor_type": "body"},
    {"name": "R/I Door Trim Panel (RR)", "code": "RI-DTRM-RR", "category": "interior", "default_hours": 0.5, "labor_type": "body"},
    {"name": "R/I A-Pillar Trim (L)", "code": "RI-APIL-L", "category": "interior", "default_hours": 0.2, "labor_type": "body"},
    {"name": "R/I A-Pillar Trim (R)", "code": "RI-APIL-R", "category": "interior", "default_hours": 0.2, "labor_type": "body"},
    {"name": "R/I B-Pillar Trim (L)", "code": "RI-BPIL-L", "category": "interior", "default_hours": 0.3, "labor_type": "body"},
    {"name": "R/I B-Pillar Trim (R)", "code": "RI-BPIL-R", "category": "interior", "default_hours": 0.3, "labor_type": "body"},
    {"name": "R/I C-Pillar Trim (L)", "code": "RI-CPIL-L", "category": "interior", "default_hours": 0.3, "labor_type": "body"},
    {"name": "R/I C-Pillar Trim (R)", "code": "RI-CPIL-R", "category": "interior", "default_hours": 0.3, "labor_type": "body"},
    {"name": "R/I D-Pillar Trim (L)", "code": "RI-DPIL-L", "category": "interior", "default_hours": 0.3, "labor_type": "body"},
    {"name": "R/I D-Pillar Trim (R)", "code": "RI-DPIL-R", "category": "interior", "default_hours": 0.3, "labor_type": "body"},
    {"name": "R/I Trunk/Cargo Liner", "code": "RI-TRNKLN", "category": "interior", "default_hours": 0.3, "labor_type": "body"},
    {"name": "R/I Sunroof Trim/Shade", "code": "RI-SRTRIM", "category": "interior", "default_hours": 0.4, "labor_type": "body"},
    {"name": "R/I Rear Seat", "code": "RI-RSEAT", "category": "interior", "default_hours": 0.5, "labor_type": "body"},
    {"name": "R/I Rear Seat Back", "code": "RI-RSEATB", "category": "interior", "default_hours": 0.4, "labor_type": "body"},
    {"name": "R/I Package Tray", "code": "RI-PKGTRAY", "category": "interior", "default_hours": 0.3, "labor_type": "body"},

    # Moldings
    {"name": "R/I Belt Molding (LF Door)", "code": "RI-BELT-LF", "category": "molding", "default_hours": 0.3, "labor_type": "body"},
    {"name": "R/I Belt Molding (RF Door)", "code": "RI-BELT-RF", "category": "molding", "default_hours": 0.3, "labor_type": "body"},
    {"name": "R/I Belt Molding (LR Door)", "code": "RI-BELT-LR", "category": "molding", "default_hours": 0.3, "labor_type": "body"},
    {"name": "R/I Belt Molding (RR Door)", "code": "RI-BELT-RR", "category": "molding", "default_hours": 0.3, "labor_type": "body"},
    {"name": "R/I Windshield Molding", "code": "RI-WSMOLD", "category": "molding", "default_hours": 0.4, "labor_type": "body"},
    {"name": "R/I Rear Glass Molding", "code": "RI-RGMOLD", "category": "molding", "default_hours": 0.4, "labor_type": "body"},
    {"name": "R/I Drip Molding (L)", "code": "RI-DRIP-L", "category": "molding", "default_hours": 0.4, "labor_type": "body"},
    {"name": "R/I Drip Molding (R)", "code": "RI-DRIP-R", "category": "molding", "default_hours": 0.4, "labor_type": "body"},
    {"name": "R/I Body Side Molding (L)", "code": "RI-BSIDE-L", "category": "molding", "default_hours": 0.5, "labor_type": "body"},
    {"name": "R/I Body Side Molding (R)", "code": "RI-BSIDE-R", "category": "molding", "default_hours": 0.5, "labor_type": "body"},

    # Glass
    {"name": "R/I Windshield", "code": "RI-WSHLD", "category": "glass", "default_hours": 1.5, "labor_type": "glass"},
    {"name": "R/I Rear Glass", "code": "RI-RGLASS", "category": "glass", "default_hours": 1.2, "labor_type": "glass"},
    {"name": "R/I Door Glass (LF)", "code": "RI-DGLS-LF", "category": "glass", "default_hours": 0.8, "labor_type": "body"},
    {"name": "R/I Door Glass (RF)", "code": "RI-DGLS-RF", "category": "glass", "default_hours": 0.8, "labor_type": "body"},
    {"name": "R/I Door Glass (LR)", "code": "RI-DGLS-LR", "category": "glass", "default_hours": 0.8, "labor_type": "body"},
    {"name": "R/I Door Glass (RR)", "code": "RI-DGLS-RR", "category": "glass", "default_hours": 0.8, "labor_type": "body"},
    {"name": "R/I Quarter Glass (L)", "code": "RI-QGLS-L", "category": "glass", "default_hours": 0.6, "labor_type": "body"},
    {"name": "R/I Quarter Glass (R)", "code": "RI-QGLS-R", "category": "glass", "default_hours": 0.6, "labor_type": "body"},
    {"name": "R/I Sunroof Glass", "code": "RI-SRGLS", "category": "glass", "default_hours": 1.0, "labor_type": "body"},

    # Mirrors
    {"name": "R/I Mirror Assembly (L)", "code": "RI-MIRR-L", "category": "electrical", "default_hours": 0.4, "labor_type": "body"},
    {"name": "R/I Mirror Assembly (R)", "code": "RI-MIRR-R", "category": "electrical", "default_hours": 0.4, "labor_type": "body"},

    # Mechanical
    {"name": "R/I Window Regulator (LF)", "code": "RI-WREG-LF", "category": "mechanical", "default_hours": 1.0, "labor_type": "mechanical"},
    {"name": "R/I Window Regulator (RF)", "code": "RI-WREG-RF", "category": "mechanical", "default_hours": 1.0, "labor_type": "mechanical"},
    {"name": "R/I Window Regulator (LR)", "code": "RI-WREG-LR", "category": "mechanical", "default_hours": 1.0, "labor_type": "mechanical"},
    {"name": "R/I Window Regulator (RR)", "code": "RI-WREG-RR", "category": "mechanical", "default_hours": 1.0, "labor_type": "mechanical"},
    {"name": "R/I Door Handle (Exterior)", "code": "RI-DHEXT", "category": "mechanical", "default_hours": 0.4, "labor_type": "body"},
    {"name": "R/I Hood Latch", "code": "RI-HDLTCH", "category": "mechanical", "default_hours": 0.3, "labor_type": "body"},
    {"name": "R/I Trunk Latch", "code": "RI-TRNKLTCH", "category": "mechanical", "default_hours": 0.3, "labor_type": "body"},
]


# =============================================================================
# PANEL → R/I ASSOCIATIONS
# =============================================================================

PANEL_RI_ASSOCIATIONS = [
    # Hood
    {"panel": "hood", "ri_code": "RI-HOODIN", "default": True, "min_dents": 0, "notes": "Always needed for hood access"},
    {"panel": "hood", "ri_code": "RI-COWL", "default": True, "min_dents": 5, "notes": "Cowl panel for rear hood access"},
    {"panel": "hood", "ri_code": "RI-WIPER", "default": False, "min_dents": 15, "notes": "Wipers may block access to rear hood"},
    {"panel": "hood", "ri_code": "RI-GRILLE", "default": False, "min_dents": 0, "notes": "If damage near front edge"},

    # Left Fender
    {"panel": "left_fender", "ri_code": "RI-HDLT-L", "default": True, "min_dents": 0, "notes": "Headlight for front access"},
    {"panel": "left_fender", "ri_code": "RI-FLIN-L", "default": True, "min_dents": 0, "notes": "Liner for underside access"},
    {"panel": "left_fender", "ri_code": "RI-MIRR-L", "default": False, "min_dents": 10, "notes": "Mirror may block access"},
    {"panel": "left_fender", "ri_code": "RI-EMBLEM", "default": False, "min_dents": 0, "notes": "Fender badge if present"},

    # Right Fender
    {"panel": "right_fender", "ri_code": "RI-HDLT-R", "default": True, "min_dents": 0, "notes": "Headlight for front access"},
    {"panel": "right_fender", "ri_code": "RI-FLIN-R", "default": True, "min_dents": 0, "notes": "Liner for underside access"},
    {"panel": "right_fender", "ri_code": "RI-MIRR-R", "default": False, "min_dents": 10, "notes": "Mirror may block access"},

    # Left Front Door
    {"panel": "left_front_door", "ri_code": "RI-DTRM-LF", "default": True, "min_dents": 0, "notes": "Door panel for inside access"},
    {"panel": "left_front_door", "ri_code": "RI-BELT-LF", "default": True, "min_dents": 5, "notes": "Belt molding for upper access"},
    {"panel": "left_front_door", "ri_code": "RI-MIRR-L", "default": False, "min_dents": 10, "notes": "Mirror may block access"},
    {"panel": "left_front_door", "ri_code": "RI-DGLS-LF", "default": False, "min_dents": 20, "access": "difficult", "notes": "Glass R/I for severe damage"},

    # Right Front Door
    {"panel": "right_front_door", "ri_code": "RI-DTRM-RF", "default": True, "min_dents": 0, "notes": "Door panel for inside access"},
    {"panel": "right_front_door", "ri_code": "RI-BELT-RF", "default": True, "min_dents": 5, "notes": "Belt molding for upper access"},
    {"panel": "right_front_door", "ri_code": "RI-MIRR-R", "default": False, "min_dents": 10, "notes": "Mirror may block access"},
    {"panel": "right_front_door", "ri_code": "RI-DGLS-RF", "default": False, "min_dents": 20, "access": "difficult", "notes": "Glass R/I for severe damage"},

    # Left Rear Door
    {"panel": "left_rear_door", "ri_code": "RI-DTRM-LR", "default": True, "min_dents": 0, "notes": "Door panel for inside access"},
    {"panel": "left_rear_door", "ri_code": "RI-BELT-LR", "default": True, "min_dents": 5, "notes": "Belt molding for upper access"},
    {"panel": "left_rear_door", "ri_code": "RI-DGLS-LR", "default": False, "min_dents": 20, "access": "difficult", "notes": "Glass R/I for severe damage"},

    # Right Rear Door
    {"panel": "right_rear_door", "ri_code": "RI-DTRM-RR", "default": True, "min_dents": 0, "notes": "Door panel for inside access"},
    {"panel": "right_rear_door", "ri_code": "RI-BELT-RR", "default": True, "min_dents": 5, "notes": "Belt molding for upper access"},
    {"panel": "right_rear_door", "ri_code": "RI-DGLS-RR", "default": False, "min_dents": 20, "access": "difficult", "notes": "Glass R/I for severe damage"},

    # Roof - THE MONEY PANEL
    {"panel": "roof", "ri_code": "RI-HDLNR", "default": True, "min_dents": 0, "vehicle_condition": "no_sunroof", "notes": "Standard headliner"},
    {"panel": "roof", "ri_code": "RI-HDLNR-SR", "default": True, "min_dents": 0, "vehicle_condition": "has_sunroof", "notes": "Headliner with sunroof"},
    {"panel": "roof", "ri_code": "RI-ANT", "default": True, "min_dents": 0, "notes": "Antenna/shark fin on most vehicles"},
    {"panel": "roof", "ri_code": "RI-RRAIL-L", "default": False, "min_dents": 0, "vehicle_condition": "has_roof_rails", "notes": "Roof rails if equipped"},
    {"panel": "roof", "ri_code": "RI-RRAIL-R", "default": False, "min_dents": 0, "vehicle_condition": "has_roof_rails", "notes": "Roof rails if equipped"},
    {"panel": "roof", "ri_code": "RI-SRTRIM", "default": False, "min_dents": 0, "vehicle_condition": "has_sunroof", "notes": "Sunroof trim/shade"},
    {"panel": "roof", "ri_code": "RI-3BRAKE", "default": False, "min_dents": 15, "notes": "Third brake light if accessing rear"},
    {"panel": "roof", "ri_code": "RI-APIL-L", "default": False, "min_dents": 20, "notes": "A-pillar for headliner access"},
    {"panel": "roof", "ri_code": "RI-APIL-R", "default": False, "min_dents": 20, "notes": "A-pillar for headliner access"},
    {"panel": "roof", "ri_code": "RI-BPIL-L", "default": False, "min_dents": 20, "notes": "B-pillar for headliner access"},
    {"panel": "roof", "ri_code": "RI-BPIL-R", "default": False, "min_dents": 20, "notes": "B-pillar for headliner access"},
    {"panel": "roof", "ri_code": "RI-CPIL-L", "default": False, "min_dents": 25, "notes": "C-pillar for full headliner drop"},
    {"panel": "roof", "ri_code": "RI-CPIL-R", "default": False, "min_dents": 25, "notes": "C-pillar for full headliner drop"},

    # Left Quarter
    {"panel": "left_quarter", "ri_code": "RI-TAIL-L", "default": True, "min_dents": 0, "notes": "Tail light for access"},
    {"panel": "left_quarter", "ri_code": "RI-QGLS-L", "default": False, "min_dents": 10, "notes": "Quarter glass if access needed"},
    {"panel": "left_quarter", "ri_code": "RI-FUEL", "default": False, "min_dents": 5, "vehicle_condition": "fuel_door_left", "notes": "Fuel door if on left side"},
    {"panel": "left_quarter", "ri_code": "RI-CPIL-L", "default": False, "min_dents": 15, "notes": "C-pillar trim for interior access"},
    {"panel": "left_quarter", "ri_code": "RI-TRNKLN", "default": False, "min_dents": 10, "notes": "Trunk liner for inside access"},

    # Right Quarter
    {"panel": "right_quarter", "ri_code": "RI-TAIL-R", "default": True, "min_dents": 0, "notes": "Tail light for access"},
    {"panel": "right_quarter", "ri_code": "RI-QGLS-R", "default": False, "min_dents": 10, "notes": "Quarter glass if access needed"},
    {"panel": "right_quarter", "ri_code": "RI-FUEL", "default": False, "min_dents": 5, "vehicle_condition": "fuel_door_right", "notes": "Fuel door if on right side"},
    {"panel": "right_quarter", "ri_code": "RI-CPIL-R", "default": False, "min_dents": 15, "notes": "C-pillar trim for interior access"},

    # Trunk/Liftgate
    {"panel": "trunk", "ri_code": "RI-TRNKLN", "default": True, "min_dents": 0, "notes": "Trunk liner for inside access"},
    {"panel": "trunk", "ri_code": "RI-SPOILER", "default": False, "min_dents": 0, "vehicle_condition": "has_spoiler", "notes": "Spoiler if equipped"},
    {"panel": "trunk", "ri_code": "RI-LICLT", "default": True, "min_dents": 3, "notes": "License plate lights"},
    {"panel": "trunk", "ri_code": "RI-3BRAKE", "default": False, "min_dents": 8, "notes": "Third brake light if mounted on trunk"},
    {"panel": "trunk", "ri_code": "RI-EMBLEM", "default": False, "min_dents": 0, "notes": "Trunk emblem/badge"},
]


# =============================================================================
# VEHICLE-SPECIFIC R/I TIMES (Top 10 vehicles)
# =============================================================================

VEHICLE_RI_TIMES = [
    # -------------------------------------------------------------------------
    # Ford F-150 (2015-2020)
    # -------------------------------------------------------------------------
    {"ri_code": "RI-HDLNR", "year_start": 2015, "year_end": 2020, "make": "Ford", "model": "F-150", "body_style": "SuperCrew", "hours": 3.2, "source": "mitchell"},
    {"ri_code": "RI-HDLNR-SR", "year_start": 2015, "year_end": 2020, "make": "Ford", "model": "F-150", "body_style": "SuperCrew", "hours": 4.5, "source": "mitchell"},
    {"ri_code": "RI-HDLT-L", "year_start": 2015, "year_end": 2020, "make": "Ford", "model": "F-150", "hours": 0.5, "source": "mitchell"},
    {"ri_code": "RI-HDLT-R", "year_start": 2015, "year_end": 2020, "make": "Ford", "model": "F-150", "hours": 0.5, "source": "mitchell"},
    {"ri_code": "RI-FLIN-L", "year_start": 2015, "year_end": 2020, "make": "Ford", "model": "F-150", "hours": 0.4, "source": "mitchell"},
    {"ri_code": "RI-FLIN-R", "year_start": 2015, "year_end": 2020, "make": "Ford", "model": "F-150", "hours": 0.4, "source": "mitchell"},
    {"ri_code": "RI-DTRM-LF", "year_start": 2015, "year_end": 2020, "make": "Ford", "model": "F-150", "hours": 0.6, "source": "mitchell"},
    {"ri_code": "RI-DTRM-RF", "year_start": 2015, "year_end": 2020, "make": "Ford", "model": "F-150", "hours": 0.6, "source": "mitchell"},
    {"ri_code": "RI-DTRM-LR", "year_start": 2015, "year_end": 2020, "make": "Ford", "model": "F-150", "hours": 0.5, "source": "mitchell"},
    {"ri_code": "RI-DTRM-RR", "year_start": 2015, "year_end": 2020, "make": "Ford", "model": "F-150", "hours": 0.5, "source": "mitchell"},
    {"ri_code": "RI-TAIL-L", "year_start": 2015, "year_end": 2020, "make": "Ford", "model": "F-150", "hours": 0.3, "source": "mitchell"},
    {"ri_code": "RI-TAIL-R", "year_start": 2015, "year_end": 2020, "make": "Ford", "model": "F-150", "hours": 0.3, "source": "mitchell"},
    {"ri_code": "RI-ANT", "year_start": 2015, "year_end": 2020, "make": "Ford", "model": "F-150", "hours": 0.3, "source": "oem"},
    {"ri_code": "RI-RRAIL-L", "year_start": 2015, "year_end": 2020, "make": "Ford", "model": "F-150", "hours": 0.6, "source": "oem"},
    {"ri_code": "RI-RRAIL-R", "year_start": 2015, "year_end": 2020, "make": "Ford", "model": "F-150", "hours": 0.6, "source": "oem"},
    {"ri_code": "RI-HOODIN", "year_start": 2015, "year_end": 2020, "make": "Ford", "model": "F-150", "hours": 0.2, "source": "oem"},

    # Ford F-150 (2021-2024) - Slightly different
    {"ri_code": "RI-HDLNR", "year_start": 2021, "year_end": 2024, "make": "Ford", "model": "F-150", "body_style": "SuperCrew", "hours": 3.5, "source": "mitchell"},
    {"ri_code": "RI-HDLNR-SR", "year_start": 2021, "year_end": 2024, "make": "Ford", "model": "F-150", "body_style": "SuperCrew", "hours": 4.8, "source": "mitchell"},

    # -------------------------------------------------------------------------
    # Chevrolet Silverado 1500 (2019-2024)
    # -------------------------------------------------------------------------
    {"ri_code": "RI-HDLNR", "year_start": 2019, "year_end": 2024, "make": "Chevrolet", "model": "Silverado 1500", "body_style": "Crew Cab", "hours": 3.3, "source": "mitchell"},
    {"ri_code": "RI-HDLNR-SR", "year_start": 2019, "year_end": 2024, "make": "Chevrolet", "model": "Silverado 1500", "body_style": "Crew Cab", "hours": 4.6, "source": "mitchell"},
    {"ri_code": "RI-HDLT-L", "year_start": 2019, "year_end": 2024, "make": "Chevrolet", "model": "Silverado 1500", "hours": 0.6, "source": "mitchell"},
    {"ri_code": "RI-HDLT-R", "year_start": 2019, "year_end": 2024, "make": "Chevrolet", "model": "Silverado 1500", "hours": 0.6, "source": "mitchell"},
    {"ri_code": "RI-DTRM-LF", "year_start": 2019, "year_end": 2024, "make": "Chevrolet", "model": "Silverado 1500", "hours": 0.6, "source": "mitchell"},
    {"ri_code": "RI-DTRM-RF", "year_start": 2019, "year_end": 2024, "make": "Chevrolet", "model": "Silverado 1500", "hours": 0.6, "source": "mitchell"},
    {"ri_code": "RI-TAIL-L", "year_start": 2019, "year_end": 2024, "make": "Chevrolet", "model": "Silverado 1500", "hours": 0.4, "source": "mitchell"},
    {"ri_code": "RI-TAIL-R", "year_start": 2019, "year_end": 2024, "make": "Chevrolet", "model": "Silverado 1500", "hours": 0.4, "source": "mitchell"},

    # -------------------------------------------------------------------------
    # Ram 1500 (2019-2024)
    # -------------------------------------------------------------------------
    {"ri_code": "RI-HDLNR", "year_start": 2019, "year_end": 2024, "make": "Ram", "model": "1500", "body_style": "Crew Cab", "hours": 3.4, "source": "mitchell"},
    {"ri_code": "RI-HDLNR-SR", "year_start": 2019, "year_end": 2024, "make": "Ram", "model": "1500", "body_style": "Crew Cab", "hours": 4.7, "source": "mitchell"},
    {"ri_code": "RI-HDLT-L", "year_start": 2019, "year_end": 2024, "make": "Ram", "model": "1500", "hours": 0.5, "source": "mitchell"},
    {"ri_code": "RI-HDLT-R", "year_start": 2019, "year_end": 2024, "make": "Ram", "model": "1500", "hours": 0.5, "source": "mitchell"},
    {"ri_code": "RI-DTRM-LF", "year_start": 2019, "year_end": 2024, "make": "Ram", "model": "1500", "hours": 0.5, "source": "mitchell"},

    # -------------------------------------------------------------------------
    # Toyota Camry (2018-2024)
    # -------------------------------------------------------------------------
    {"ri_code": "RI-HDLNR", "year_start": 2018, "year_end": 2024, "make": "Toyota", "model": "Camry", "hours": 2.2, "source": "mitchell"},
    {"ri_code": "RI-HDLNR-SR", "year_start": 2018, "year_end": 2024, "make": "Toyota", "model": "Camry", "hours": 3.0, "source": "mitchell"},
    {"ri_code": "RI-HDLT-L", "year_start": 2018, "year_end": 2024, "make": "Toyota", "model": "Camry", "hours": 0.4, "source": "mitchell"},
    {"ri_code": "RI-HDLT-R", "year_start": 2018, "year_end": 2024, "make": "Toyota", "model": "Camry", "hours": 0.4, "source": "mitchell"},
    {"ri_code": "RI-DTRM-LF", "year_start": 2018, "year_end": 2024, "make": "Toyota", "model": "Camry", "hours": 0.4, "source": "mitchell"},
    {"ri_code": "RI-DTRM-RF", "year_start": 2018, "year_end": 2024, "make": "Toyota", "model": "Camry", "hours": 0.4, "source": "mitchell"},

    # -------------------------------------------------------------------------
    # Honda Accord (2018-2024)
    # -------------------------------------------------------------------------
    {"ri_code": "RI-HDLNR", "year_start": 2018, "year_end": 2024, "make": "Honda", "model": "Accord", "hours": 2.3, "source": "mitchell"},
    {"ri_code": "RI-HDLNR-SR", "year_start": 2018, "year_end": 2024, "make": "Honda", "model": "Accord", "hours": 3.2, "source": "mitchell"},
    {"ri_code": "RI-HDLT-L", "year_start": 2018, "year_end": 2024, "make": "Honda", "model": "Accord", "hours": 0.5, "source": "mitchell"},
    {"ri_code": "RI-HDLT-R", "year_start": 2018, "year_end": 2024, "make": "Honda", "model": "Accord", "hours": 0.5, "source": "mitchell"},

    # -------------------------------------------------------------------------
    # Toyota RAV4 (2019-2024)
    # -------------------------------------------------------------------------
    {"ri_code": "RI-HDLNR", "year_start": 2019, "year_end": 2024, "make": "Toyota", "model": "RAV4", "hours": 2.4, "source": "mitchell"},
    {"ri_code": "RI-HDLNR-SR", "year_start": 2019, "year_end": 2024, "make": "Toyota", "model": "RAV4", "hours": 3.3, "source": "mitchell"},
    {"ri_code": "RI-HDLT-L", "year_start": 2019, "year_end": 2024, "make": "Toyota", "model": "RAV4", "hours": 0.5, "source": "mitchell"},
    {"ri_code": "RI-HDLT-R", "year_start": 2019, "year_end": 2024, "make": "Toyota", "model": "RAV4", "hours": 0.5, "source": "mitchell"},
    {"ri_code": "RI-RRAIL-L", "year_start": 2019, "year_end": 2024, "make": "Toyota", "model": "RAV4", "hours": 0.5, "source": "oem"},
    {"ri_code": "RI-RRAIL-R", "year_start": 2019, "year_end": 2024, "make": "Toyota", "model": "RAV4", "hours": 0.5, "source": "oem"},

    # -------------------------------------------------------------------------
    # Honda CR-V (2017-2024)
    # -------------------------------------------------------------------------
    {"ri_code": "RI-HDLNR", "year_start": 2017, "year_end": 2024, "make": "Honda", "model": "CR-V", "hours": 2.5, "source": "mitchell"},
    {"ri_code": "RI-HDLNR-SR", "year_start": 2017, "year_end": 2024, "make": "Honda", "model": "CR-V", "hours": 3.4, "source": "mitchell"},
    {"ri_code": "RI-HDLT-L", "year_start": 2017, "year_end": 2024, "make": "Honda", "model": "CR-V", "hours": 0.5, "source": "mitchell"},
    {"ri_code": "RI-HDLT-R", "year_start": 2017, "year_end": 2024, "make": "Honda", "model": "CR-V", "hours": 0.5, "source": "mitchell"},

    # -------------------------------------------------------------------------
    # Ford Explorer (2020-2024)
    # -------------------------------------------------------------------------
    {"ri_code": "RI-HDLNR", "year_start": 2020, "year_end": 2024, "make": "Ford", "model": "Explorer", "hours": 2.8, "source": "mitchell"},
    {"ri_code": "RI-HDLNR-SR", "year_start": 2020, "year_end": 2024, "make": "Ford", "model": "Explorer", "hours": 3.8, "source": "mitchell"},
    {"ri_code": "RI-HDLT-L", "year_start": 2020, "year_end": 2024, "make": "Ford", "model": "Explorer", "hours": 0.6, "source": "mitchell"},
    {"ri_code": "RI-HDLT-R", "year_start": 2020, "year_end": 2024, "make": "Ford", "model": "Explorer", "hours": 0.6, "source": "mitchell"},

    # -------------------------------------------------------------------------
    # Chevrolet Equinox (2018-2024)
    # -------------------------------------------------------------------------
    {"ri_code": "RI-HDLNR", "year_start": 2018, "year_end": 2024, "make": "Chevrolet", "model": "Equinox", "hours": 2.3, "source": "mitchell"},
    {"ri_code": "RI-HDLNR-SR", "year_start": 2018, "year_end": 2024, "make": "Chevrolet", "model": "Equinox", "hours": 3.2, "source": "mitchell"},
    {"ri_code": "RI-HDLT-L", "year_start": 2018, "year_end": 2024, "make": "Chevrolet", "model": "Equinox", "hours": 0.5, "source": "mitchell"},
    {"ri_code": "RI-HDLT-R", "year_start": 2018, "year_end": 2024, "make": "Chevrolet", "model": "Equinox", "hours": 0.5, "source": "mitchell"},

    # -------------------------------------------------------------------------
    # Jeep Grand Cherokee (2022-2024) - New generation
    # -------------------------------------------------------------------------
    {"ri_code": "RI-HDLNR", "year_start": 2022, "year_end": 2024, "make": "Jeep", "model": "Grand Cherokee", "hours": 3.0, "source": "mitchell"},
    {"ri_code": "RI-HDLNR-SR", "year_start": 2022, "year_end": 2024, "make": "Jeep", "model": "Grand Cherokee", "hours": 4.2, "source": "mitchell"},
    {"ri_code": "RI-HDLT-L", "year_start": 2022, "year_end": 2024, "make": "Jeep", "model": "Grand Cherokee", "hours": 0.6, "source": "mitchell"},
    {"ri_code": "RI-HDLT-R", "year_start": 2022, "year_end": 2024, "make": "Jeep", "model": "Grand Cherokee", "hours": 0.6, "source": "mitchell"},
    {"ri_code": "RI-RRAIL-L", "year_start": 2022, "year_end": 2024, "make": "Jeep", "model": "Grand Cherokee", "hours": 0.6, "source": "oem"},
    {"ri_code": "RI-RRAIL-R", "year_start": 2022, "year_end": 2024, "make": "Jeep", "model": "Grand Cherokee", "hours": 0.6, "source": "oem"},
]


# =============================================================================
# LABOR RATES
# =============================================================================

DEFAULT_LABOR_RATES = [
    {"rate_type": "body", "hourly_rate": 52.00, "notes": "Standard body labor"},
    {"rate_type": "paint", "hourly_rate": 52.00, "notes": "Paint labor"},
    {"rate_type": "pdr", "hourly_rate": 75.00, "notes": "PDR labor rate"},
    {"rate_type": "mechanical", "hourly_rate": 85.00, "notes": "Mechanical labor"},
    {"rate_type": "electrical", "hourly_rate": 85.00, "notes": "Electrical labor"},
    {"rate_type": "glass", "hourly_rate": 50.00, "notes": "Glass labor"},
    {"rate_type": "structural", "hourly_rate": 60.00, "notes": "Frame/structural"},
    {"rate_type": "aluminum", "hourly_rate": 75.00, "notes": "Aluminum panel labor"},
]


# =============================================================================
# INSURANCE COMPANIES
# =============================================================================

INSURANCE_COMPANIES = [
    {"name": "State Farm", "code": "STATEFARM", "body_rate": 52.00, "pdr_rate": 75.00, "typical_review_days": 3, "supplement_friendly": True,
     "common_pushback_items": json.dumps(["headliner_over_3hrs", "blend_panels"])},
    {"name": "GEICO", "code": "GEICO", "body_rate": 50.00, "pdr_rate": 72.00, "typical_review_days": 5, "supplement_friendly": True,
     "common_pushback_items": json.dumps(["oversized_dents", "roof_rail_time"])},
    {"name": "Progressive", "code": "PROGRESSIVE", "body_rate": 52.00, "pdr_rate": 75.00, "typical_review_days": 4, "supplement_friendly": True,
     "common_pushback_items": json.dumps(["oem_parts", "excessive_dent_count"])},
    {"name": "Allstate", "code": "ALLSTATE", "body_rate": 52.00, "pdr_rate": 74.00, "typical_review_days": 4, "supplement_friendly": True,
     "common_pushback_items": json.dumps(["headliner_time", "pillar_trim"])},
    {"name": "USAA", "code": "USAA", "body_rate": 54.00, "pdr_rate": 78.00, "typical_review_days": 2, "supplement_friendly": True,
     "notes": "Generally the easiest to work with"},
    {"name": "Liberty Mutual", "code": "LIBERTY", "body_rate": 50.00, "pdr_rate": 72.00, "typical_review_days": 5, "supplement_friendly": False,
     "common_pushback_items": json.dumps(["all_ri_times", "dent_pricing"])},
    {"name": "Farmers", "code": "FARMERS", "body_rate": 52.00, "pdr_rate": 74.00, "typical_review_days": 4, "supplement_friendly": True},
    {"name": "Nationwide", "code": "NATIONWIDE", "body_rate": 52.00, "pdr_rate": 74.00, "typical_review_days": 4, "supplement_friendly": True},
    {"name": "American Family", "code": "AMFAM", "body_rate": 52.00, "pdr_rate": 75.00, "typical_review_days": 3, "supplement_friendly": True},
    {"name": "Travelers", "code": "TRAVELERS", "body_rate": 52.00, "pdr_rate": 74.00, "typical_review_days": 4, "supplement_friendly": True},
    {"name": "Hartford", "code": "HARTFORD", "body_rate": 52.00, "pdr_rate": 74.00, "typical_review_days": 5, "supplement_friendly": True},
    {"name": "Erie", "code": "ERIE", "body_rate": 52.00, "pdr_rate": 75.00, "typical_review_days": 3, "supplement_friendly": True},
    {"name": "Auto-Owners", "code": "AUTOOWNERS", "body_rate": 52.00, "pdr_rate": 75.00, "typical_review_days": 4, "supplement_friendly": True},
]


# =============================================================================
# SMART ALERT RULES
# =============================================================================

ALERT_RULES = [
    # Missing R/I Alerts
    {
        "name": "Missing Headliner R/I on Roof Damage",
        "trigger_conditions": json.dumps({"panel": "roof", "min_dents": 1, "missing_ri": ["RI-HDLNR", "RI-HDLNR-SR"]}),
        "alert_type": "missing_ri",
        "severity": "critical",
        "alert_message": "Roof has {dent_count} dents but no headliner R/I included. This is typically $150-300 in missed labor.",
        "suggested_action": "Add R/I Headliner",
        "priority": 10
    },
    {
        "name": "Missing Fender Liner on Fender Damage",
        "trigger_conditions": json.dumps({"panel": ["left_fender", "right_fender"], "min_dents": 5, "missing_ri": ["RI-FLIN-L", "RI-FLIN-R"]}),
        "alert_type": "missing_ri",
        "severity": "warning",
        "alert_message": "Fender has {dent_count} dents but no fender liner R/I. Usually needed for proper access.",
        "suggested_action": "Add R/I Fender Liner",
        "priority": 20
    },
    {
        "name": "Missing Headlight R/I on Fender Damage",
        "trigger_conditions": json.dumps({"panel": ["left_fender", "right_fender"], "min_dents": 8, "missing_ri": ["RI-HDLT-L", "RI-HDLT-R"]}),
        "alert_type": "missing_ri",
        "severity": "warning",
        "alert_message": "Fender damage typically requires headlight R/I for proper access.",
        "suggested_action": "Add R/I Headlight",
        "priority": 25
    },
    {
        "name": "Missing Door Trim on Door Damage",
        "trigger_conditions": json.dumps({"panel": ["left_front_door", "right_front_door", "left_rear_door", "right_rear_door"], "min_dents": 1, "missing_ri": ["RI-DTRM-LF", "RI-DTRM-RF", "RI-DTRM-LR", "RI-DTRM-RR"]}),
        "alert_type": "missing_ri",
        "severity": "warning",
        "alert_message": "Door has damage but no door trim panel R/I. This is needed for inside access.",
        "suggested_action": "Add R/I Door Trim Panel",
        "priority": 15
    },
    {
        "name": "Missing Antenna on Roof Damage",
        "trigger_conditions": json.dumps({"panel": "roof", "min_dents": 5, "missing_ri": ["RI-ANT"]}),
        "alert_type": "missing_ri",
        "severity": "info",
        "alert_message": "Roof damage but no antenna R/I. Most vehicles have shark fin antenna.",
        "suggested_action": "Add R/I Antenna",
        "priority": 50
    },

    # Consistency Alerts
    {
        "name": "Estimate Below Average",
        "trigger_conditions": json.dumps({"variance_below": 25}),
        "alert_type": "low_estimate",
        "severity": "warning",
        "alert_message": "This estimate is {variance}% below average for similar vehicles. Review for missed items.",
        "suggested_action": "Review estimate for missing R/I or underpriced panels",
        "priority": 30
    },
    {
        "name": "Estimate Significantly Below Average",
        "trigger_conditions": json.dumps({"variance_below": 40}),
        "alert_type": "low_estimate",
        "severity": "critical",
        "alert_message": "This estimate is {variance}% below average for similar vehicles. Strongly recommend review.",
        "suggested_action": "Review estimate immediately - likely missing items",
        "priority": 5
    },

    # Photo Alerts
    {
        "name": "Missing Panel Photos",
        "trigger_conditions": json.dumps({"damaged_panels_without_photos": True}),
        "alert_type": "photo_missing",
        "severity": "warning",
        "alert_message": "Panels with damage but no photos: {panels}. Insurance may push back without documentation.",
        "suggested_action": "Add damage photos for all affected panels",
        "priority": 35
    },
    {
        "name": "Missing VIN Photo",
        "trigger_conditions": json.dumps({"missing_photo_type": "vin"}),
        "alert_type": "photo_missing",
        "severity": "info",
        "alert_message": "No VIN photo included. Consider adding for complete documentation.",
        "suggested_action": "Add VIN plate photo",
        "priority": 60
    },

    # High Value Alerts
    {
        "name": "Large Estimate - Double Check",
        "trigger_conditions": json.dumps({"estimate_total_above": 5000}),
        "alert_type": "review_recommended",
        "severity": "info",
        "alert_message": "Estimate exceeds $5,000. Consider having a second person review before submission.",
        "priority": 70
    },
]


# =============================================================================
# PHOTO CHECKLIST
# =============================================================================

PHOTO_CHECKLIST = {
    "name": "Standard Hail Documentation",
    "description": "Complete photo documentation for hail damage estimates",
    "required_photos": json.dumps([
        {"name": "VIN Plate", "angle": "door_jamb", "required": True, "panel": None},
        {"name": "Odometer", "angle": "dash", "required": True, "panel": None},
        {"name": "License Plate", "angle": "rear", "required": True, "panel": None},
        {"name": "Full Front", "angle": "front_center", "required": True, "panel": None},
        {"name": "Full Rear", "angle": "rear_center", "required": True, "panel": None},
        {"name": "Full Left Side", "angle": "left_profile", "required": True, "panel": None},
        {"name": "Full Right Side", "angle": "right_profile", "required": True, "panel": None},
        {"name": "Hood Overview", "angle": "above_front", "required": True, "panel": "hood"},
        {"name": "Roof Overview", "angle": "above_center", "required": True, "panel": "roof"},
        {"name": "Trunk/Liftgate Overview", "angle": "above_rear", "required": True, "panel": "trunk"},
        {"name": "Hood Detail with Reflection", "angle": "reflection_board", "required": False, "panel": "hood"},
        {"name": "Roof Detail with Reflection", "angle": "reflection_board", "required": False, "panel": "roof"},
        {"name": "Left Fender", "angle": "above_side", "required": False, "panel": "left_fender"},
        {"name": "Right Fender", "angle": "above_side", "required": False, "panel": "right_fender"},
    ]),
    "is_default": True
}


# =============================================================================
# PUSHBACK JUSTIFICATIONS
# =============================================================================

PUSHBACK_JUSTIFICATIONS = [
    {
        "category": "ri_time",
        "trigger_item": "headliner",
        "title": "Headliner R/I Time Justification",
        "justification_text": """The headliner removal time is based on OEM procedures which require proper disconnection of all wiring (dome lights, sunroof controls, OnStar modules), removal of A/B/C pillar trim, sunvisors, and careful handling to prevent damage to the headliner material. Industry standard times (Mitchell, Motor, OEM) support this labor time.""",
        "oem_reference": "See manufacturer workshop manual - Interior Trim section",
        "mitchell_reference": "Mitchell collision estimating guide",
        "labor_time_source": "Mitchell/Motor labor times",
        "success_rate": 85.0
    },
    {
        "category": "ri_time",
        "trigger_item": "roof_rails",
        "title": "Roof Rail R/I Time Justification",
        "justification_text": """Roof rail removal requires proper tooling and technique to avoid damage to the roof panel. The fasteners are often hidden and require specific sequence for removal. Time includes accessing hidden fasteners, proper removal to avoid paint damage, and reinstallation with correct torque specifications.""",
        "oem_reference": "OEM workshop manual - Exterior Trim",
        "success_rate": 80.0
    },
    {
        "category": "pdr_price",
        "trigger_item": "oversized_dent",
        "title": "Oversized Dent Pricing Justification",
        "justification_text": """Oversized dents (larger than golf ball size) require significantly more time and skill to repair. They often require multiple pushing points, glue pulling techniques, and careful blending. Industry standard is to charge premium pricing for dents exceeding 1.5" diameter.""",
        "success_rate": 75.0
    },
    {
        "category": "pdr_price",
        "trigger_item": "body_line",
        "title": "Body Line Damage Pricing Justification",
        "justification_text": """Damage on or near body lines requires precision work to maintain the factory contour. This involves additional time for cross-checking, using specialty tips, and often requires working from multiple access points. Industry standard allows for premium pricing on body line repairs.""",
        "success_rate": 78.0
    },
]


# =============================================================================
# SEED FUNCTION
# =============================================================================

def seed_estimating_data(db_path: str = "data/pdr_crm.db"):
    """Populate all estimating seed data"""

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("\n" + "=" * 70)
    print("PDR PRO ESTIMATING SYSTEM - SEEDING DATA")
    print("=" * 70 + "\n")

    # -------------------------------------------------------------------------
    # R/I Operations
    # -------------------------------------------------------------------------
    print("Seeding R/I Operations...")
    ri_op_map = {}  # code -> id

    for op in RI_OPERATIONS:
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO ri_operations (name, code, category, default_hours, default_labor_type, notes)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (op["name"], op["code"], op["category"], op["default_hours"], op.get("labor_type", "body"), op.get("notes")))

            # Get the ID
            cursor.execute("SELECT id FROM ri_operations WHERE code = ?", (op["code"],))
            row = cursor.fetchone()
            if row:
                ri_op_map[op["code"]] = row[0]
        except Exception as e:
            print(f"  Warning: {op['code']} - {e}")

    print(f"[OK] Seeded {len(RI_OPERATIONS)} R/I operations")

    # -------------------------------------------------------------------------
    # Panel → R/I Associations
    # -------------------------------------------------------------------------
    print("\nSeeding Panel R/I Associations...")
    assoc_count = 0

    for assoc in PANEL_RI_ASSOCIATIONS:
        ri_op_id = ri_op_map.get(assoc["ri_code"])
        if not ri_op_id:
            print(f"  Warning: R/I code not found: {assoc['ri_code']}")
            continue

        try:
            cursor.execute("""
                INSERT OR IGNORE INTO panel_ri_associations
                (panel_name, ri_operation_id, is_default_selected, min_dent_count, access_trigger, condition_notes, vehicle_condition, priority)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                assoc["panel"],
                ri_op_id,
                1 if assoc.get("default", False) else 0,
                assoc.get("min_dents", 0),
                assoc.get("access"),
                assoc.get("notes"),
                assoc.get("vehicle_condition"),
                assoc.get("priority", 100)
            ))
            assoc_count += 1
        except Exception as e:
            print(f"  Warning: {assoc['panel']}/{assoc['ri_code']} - {e}")

    print(f"[OK] Seeded {assoc_count} panel associations")

    # -------------------------------------------------------------------------
    # Vehicle R/I Times
    # -------------------------------------------------------------------------
    print("\nSeeding Vehicle-Specific R/I Times...")
    time_count = 0

    for time in VEHICLE_RI_TIMES:
        ri_op_id = ri_op_map.get(time["ri_code"])
        if not ri_op_id:
            continue

        try:
            cursor.execute("""
                INSERT OR IGNORE INTO ri_times
                (ri_operation_id, year_start, year_end, make, model, body_style, labor_hours, labor_type, source, confidence_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                ri_op_id,
                time["year_start"],
                time["year_end"],
                time["make"],
                time["model"],
                time.get("body_style"),
                time["hours"],
                time.get("labor_type", "body"),
                time.get("source", "mitchell"),
                75  # Default confidence
            ))
            time_count += 1
        except Exception as e:
            print(f"  Warning: {time['make']} {time['model']} - {e}")

    print(f"[OK] Seeded {time_count} vehicle-specific R/I times")

    # -------------------------------------------------------------------------
    # Labor Rates
    # -------------------------------------------------------------------------
    print("\nSeeding Labor Rates...")

    for rate in DEFAULT_LABOR_RATES:
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO labor_rates (rate_type, hourly_rate, notes, effective_date, is_active)
                VALUES (?, ?, ?, date('now'), 1)
            """, (rate["rate_type"], rate["hourly_rate"], rate.get("notes")))
        except Exception as e:
            print(f"  Warning: {rate['rate_type']} - {e}")

    print(f"[OK] Seeded {len(DEFAULT_LABOR_RATES)} labor rates")

    # -------------------------------------------------------------------------
    # Insurance Companies
    # -------------------------------------------------------------------------
    print("\nSeeding Insurance Companies...")

    for ins in INSURANCE_COMPANIES:
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO insurance_companies
                (name, code, body_rate, pdr_rate, typical_review_days, supplement_friendly, common_pushback_items, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                ins["name"],
                ins["code"],
                ins.get("body_rate"),
                ins.get("pdr_rate"),
                ins.get("typical_review_days"),
                1 if ins.get("supplement_friendly", True) else 0,
                ins.get("common_pushback_items"),
                ins.get("notes")
            ))
        except Exception as e:
            print(f"  Warning: {ins['name']} - {e}")

    print(f"[OK] Seeded {len(INSURANCE_COMPANIES)} insurance companies")

    # -------------------------------------------------------------------------
    # Alert Rules
    # -------------------------------------------------------------------------
    print("\nSeeding Smart Alert Rules...")

    for rule in ALERT_RULES:
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO estimate_alert_rules
                (name, trigger_conditions, alert_type, severity, alert_message, suggested_action, priority, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1)
            """, (
                rule["name"],
                rule["trigger_conditions"],
                rule["alert_type"],
                rule["severity"],
                rule["alert_message"],
                rule.get("suggested_action"),
                rule.get("priority", 100)
            ))
        except Exception as e:
            print(f"  Warning: {rule['name']} - {e}")

    print(f"[OK] Seeded {len(ALERT_RULES)} alert rules")

    # -------------------------------------------------------------------------
    # Photo Checklist
    # -------------------------------------------------------------------------
    print("\nSeeding Photo Checklist...")

    try:
        cursor.execute("""
            INSERT OR IGNORE INTO photo_checklists
            (name, description, required_photos, is_default, is_active)
            VALUES (?, ?, ?, 1, 1)
        """, (
            PHOTO_CHECKLIST["name"],
            PHOTO_CHECKLIST["description"],
            PHOTO_CHECKLIST["required_photos"]
        ))
        print("[OK] Seeded default photo checklist")
    except Exception as e:
        print(f"  Warning: Photo checklist - {e}")

    # -------------------------------------------------------------------------
    # Pushback Justifications
    # -------------------------------------------------------------------------
    print("\nSeeding Pushback Justifications...")

    for just in PUSHBACK_JUSTIFICATIONS:
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO pushback_justifications
                (category, trigger_item, title, justification_text, oem_reference, mitchell_reference, labor_time_source, success_rate)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                just["category"],
                just["trigger_item"],
                just["title"],
                just["justification_text"],
                just.get("oem_reference"),
                just.get("mitchell_reference"),
                just.get("labor_time_source"),
                just.get("success_rate")
            ))
        except Exception as e:
            print(f"  Warning: {just['title']} - {e}")

    print(f"[OK] Seeded {len(PUSHBACK_JUSTIFICATIONS)} pushback justifications")

    conn.commit()
    conn.close()

    print("\n" + "=" * 70)
    print("ESTIMATING DATA SEEDING COMPLETE")
    print("=" * 70 + "\n")


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    db_path = sys.argv[1] if len(sys.argv) > 1 else "data/pdr_crm.db"

    # First create schema
    from src.crm.models.estimating_schema import EstimatingSchema
    EstimatingSchema.create_all_tables(db_path)
    EstimatingSchema.add_estimate_insurance_fields(db_path)

    # Then seed data
    seed_estimating_data(db_path)

    print("Done! Run test_estimating_system.py to verify.")
