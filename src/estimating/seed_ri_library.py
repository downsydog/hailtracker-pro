"""
R&I Library Seed Data

This seeds the ri_library table with standard PDR R&I operations.
Each operation has min/typical/max time ranges with scope bullet justifications.
"""

import psycopg2
import json
import os

PG_CONFIG = {
    "host": os.environ.get('PG_HOST', '127.0.0.1'),
    "port": int(os.environ.get('PG_PORT', 5432)),
    "database": os.environ.get('PG_DATABASE', 'hailtracker_master'),
    "user": os.environ.get('PG_USER', 'hailtracker'),
    "password": os.environ.get('PG_PASSWORD', 'hailtracker_dev_2024')
}

# Standard tier multipliers
TIER_MULTIPLIERS = {
    "economy": 0.85,
    "standard": 1.0,
    "premium": 1.15,
    "luxury": 1.35,
    "ev_adas": 1.25
}

# R&I Operations Library
RI_OPERATIONS = [
    # INTERIOR ACCESS
    {
        "operation_code": "RI_HEADLINER_PARTIAL",
        "name": "R&I Headliner (Partial Drop)",
        "category": "interior_access",
        "base_time_min": 0.8,
        "base_time_typical": 1.2,
        "base_time_max": 1.8,
        "scope_min": [
            "Release headliner retainers at repair area",
            "Support headliner during repair",
            "Reinstall retainers and verify fit"
        ],
        "scope_typical": [
            "Release headliner retainers at repair area",
            "Remove overhead console/dome light if obstructing",
            "Remove assist handles as needed",
            "Support headliner during repair",
            "Reinstall all components",
            "Verify fit and function"
        ],
        "scope_max": [
            "All typical scope items",
            "Remove A-pillar upper trims",
            "Disconnect wiring harnesses",
            "Additional fitment verification"
        ],
        "tier_multipliers": {"economy": 0.85, "standard": 1.0, "premium": 1.15, "luxury": 1.35, "ev_adas": 1.25}
    },
    {
        "operation_code": "RI_HEADLINER_FULL",
        "name": "R&I Headliner (Full Removal)",
        "category": "interior_access",
        "base_time_min": 1.5,
        "base_time_typical": 2.2,
        "base_time_max": 3.0,
        "scope_min": [
            "Remove sun visors (L/R)",
            "Remove dome light assembly",
            "Remove assist handles (front)",
            "Release all retainers/clips",
            "Disconnect basic wiring",
            "Remove headliner from vehicle",
            "Reinstall and verify fit"
        ],
        "scope_typical": [
            "Remove sun visors (L/R)",
            "Remove overhead console/dome light assembly",
            "Remove all assist handles (4)",
            "Remove upper seat belt anchor covers",
            "Remove A/B/C pillar upper trims as required",
            "Release all retainers and clips",
            "Disconnect all wiring harnesses attached to headliner",
            "Carefully remove headliner from vehicle",
            "Bag and tag all hardware",
            "Protect interior surfaces",
            "Reinstall all components",
            "Verify fit, function, and no rattles"
        ],
        "scope_max": [
            "All typical scope items",
            "Remove additional overhead modules (SOS/mic/camera)",
            "Remove D-pillar trim (SUV/wagon)",
            "Detach extra harness routing and anchors",
            "Remove rear header trim",
            "Additional rattle check and quality verification"
        ],
        "tier_multipliers": {"economy": 0.85, "standard": 1.0, "premium": 1.15, "luxury": 1.4, "ev_adas": 1.3}
    },
    {
        "operation_code": "RI_OVERHEAD_CONSOLE",
        "name": "R&I Overhead Console",
        "category": "interior_access",
        "base_time_min": 0.15,
        "base_time_typical": 0.25,
        "base_time_max": 0.4,
        "scope_min": [
            "Release console retainers",
            "Lower console",
            "Reinstall"
        ],
        "scope_typical": [
            "Release console retainers",
            "Disconnect wiring connector(s)",
            "Remove console from headliner",
            "Reinstall and verify function"
        ],
        "scope_max": [
            "All typical items",
            "Multiple wiring harnesses",
            "Integrated garage door/compass module"
        ],
        "tier_multipliers": {"economy": 0.85, "standard": 1.0, "premium": 1.2, "luxury": 1.4, "ev_adas": 1.3}
    },
    {
        "operation_code": "RI_SUN_VISORS",
        "name": "R&I Sun Visors (Pair)",
        "category": "interior_access",
        "base_time_min": 0.1,
        "base_time_typical": 0.2,
        "base_time_max": 0.3,
        "scope_min": [
            "Remove visor screws/clips (2)",
            "Reinstall"
        ],
        "scope_typical": [
            "Remove visor mounting screws (L/R)",
            "Disconnect illuminated visor wiring if equipped",
            "Remove visors",
            "Reinstall and verify function"
        ],
        "scope_max": [
            "Typical scope",
            "Integrated mirror/light wiring",
            "Vanity light function check"
        ],
        "tier_multipliers": {"economy": 0.9, "standard": 1.0, "premium": 1.15, "luxury": 1.25, "ev_adas": 1.1}
    },
    {
        "operation_code": "RI_ASSIST_HANDLES",
        "name": "R&I Assist Handles (Set)",
        "category": "interior_access",
        "base_time_min": 0.15,
        "base_time_typical": 0.25,
        "base_time_max": 0.35,
        "scope_min": [
            "Remove 2 handles",
            "Reinstall"
        ],
        "scope_typical": [
            "Remove all assist handles (typically 4)",
            "Remove trim covers",
            "Reinstall all and verify secure"
        ],
        "scope_max": [
            "Remove all handles including integrated coat hooks",
            "Bag/tag hardware",
            "Verify no rattles"
        ],
        "tier_multipliers": {"economy": 0.9, "standard": 1.0, "premium": 1.1, "luxury": 1.2, "ev_adas": 1.0}
    },
    {
        "operation_code": "RI_PILLAR_TRIM_A_UPPER",
        "name": "R&I A-Pillar Upper Trim (Pair)",
        "category": "interior_access",
        "base_time_min": 0.2,
        "base_time_typical": 0.35,
        "base_time_max": 0.5,
        "scope_min": [
            "Release trim clips",
            "Remove trims",
            "Reinstall"
        ],
        "scope_typical": [
            "Release trim retaining clips",
            "Disconnect any wiring (tweeter speakers)",
            "Remove A-pillar trims (L/R)",
            "Reinstall and verify fit"
        ],
        "scope_max": [
            "Typical scope",
            "Integrated airbag considerations",
            "Multiple speaker connections",
            "Weatherstrip interference"
        ],
        "tier_multipliers": {"economy": 0.85, "standard": 1.0, "premium": 1.2, "luxury": 1.35, "ev_adas": 1.2}
    },
    {
        "operation_code": "RI_PILLAR_TRIM_B_UPPER",
        "name": "R&I B-Pillar Upper Trim (Pair)",
        "category": "interior_access",
        "base_time_min": 0.2,
        "base_time_typical": 0.3,
        "base_time_max": 0.45,
        "scope_min": [
            "Release trim clips",
            "Remove trims",
            "Reinstall"
        ],
        "scope_typical": [
            "Release trim retaining clips",
            "Remove seat belt upper guide if integrated",
            "Remove B-pillar trims (L/R)",
            "Reinstall and verify fit"
        ],
        "scope_max": [
            "Typical scope",
            "Integrated seat belt pretensioner covers",
            "Curtain airbag trim considerations"
        ],
        "tier_multipliers": {"economy": 0.85, "standard": 1.0, "premium": 1.15, "luxury": 1.3, "ev_adas": 1.15}
    },
    {
        "operation_code": "RI_PILLAR_TRIM_C_UPPER",
        "name": "R&I C-Pillar Upper Trim (Pair)",
        "category": "interior_access",
        "base_time_min": 0.2,
        "base_time_typical": 0.3,
        "base_time_max": 0.45,
        "scope_min": [
            "Release trim clips",
            "Remove trims",
            "Reinstall"
        ],
        "scope_typical": [
            "Release trim retaining clips",
            "Remove C-pillar trims (L/R)",
            "Reinstall and verify secure fit"
        ],
        "scope_max": [
            "Typical scope",
            "Curtain airbag considerations",
            "Rear speaker wiring"
        ],
        "tier_multipliers": {"economy": 0.85, "standard": 1.0, "premium": 1.15, "luxury": 1.3, "ev_adas": 1.15}
    },
    {
        "operation_code": "RI_SEATBELT_UPPER",
        "name": "R&I Upper Seat Belt Anchors (Pair)",
        "category": "interior_access",
        "base_time_min": 0.15,
        "base_time_typical": 0.25,
        "base_time_max": 0.35,
        "scope_min": [
            "Remove anchor covers",
            "Loosen anchors",
            "Reinstall and torque"
        ],
        "scope_typical": [
            "Remove trim covers",
            "Loosen/remove upper seat belt anchor bolts (L/R)",
            "Position belts away from work area",
            "Reinstall anchors to specification",
            "Verify retractor function"
        ],
        "scope_max": [
            "Typical scope",
            "Pretensioner considerations",
            "Multiple anchor points"
        ],
        "tier_multipliers": {"economy": 0.9, "standard": 1.0, "premium": 1.1, "luxury": 1.2, "ev_adas": 1.1}
    },
    # DOOR/SIDE ACCESS
    {
        "operation_code": "RI_DOOR_TRIM_FRONT",
        "name": "R&I Front Door Trim Panel",
        "category": "door_access",
        "base_time_min": 0.3,
        "base_time_typical": 0.5,
        "base_time_max": 0.75,
        "scope_min": [
            "Remove door panel retainers",
            "Disconnect window switch",
            "Remove panel",
            "Reinstall"
        ],
        "scope_typical": [
            "Remove door panel retainers and screws",
            "Disconnect window/lock switch connectors",
            "Disconnect door handle linkage if needed",
            "Remove vapor barrier as needed",
            "Remove door trim panel",
            "Reinstall panel, connectors, and verify all functions"
        ],
        "scope_max": [
            "All typical items",
            "Integrated speaker removal",
            "Puddle light disconnect",
            "Power mirror switch",
            "Memory seat switches"
        ],
        "tier_multipliers": {"economy": 0.85, "standard": 1.0, "premium": 1.2, "luxury": 1.4, "ev_adas": 1.2}
    },
    {
        "operation_code": "RI_DOOR_TRIM_REAR",
        "name": "R&I Rear Door Trim Panel",
        "category": "door_access",
        "base_time_min": 0.25,
        "base_time_typical": 0.4,
        "base_time_max": 0.6,
        "scope_min": [
            "Remove door panel retainers",
            "Disconnect switches",
            "Remove panel",
            "Reinstall"
        ],
        "scope_typical": [
            "Remove door panel retainers and screws",
            "Disconnect window/lock switch connectors",
            "Remove vapor barrier as needed",
            "Remove door trim panel",
            "Reinstall and verify all functions"
        ],
        "scope_max": [
            "All typical items",
            "Integrated speaker",
            "Rear window shade mechanism",
            "Child lock access"
        ],
        "tier_multipliers": {"economy": 0.85, "standard": 1.0, "premium": 1.15, "luxury": 1.35, "ev_adas": 1.15}
    },
    {
        "operation_code": "RI_VAPOR_BARRIER",
        "name": "R&I Vapor Barrier (Detach/Reseal)",
        "category": "door_access",
        "base_time_min": 0.1,
        "base_time_typical": 0.2,
        "base_time_max": 0.3,
        "scope_min": [
            "Peel back barrier",
            "Reseal"
        ],
        "scope_typical": [
            "Carefully detach vapor barrier adhesive",
            "Position for inner panel access",
            "Reseal barrier ensuring watertight seal"
        ],
        "scope_max": [
            "Full barrier removal",
            "Replace damaged sections",
            "Apply new sealer as needed"
        ],
        "tier_multipliers": {"economy": 0.9, "standard": 1.0, "premium": 1.1, "luxury": 1.2, "ev_adas": 1.0}
    },
    {
        "operation_code": "RI_QUARTER_TRIM",
        "name": "R&I Quarter Interior Trim Panel",
        "category": "door_access",
        "base_time_min": 0.3,
        "base_time_typical": 0.5,
        "base_time_max": 0.8,
        "scope_min": [
            "Remove trim retainers",
            "Remove panel",
            "Reinstall"
        ],
        "scope_typical": [
            "Remove trim panel retainers",
            "Disconnect any wiring",
            "Remove seat belt lower anchor if needed",
            "Remove quarter trim panel",
            "Reinstall all components"
        ],
        "scope_max": [
            "Typical scope",
            "Rear seat removal for access",
            "Speaker disconnect",
            "Subwoofer access"
        ],
        "tier_multipliers": {"economy": 0.85, "standard": 1.0, "premium": 1.2, "luxury": 1.4, "ev_adas": 1.2}
    },
    # EXTERIOR PANELS
    {
        "operation_code": "RI_HOOD_INSULATION",
        "name": "R&I Hood Insulation Pad",
        "category": "exterior_panel",
        "base_time_min": 0.1,
        "base_time_typical": 0.15,
        "base_time_max": 0.25,
        "scope_min": [
            "Release retainers",
            "Remove pad",
            "Reinstall"
        ],
        "scope_typical": [
            "Release insulation pad retainers",
            "Remove pad from hood",
            "Store safely",
            "Reinstall and verify secure"
        ],
        "scope_max": [
            "Typical scope",
            "Multiple pad sections",
            "Integrated sound deadening"
        ],
        "tier_multipliers": {"economy": 0.9, "standard": 1.0, "premium": 1.1, "luxury": 1.15, "ev_adas": 1.0}
    },
    {
        "operation_code": "RI_ROOF_MOLDING",
        "name": "R&I Roof Side Molding",
        "category": "exterior_panel",
        "base_time_min": 0.2,
        "base_time_typical": 0.35,
        "base_time_max": 0.5,
        "scope_min": [
            "Release molding clips",
            "Remove molding",
            "Reinstall"
        ],
        "scope_typical": [
            "Release molding retaining clips",
            "Carefully remove roof side molding",
            "Clean adhesive residue",
            "Reinstall with proper alignment"
        ],
        "scope_max": [
            "Typical scope",
            "Adhesive replacement",
            "Chrome/painted finish handling"
        ],
        "tier_multipliers": {"economy": 0.9, "standard": 1.0, "premium": 1.15, "luxury": 1.25, "ev_adas": 1.1}
    },
    {
        "operation_code": "RI_DECK_LID_TRIM",
        "name": "R&I Deck Lid/Trunk Lid Trim Panel",
        "category": "exterior_panel",
        "base_time_min": 0.15,
        "base_time_typical": 0.25,
        "base_time_max": 0.4,
        "scope_min": [
            "Remove retainers",
            "Remove panel",
            "Reinstall"
        ],
        "scope_typical": [
            "Remove trim panel retainers",
            "Disconnect license plate light if integrated",
            "Remove interior trim panel",
            "Reinstall and verify"
        ],
        "scope_max": [
            "Typical scope",
            "Rear camera wiring",
            "Power trunk components"
        ],
        "tier_multipliers": {"economy": 0.9, "standard": 1.0, "premium": 1.15, "luxury": 1.3, "ev_adas": 1.2}
    },
    # LINERS
    {
        "operation_code": "RI_FENDER_LINER_FRONT",
        "name": "R&I Front Fender Liner",
        "category": "liner",
        "base_time_min": 0.15,
        "base_time_typical": 0.25,
        "base_time_max": 0.4,
        "scope_min": [
            "Remove liner fasteners",
            "Drop liner",
            "Reinstall"
        ],
        "scope_typical": [
            "Remove fender liner fasteners/push pins",
            "Remove liner for inner fender access",
            "Reinstall liner",
            "Verify all fasteners secure"
        ],
        "scope_max": [
            "Typical scope",
            "Wheel removal for access",
            "Air dam interference"
        ],
        "tier_multipliers": {"economy": 0.9, "standard": 1.0, "premium": 1.1, "luxury": 1.2, "ev_adas": 1.1}
    },
    {
        "operation_code": "RI_FENDER_LINER_REAR",
        "name": "R&I Rear Fender/Wheelhouse Liner",
        "category": "liner",
        "base_time_min": 0.15,
        "base_time_typical": 0.25,
        "base_time_max": 0.4,
        "scope_min": [
            "Remove liner fasteners",
            "Drop liner",
            "Reinstall"
        ],
        "scope_typical": [
            "Remove wheelhouse liner fasteners",
            "Remove liner for quarter panel access",
            "Reinstall and verify secure"
        ],
        "scope_max": [
            "Typical scope",
            "Integrated splash shield",
            "Exhaust routing consideration"
        ],
        "tier_multipliers": {"economy": 0.9, "standard": 1.0, "premium": 1.1, "luxury": 1.2, "ev_adas": 1.1}
    },
    # LAMPS
    {
        "operation_code": "RI_HEADLAMP",
        "name": "R&I Headlamp Assembly",
        "category": "lamp",
        "base_time_min": 0.2,
        "base_time_typical": 0.35,
        "base_time_max": 0.6,
        "scope_min": [
            "Remove fasteners",
            "Disconnect bulb connectors",
            "Remove lamp",
            "Reinstall"
        ],
        "scope_typical": [
            "Remove headlamp fasteners",
            "Disconnect all electrical connectors",
            "Remove headlamp assembly",
            "Reinstall and verify aim"
        ],
        "scope_max": [
            "Typical scope",
            "HID/LED ballast handling",
            "Auto-leveling motor",
            "Bumper cover loosening for access"
        ],
        "tier_multipliers": {"economy": 0.85, "standard": 1.0, "premium": 1.25, "luxury": 1.5, "ev_adas": 1.3}
    },
    {
        "operation_code": "RI_TAIL_LAMP",
        "name": "R&I Tail Lamp Assembly",
        "category": "lamp",
        "base_time_min": 0.15,
        "base_time_typical": 0.25,
        "base_time_max": 0.4,
        "scope_min": [
            "Remove fasteners",
            "Disconnect connector",
            "Remove lamp",
            "Reinstall"
        ],
        "scope_typical": [
            "Remove tail lamp fasteners",
            "Access through trunk/cargo area",
            "Disconnect electrical connector",
            "Remove lamp assembly",
            "Reinstall and verify function"
        ],
        "scope_max": [
            "Typical scope",
            "LED module handling",
            "Sequential turn signal verify"
        ],
        "tier_multipliers": {"economy": 0.9, "standard": 1.0, "premium": 1.15, "luxury": 1.3, "ev_adas": 1.15}
    },
    {
        "operation_code": "RI_THIRD_BRAKE_LAMP",
        "name": "R&I High Mount Stop Lamp (CHMSL)",
        "category": "lamp",
        "base_time_min": 0.1,
        "base_time_typical": 0.2,
        "base_time_max": 0.3,
        "scope_min": [
            "Remove fasteners",
            "Disconnect",
            "Remove",
            "Reinstall"
        ],
        "scope_typical": [
            "Remove CHMSL mounting fasteners",
            "Disconnect electrical connector",
            "Remove lamp from spoiler/deck",
            "Reinstall and verify function"
        ],
        "scope_max": [
            "Typical scope",
            "Integrated camera",
            "Spoiler removal required"
        ],
        "tier_multipliers": {"economy": 0.9, "standard": 1.0, "premium": 1.2, "luxury": 1.35, "ev_adas": 1.25}
    },
    # BUMPERS
    {
        "operation_code": "RI_BUMPER_FRONT_PARTIAL",
        "name": "R&I Front Bumper Cover (Partial/Loosen)",
        "category": "bumper",
        "base_time_min": 0.2,
        "base_time_typical": 0.35,
        "base_time_max": 0.5,
        "scope_min": [
            "Remove upper fasteners",
            "Pull bumper for access",
            "Resecure"
        ],
        "scope_typical": [
            "Remove upper bumper fasteners",
            "Remove fender liner attachments to bumper",
            "Pull bumper cover away from fenders for access",
            "Resecure all fasteners"
        ],
        "scope_max": [
            "Typical scope",
            "Fog lamp disconnect",
            "Sensor/camera clearance"
        ],
        "tier_multipliers": {"economy": 0.85, "standard": 1.0, "premium": 1.2, "luxury": 1.35, "ev_adas": 1.25}
    },
    {
        "operation_code": "RI_BUMPER_REAR_PARTIAL",
        "name": "R&I Rear Bumper Cover (Partial/Loosen)",
        "category": "bumper",
        "base_time_min": 0.2,
        "base_time_typical": 0.3,
        "base_time_max": 0.45,
        "scope_min": [
            "Remove upper fasteners",
            "Pull bumper for access",
            "Resecure"
        ],
        "scope_typical": [
            "Remove upper bumper fasteners",
            "Remove wheelhouse to bumper fasteners",
            "Pull bumper cover for access",
            "Resecure all fasteners"
        ],
        "scope_max": [
            "Typical scope",
            "Sensor disconnect",
            "Exhaust tip clearance"
        ],
        "tier_multipliers": {"economy": 0.85, "standard": 1.0, "premium": 1.15, "luxury": 1.3, "ev_adas": 1.25}
    },
    # SPECIAL ACCESS
    {
        "operation_code": "RI_SEAT_FRONT",
        "name": "R&I Front Seat",
        "category": "special_access",
        "base_time_min": 0.3,
        "base_time_typical": 0.5,
        "base_time_max": 0.75,
        "scope_min": [
            "Remove seat bolts",
            "Disconnect wiring",
            "Remove seat",
            "Reinstall"
        ],
        "scope_typical": [
            "Disconnect battery (SRS precaution)",
            "Remove seat mounting bolts",
            "Disconnect all electrical connectors",
            "Remove seat from vehicle",
            "Reinstall and verify all functions",
            "Clear any fault codes"
        ],
        "scope_max": [
            "Typical scope",
            "Heated/cooled seat wiring",
            "Memory seat module",
            "Occupant detection system"
        ],
        "tier_multipliers": {"economy": 0.85, "standard": 1.0, "premium": 1.3, "luxury": 1.5, "ev_adas": 1.3}
    },
    {
        "operation_code": "RI_SEAT_REAR",
        "name": "R&I Rear Seat (Bench/Bottom)",
        "category": "special_access",
        "base_time_min": 0.15,
        "base_time_typical": 0.25,
        "base_time_max": 0.4,
        "scope_min": [
            "Release seat latches",
            "Remove seat cushion",
            "Reinstall"
        ],
        "scope_typical": [
            "Release rear seat bottom latches",
            "Remove seat bottom",
            "Fold/remove seat back if needed",
            "Reinstall and verify latches secure"
        ],
        "scope_max": [
            "Typical scope",
            "Heated seat wiring",
            "Child seat anchor access"
        ],
        "tier_multipliers": {"economy": 0.9, "standard": 1.0, "premium": 1.15, "luxury": 1.3, "ev_adas": 1.15}
    }
]

# Vehicle tier classifications
VEHICLE_TIERS = [
    # Economy
    {"make": "Kia", "model": "Rio", "tier": "economy"},
    {"make": "Kia", "model": "Soul", "tier": "economy"},
    {"make": "Kia", "model": "Forte", "tier": "economy"},
    {"make": "Hyundai", "model": "Accent", "tier": "economy"},
    {"make": "Hyundai", "model": "Elantra", "tier": "economy"},
    {"make": "Nissan", "model": "Versa", "tier": "economy"},
    {"make": "Nissan", "model": "Sentra", "tier": "economy"},
    {"make": "Toyota", "model": "Yaris", "tier": "economy"},
    {"make": "Honda", "model": "Fit", "tier": "economy"},
    {"make": "Chevrolet", "model": "Spark", "tier": "economy"},
    {"make": "Chevrolet", "model": "Sonic", "tier": "economy"},
    {"make": "Ford", "model": "Fiesta", "tier": "economy"},

    # Standard
    {"make": "Toyota", "model": "Camry", "tier": "standard"},
    {"make": "Toyota", "model": "RAV4", "tier": "standard"},
    {"make": "Toyota", "model": "Corolla", "tier": "standard"},
    {"make": "Honda", "model": "Accord", "tier": "standard"},
    {"make": "Honda", "model": "CR-V", "tier": "standard"},
    {"make": "Honda", "model": "Civic", "tier": "standard"},
    {"make": "Ford", "model": "Fusion", "tier": "standard"},
    {"make": "Ford", "model": "Escape", "tier": "standard"},
    {"make": "Ford", "model": "F-150", "tier": "standard"},
    {"make": "Chevrolet", "model": "Malibu", "tier": "standard"},
    {"make": "Chevrolet", "model": "Equinox", "tier": "standard"},
    {"make": "Chevrolet", "model": "Silverado", "tier": "standard"},
    {"make": "Nissan", "model": "Altima", "tier": "standard"},
    {"make": "Nissan", "model": "Rogue", "tier": "standard"},
    {"make": "Hyundai", "model": "Sonata", "tier": "standard"},
    {"make": "Hyundai", "model": "Tucson", "tier": "standard"},
    {"make": "Hyundai", "model": "Santa Fe", "tier": "standard"},
    {"make": "Kia", "model": "Optima", "tier": "standard"},
    {"make": "Kia", "model": "Sportage", "tier": "standard"},
    {"make": "Kia", "model": "Sorento", "tier": "standard"},

    # Premium
    {"make": "Toyota", "model": "Avalon", "tier": "premium"},
    {"make": "Toyota", "model": "Highlander", "tier": "premium"},
    {"make": "Honda", "model": "Pilot", "tier": "premium"},
    {"make": "Honda", "model": "Odyssey", "tier": "premium"},
    {"make": "Mazda", "model": "Mazda6", "tier": "premium"},
    {"make": "Mazda", "model": "CX-5", "tier": "premium"},
    {"make": "Mazda", "model": "CX-9", "tier": "premium"},
    {"make": "Subaru", "model": "Outback", "tier": "premium"},
    {"make": "Subaru", "model": "Ascent", "tier": "premium"},
    {"make": "Volkswagen", "model": "Passat", "tier": "premium"},
    {"make": "Volkswagen", "model": "Atlas", "tier": "premium"},
    {"make": "Volkswagen", "model": "Tiguan", "tier": "premium"},
    {"make": "Buick", "model": None, "tier": "premium", "notes": "All models"},
    {"make": "Chrysler", "model": "300", "tier": "premium"},
    {"make": "Chrysler", "model": "Pacifica", "tier": "premium"},

    # Luxury (entire makes)
    {"make": "BMW", "model": None, "tier": "luxury", "notes": "All models"},
    {"make": "Mercedes-Benz", "model": None, "tier": "luxury", "notes": "All models"},
    {"make": "Audi", "model": None, "tier": "luxury", "notes": "All models"},
    {"make": "Lexus", "model": None, "tier": "luxury", "notes": "All models"},
    {"make": "Infiniti", "model": None, "tier": "luxury", "notes": "All models"},
    {"make": "Acura", "model": None, "tier": "luxury", "notes": "All models"},
    {"make": "Genesis", "model": None, "tier": "luxury", "notes": "All models"},
    {"make": "Cadillac", "model": None, "tier": "luxury", "notes": "All models"},
    {"make": "Lincoln", "model": None, "tier": "luxury", "notes": "All models"},
    {"make": "Porsche", "model": None, "tier": "luxury", "notes": "All models"},
    {"make": "Land Rover", "model": None, "tier": "luxury", "notes": "All models"},
    {"make": "Jaguar", "model": None, "tier": "luxury", "notes": "All models"},
    {"make": "Volvo", "model": None, "tier": "luxury", "notes": "All models"},

    # EV/ADAS
    {"make": "Tesla", "model": None, "tier": "ev_adas", "notes": "All models"},
    {"make": "Rivian", "model": None, "tier": "ev_adas", "notes": "All models"},
    {"make": "Lucid", "model": None, "tier": "ev_adas", "notes": "All models"},
    {"make": "Polestar", "model": None, "tier": "ev_adas", "notes": "All models"},
]


def seed_ri_library():
    """Seed the R&I library with standard operations."""
    conn = psycopg2.connect(**PG_CONFIG)
    cur = conn.cursor()

    # Clear existing system entries (tenant_id IS NULL)
    cur.execute("DELETE FROM ri_library WHERE tenant_id IS NULL")

    for op in RI_OPERATIONS:
        cur.execute("""
            INSERT INTO ri_library (
                tenant_id, operation_code, name, category,
                base_time_min, base_time_typical, base_time_max,
                scope_min, scope_typical, scope_max,
                tier_multipliers, common_adders, is_active
            ) VALUES (
                NULL, %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s,
                %s, %s, TRUE
            )
        """, (
            op["operation_code"],
            op["name"],
            op["category"],
            op["base_time_min"],
            op["base_time_typical"],
            op["base_time_max"],
            json.dumps(op["scope_min"]),
            json.dumps(op["scope_typical"]),
            json.dumps(op["scope_max"]),
            json.dumps(op["tier_multipliers"]),
            json.dumps(op.get("common_adders"))
        ))

    conn.commit()
    print(f"Seeded {len(RI_OPERATIONS)} R&I operations")

    # Verify
    cur.execute("SELECT COUNT(*) FROM ri_library WHERE tenant_id IS NULL")
    count = cur.fetchone()[0]
    print(f"Verified: {count} system R&I operations in database")

    conn.close()


def seed_vehicle_tiers():
    """Seed the vehicle tier classifications."""
    conn = psycopg2.connect(**PG_CONFIG)
    cur = conn.cursor()

    # Clear existing entries
    cur.execute("DELETE FROM vehicle_tiers")

    for vt in VEHICLE_TIERS:
        cur.execute("""
            INSERT INTO vehicle_tiers (make, model, tier, notes)
            VALUES (%s, %s, %s, %s)
        """, (
            vt["make"],
            vt.get("model"),
            vt["tier"],
            vt.get("notes")
        ))

    conn.commit()
    print(f"Seeded {len(VEHICLE_TIERS)} vehicle tier classifications")

    # Verify tier counts
    cur.execute("SELECT tier, COUNT(*) FROM vehicle_tiers GROUP BY tier ORDER BY tier")
    for row in cur.fetchall():
        print(f"  {row[0]}: {row[1]} entries")

    conn.close()


def get_vehicle_tier(make: str, model: str = None) -> str:
    """
    Get the tier for a vehicle make/model.
    Returns 'standard' if no match found.
    """
    conn = psycopg2.connect(**PG_CONFIG)
    cur = conn.cursor()

    # Try exact make+model match first
    if model:
        cur.execute("""
            SELECT tier FROM vehicle_tiers
            WHERE LOWER(make) = LOWER(%s) AND LOWER(model) = LOWER(%s)
            LIMIT 1
        """, (make, model))
        result = cur.fetchone()
        if result:
            conn.close()
            return result[0]

    # Try make-only match (model IS NULL means "all models")
    cur.execute("""
        SELECT tier FROM vehicle_tiers
        WHERE LOWER(make) = LOWER(%s) AND model IS NULL
        LIMIT 1
    """, (make,))
    result = cur.fetchone()

    conn.close()
    return result[0] if result else "standard"


if __name__ == "__main__":
    print("Seeding R&I Library...")
    seed_ri_library()

    print("\nSeeding Vehicle Tiers...")
    seed_vehicle_tiers()

    print("\nTesting tier lookup...")
    test_vehicles = [
        ("Toyota", "Camry"),
        ("BMW", "X5"),
        ("Tesla", "Model 3"),
        ("Kia", "Rio"),
        ("Unknown", "Car")
    ]
    for make, model in test_vehicles:
        tier = get_vehicle_tier(make, model)
        print(f"  {make} {model} -> {tier}")

    print("\nDone!")
