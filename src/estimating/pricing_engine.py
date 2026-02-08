"""
PDR Pricing Engine
Zone-based dent pricing with panel difficulty and material modifiers.
Enhanced with vehicle tier-aware R&I time calculations and scope bullets.
Faster than Mobile Tech RX with auto R&I suggestions and defensible supplements.
"""

from typing import Dict, List, Optional, Tuple, Any
from decimal import Decimal, ROUND_HALF_UP
import json

# Tier multipliers for R&I operations
TIER_MULTIPLIERS = {
    "economy": 0.85,
    "standard": 1.0,
    "premium": 1.15,
    "luxury": 1.35,
    "ev_adas": 1.25
}

# Default pricing configuration - Enhanced with coin sizes and depth
DEFAULT_PRICING_CONFIG = {
    # Enhanced dent sizes (coin-based for industry standard)
    "base_prices": {
        # Legacy sizes (for backward compatibility)
        "small": 50,
        "medium": 75,
        "large": 100,
        "xlarge": 150,
        # Enhanced coin-based sizes
        "dime": 45,
        "nickel": 55,
        "quarter": 70,
        "half_dollar": 95,
        "silver_dollar": 125,
        "oversized": 175
    },
    # Depth multipliers (how deep the dent is)
    "depth_multipliers": {
        "shallow": 1.0,
        "medium": 1.25,
        "deep": 1.6,
        "severe": 2.0
    },
    "zone_multipliers": {
        "center": 1.0,
        "edge": 1.4,
        "crease": 1.6,
        "body_line": 1.8
    },
    "panel_difficulty": {
        "hood": 1.0,
        "roof": 1.2,
        "driver_door": 1.0,
        "passenger_door": 1.0,
        "driver_rear_door": 1.1,
        "passenger_rear_door": 1.1,
        "driver_fender": 1.1,
        "passenger_fender": 1.1,
        "driver_quarter": 1.3,
        "passenger_quarter": 1.3,
        "trunk": 1.0,
        "tailgate": 1.1,
        "left_door": 1.0,
        "right_door": 1.0,
        "left_rear_door": 1.1,
        "right_rear_door": 1.1,
        "left_fender": 1.1,
        "right_fender": 1.1,
        "left_quarter": 1.3,
        "right_quarter": 1.3
    },
    "material_modifiers": {
        "steel": 1.0,
        "aluminum": 1.5,
        "high_strength_steel": 1.3,
        "carbon_fiber": 2.0
    },
    "rin_items": {
        "door_handle_removal": {"price": 25, "time": 0.25},
        "door_trim_panel": {"price": 35, "time": 0.33},
        "headliner_drop": {"price": 150, "time": 1.5},
        "headliner_partial": {"price": 75, "time": 0.75},
        "fender_liner": {"price": 20, "time": 0.17},
        "taillight_removal": {"price": 30, "time": 0.25},
        "mirror_removal": {"price": 25, "time": 0.25},
        "antenna_removal": {"price": 20, "time": 0.17},
        "molding_removal": {"price": 15, "time": 0.17},
        "emblem_removal": {"price": 10, "time": 0.08},
        "wiper_arm_removal": {"price": 15, "time": 0.17},
        "cowl_panel": {"price": 25, "time": 0.25},
        "roof_rack_removal": {"price": 40, "time": 0.5},
        "sunroof_molding": {"price": 30, "time": 0.33},
        "quarter_glass_molding": {"price": 25, "time": 0.25},
        "bedliner_removal": {"price": 50, "time": 0.5},
        "tailgate_trim": {"price": 30, "time": 0.33}
    },
    "panel_rin_associations": {
        "hood": ["wiper_arm_removal", "cowl_panel"],
        "roof": ["headliner_drop", "sunroof_molding", "roof_rack_removal", "antenna_removal"],
        "driver_door": ["door_handle_removal", "door_trim_panel", "mirror_removal"],
        "passenger_door": ["door_handle_removal", "door_trim_panel", "mirror_removal"],
        "driver_rear_door": ["door_handle_removal", "door_trim_panel"],
        "passenger_rear_door": ["door_handle_removal", "door_trim_panel"],
        "driver_fender": ["fender_liner", "emblem_removal"],
        "passenger_fender": ["fender_liner", "emblem_removal"],
        "driver_quarter": ["quarter_glass_molding", "taillight_removal"],
        "passenger_quarter": ["quarter_glass_molding", "taillight_removal"],
        "trunk": ["emblem_removal", "taillight_removal"],
        "tailgate": ["tailgate_trim", "emblem_removal", "taillight_removal"]
    },
    "zone_rin_triggers": {
        "edge": ["door_handle_removal", "mirror_removal", "molding_removal"],
        "crease": ["door_trim_panel"]
    }
}


class PricingEngine:
    """
    PDR Pricing Engine with zone-based multipliers.

    Key Features:
    - Per-dent pricing based on size + zone
    - Panel difficulty multipliers
    - Material modifiers (aluminum, HSS)
    - Auto R&I suggestions based on zone
    """

    def __init__(self, config: Optional[Dict] = None):
        """Initialize with pricing config (uses default if not provided)."""
        self.config = config or DEFAULT_PRICING_CONFIG

    def calculate_dent_price(
        self,
        size: str,
        zone: str,
        depth: str = "medium",
        panel_difficulty: float = 1.0,
        material_modifier: float = 1.0
    ) -> Tuple[Decimal, Dict]:
        """
        Calculate price for a single dent with enhanced size/depth options.

        Args:
            size: dime, nickel, quarter, half_dollar, silver_dollar, oversized
                  (also supports legacy: small, medium, large, xlarge)
            zone: center, edge, crease, body_line
            depth: shallow, medium, deep, severe
            panel_difficulty: Panel difficulty multiplier (from config)
            material_modifier: Material modifier (steel=1.0, aluminum=1.5, etc.)

        Returns:
            Tuple of (final_price, breakdown_dict)
        """
        # Get base price for size
        base_prices = self.config.get("base_prices", DEFAULT_PRICING_CONFIG["base_prices"])
        base_price = Decimal(str(base_prices.get(size, 75)))

        # Get zone multiplier
        zone_multipliers = self.config.get("zone_multipliers", DEFAULT_PRICING_CONFIG["zone_multipliers"])
        zone_mult = Decimal(str(zone_multipliers.get(zone, 1.0)))

        # Get depth multiplier
        depth_multipliers = self.config.get("depth_multipliers", DEFAULT_PRICING_CONFIG["depth_multipliers"])
        depth_mult = Decimal(str(depth_multipliers.get(depth, 1.0)))

        # Apply multipliers
        panel_mult = Decimal(str(panel_difficulty))
        material_mult = Decimal(str(material_modifier))

        final_price = base_price * zone_mult * depth_mult * panel_mult * material_mult
        final_price = final_price.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        # Determine complexity from zone and depth
        complexity_score = 0
        if zone in ["crease", "body_line"]:
            complexity_score += 2
        elif zone == "edge":
            complexity_score += 1
        if depth in ["deep", "severe"]:
            complexity_score += 2
        elif depth == "medium":
            complexity_score += 1

        complexity = "low" if complexity_score <= 1 else ("medium" if complexity_score <= 2 else "high")

        # Build reason string
        reasons = []
        if zone != "center":
            reasons.append(f"{zone} zone")
        if depth != "shallow":
            reasons.append(f"{depth} depth")

        breakdown = {
            "base_price": float(base_price),
            "zone_multiplier": float(zone_mult),
            "depth_multiplier": float(depth_mult),
            "panel_difficulty": float(panel_mult),
            "material_modifier": float(material_mult),
            "complexity": complexity,
            "reason": ", ".join(reasons) if reasons else None
        }

        return final_price, breakdown

    def get_panel_difficulty(self, panel_name: str) -> float:
        """Get difficulty multiplier for a panel."""
        panel_difficulty = self.config.get("panel_difficulty", DEFAULT_PRICING_CONFIG["panel_difficulty"])
        return panel_difficulty.get(panel_name.lower().replace(" ", "_"), 1.0)

    def get_material_modifier(self, material: str) -> float:
        """Get modifier for material type."""
        material_modifiers = self.config.get("material_modifiers", DEFAULT_PRICING_CONFIG["material_modifiers"])
        return material_modifiers.get(material.lower().replace(" ", "_"), 1.0)

    def suggest_rin_for_zone(
        self,
        panel: str,
        zone: str,
        existing_dents: List[Dict] = None
    ) -> List[Dict]:
        """
        Suggest R&I items needed for accessing a zone on a panel.

        Args:
            panel: Panel name (e.g., "driver_door")
            zone: Zone being worked (center, edge, crease)
            existing_dents: List of existing dents on this panel

        Returns:
            List of suggested R&I items with prices and times
        """
        suggestions = []
        rin_items = self.config.get("rin_items", DEFAULT_PRICING_CONFIG["rin_items"])

        # Get panel-based R&I associations
        panel_associations = self.config.get("panel_rin_associations", DEFAULT_PRICING_CONFIG["panel_rin_associations"])
        panel_key = panel.lower().replace(" ", "_")

        # Always suggest panel-specific R&I items if working edges or creases
        if zone in ["edge", "crease"]:
            for item_name in panel_associations.get(panel_key, []):
                if item_name in rin_items:
                    item = rin_items[item_name]
                    suggestions.append({
                        "item_name": item_name,
                        "display_name": item_name.replace("_", " ").title(),
                        "price": item["price"],
                        "time_hours": item["time"],
                        "reason": f"Required for {zone} access on {panel}",
                        "auto_suggested": True
                    })

        # Add zone-specific triggers
        zone_triggers = self.config.get("zone_rin_triggers", DEFAULT_PRICING_CONFIG["zone_rin_triggers"])
        for item_name in zone_triggers.get(zone, []):
            # Don't duplicate
            if not any(s["item_name"] == item_name for s in suggestions):
                if item_name in rin_items:
                    item = rin_items[item_name]
                    suggestions.append({
                        "item_name": item_name,
                        "display_name": item_name.replace("_", " ").title(),
                        "price": item["price"],
                        "time_hours": item["time"],
                        "reason": f"Commonly needed for {zone} zone work",
                        "auto_suggested": True
                    })

        return suggestions

    def calculate_panel_total(
        self,
        dents: List[Dict],
        panel_name: str,
        material: str = "steel"
    ) -> Tuple[Decimal, List[Dict]]:
        """
        Calculate total price for all dents on a panel.

        Args:
            dents: List of dent dicts with 'size', 'zone', and optionally 'depth' keys
            panel_name: Name of the panel
            material: Material type (steel, aluminum, high_strength_steel)

        Returns:
            Tuple of (total_price, list of priced dents)
        """
        panel_difficulty = self.get_panel_difficulty(panel_name)
        material_modifier = self.get_material_modifier(material)

        priced_dents = []
        total = Decimal('0')

        for dent in dents:
            price, breakdown = self.calculate_dent_price(
                size=dent.get('size', 'medium'),
                zone=dent.get('zone', 'center'),
                depth=dent.get('depth', 'medium'),
                panel_difficulty=panel_difficulty,
                material_modifier=material_modifier
            )

            priced_dent = {
                **dent,
                "base_price": breakdown["base_price"],
                "final_price": float(price),
                "multiplier": (breakdown["zone_multiplier"] * breakdown["depth_multiplier"] *
                              breakdown["panel_difficulty"] * breakdown["material_modifier"]),
                "complexity": breakdown["complexity"],
                "reason": breakdown["reason"]
            }
            priced_dents.append(priced_dent)
            total += price

        return total, priced_dents

    def calculate_ri_time(
        self,
        operation_code: str,
        vehicle_tier: str = "standard",
        scope_level: str = "typical",
        ri_library: Optional[Dict] = None
    ) -> Tuple[float, Dict]:
        """
        Calculate R&I time with vehicle tier adjustment.

        Args:
            operation_code: R&I operation code (e.g., RI_HEADLINER_FULL)
            vehicle_tier: economy, standard, premium, luxury, ev_adas
            scope_level: min, typical, max (determines base time used)
            ri_library: Optional dict with R&I operation details from database

        Returns:
            Tuple of (adjusted_time_hours, calculation_details)
        """
        if not ri_library:
            # Return sensible defaults if no library data
            return 0.5, {"error": "No R&I library data provided"}

        # Get base time based on scope level
        if scope_level == "min":
            base_time = ri_library.get("base_time_min", 0.25)
        elif scope_level == "max":
            base_time = ri_library.get("base_time_max", 1.0)
        else:
            base_time = ri_library.get("base_time_typical", 0.5)

        # Get tier multiplier (from operation or global)
        tier_mults = ri_library.get("tier_multipliers", {})
        if isinstance(tier_mults, str):
            tier_mults = json.loads(tier_mults)
        tier_mult = tier_mults.get(vehicle_tier, TIER_MULTIPLIERS.get(vehicle_tier, 1.0))

        # Calculate adjusted time
        adjusted_time = base_time * tier_mult

        details = {
            "operation_code": operation_code,
            "operation_name": ri_library.get("name", operation_code),
            "base_time": base_time,
            "scope_level": scope_level,
            "vehicle_tier": vehicle_tier,
            "tier_multiplier": tier_mult,
            "adjusted_time": round(adjusted_time, 2)
        }

        return round(adjusted_time, 2), details

    def generate_ri_scope_text(
        self,
        ri_library: Dict,
        scope_level: str = "typical",
        vehicle_tier: str = "standard",
        include_time: bool = True
    ) -> str:
        """
        Generate defensible scope text for insurance supplements.

        Args:
            ri_library: Dict with R&I operation details from database
            scope_level: min, typical, max
            vehicle_tier: Vehicle tier for time calculation
            include_time: Whether to include time in output

        Returns:
            Formatted scope text for supplement narrative
        """
        operation_name = ri_library.get("name", "R&I Operation")

        # Get scope bullets for the level
        if scope_level == "min":
            scope_key = "scope_min"
        elif scope_level == "max":
            scope_key = "scope_max"
        else:
            scope_key = "scope_typical"

        scope_bullets = ri_library.get(scope_key, [])
        if isinstance(scope_bullets, str):
            scope_bullets = json.loads(scope_bullets)

        # Calculate time
        adjusted_time, time_details = self.calculate_ri_time(
            operation_code=ri_library.get("operation_code", ""),
            vehicle_tier=vehicle_tier,
            scope_level=scope_level,
            ri_library=ri_library
        )

        # Build narrative
        lines = [f"{operation_name}"]

        if include_time:
            lines.append(f"Estimated time: {adjusted_time} hours ({vehicle_tier} tier vehicle)")

        if scope_bullets:
            lines.append("Scope of work:")
            for bullet in scope_bullets:
                lines.append(f"  • {bullet}")

        return "\n".join(lines)

    def suggest_ri_for_panel(
        self,
        panel_name: str,
        zones_worked: List[str],
        ri_library_items: Optional[List[Dict]] = None
    ) -> List[Dict]:
        """
        Suggest R&I operations based on panel and zones being worked.

        Args:
            panel_name: Name of the panel being worked
            zones_worked: List of zones with dents (center, edge, crease, body_line)
            ri_library_items: Optional list of R&I operations from database

        Returns:
            List of suggested R&I operations with justifications
        """
        suggestions = []

        # Panel to R&I operation mappings
        PANEL_RI_MAP = {
            "hood": ["RI_HOOD_INSULATION"],
            "roof": ["RI_HEADLINER_PARTIAL", "RI_OVERHEAD_CONSOLE", "RI_SUN_VISORS"],
            "driver_door": ["RI_DOOR_TRIM_FRONT", "RI_VAPOR_BARRIER"],
            "passenger_door": ["RI_DOOR_TRIM_FRONT", "RI_VAPOR_BARRIER"],
            "driver_rear_door": ["RI_DOOR_TRIM_REAR", "RI_VAPOR_BARRIER"],
            "passenger_rear_door": ["RI_DOOR_TRIM_REAR", "RI_VAPOR_BARRIER"],
            "driver_fender": ["RI_FENDER_LINER_FRONT", "RI_HEADLAMP"],
            "passenger_fender": ["RI_FENDER_LINER_FRONT", "RI_HEADLAMP"],
            "driver_quarter": ["RI_QUARTER_TRIM", "RI_TAIL_LAMP", "RI_FENDER_LINER_REAR"],
            "passenger_quarter": ["RI_QUARTER_TRIM", "RI_TAIL_LAMP", "RI_FENDER_LINER_REAR"],
            "trunk": ["RI_DECK_LID_TRIM", "RI_TAIL_LAMP", "RI_THIRD_BRAKE_LAMP"],
            "tailgate": ["RI_DECK_LID_TRIM", "RI_TAIL_LAMP", "RI_THIRD_BRAKE_LAMP"],
        }

        # Zone-based additional R&I triggers
        ZONE_RI_TRIGGERS = {
            "edge": {
                "roof": ["RI_PILLAR_TRIM_A_UPPER", "RI_ROOF_MOLDING"],
                "hood": ["RI_BUMPER_FRONT_PARTIAL"],
            },
            "crease": {
                "roof": ["RI_HEADLINER_FULL", "RI_ASSIST_HANDLES"],
            },
            "body_line": {
                "driver_door": ["RI_DOOR_TRIM_FRONT"],
                "passenger_door": ["RI_DOOR_TRIM_FRONT"],
            }
        }

        panel_key = panel_name.lower().replace(" ", "_")

        # Get base R&I suggestions for this panel
        needed_ops = set(PANEL_RI_MAP.get(panel_key, []))

        # Add zone-specific R&I operations
        for zone in zones_worked:
            zone_triggers = ZONE_RI_TRIGGERS.get(zone, {})
            panel_zone_ops = zone_triggers.get(panel_key, [])
            needed_ops.update(panel_zone_ops)

        # If working creases or body lines on roof, need full headliner
        if panel_key == "roof" and any(z in ["crease", "body_line"] for z in zones_worked):
            needed_ops.discard("RI_HEADLINER_PARTIAL")
            needed_ops.add("RI_HEADLINER_FULL")

        # Build suggestions with justifications
        for op_code in needed_ops:
            # Find matching library item if provided
            lib_item = None
            if ri_library_items:
                for item in ri_library_items:
                    if item.get("operation_code") == op_code:
                        lib_item = item
                        break

            justification = f"Required for {panel_name} access"
            if any(z in zones_worked for z in ["edge", "crease", "body_line"]):
                justification = f"Required for {', '.join(zones_worked)} zone access on {panel_name}"

            suggestion = {
                "operation_code": op_code,
                "name": lib_item.get("name", op_code) if lib_item else op_code,
                "category": lib_item.get("category", "general") if lib_item else "general",
                "base_time_typical": lib_item.get("base_time_typical", 0.5) if lib_item else 0.5,
                "justification": justification,
                "auto_suggested": True,
                "zones_triggering": zones_worked
            }
            suggestions.append(suggestion)

        return suggestions


def calculate_estimate_total(db_conn, estimate_id: int) -> Dict:
    """
    Calculate complete estimate total from database.

    Args:
        db_conn: PostgreSQL connection
        estimate_id: ID of the estimate

    Returns:
        Dict with totals breakdown
    """
    cursor = db_conn.cursor()

    # Get all panels for this estimate
    cursor.execute("""
        SELECT ep.id, ep.panel_name, ep.panel_difficulty, ep.material_modifier
        FROM estimate_panels ep
        WHERE ep.estimate_id = %s
    """, (estimate_id,))
    panels = cursor.fetchall()

    dent_total = Decimal('0')
    rin_total = Decimal('0')
    panel_totals = []

    engine = PricingEngine()

    for panel in panels:
        panel_id, panel_name, panel_difficulty, material_modifier = panel

        # Get dents for this panel
        cursor.execute("""
            SELECT id, zone, size, type, final_price
            FROM dents
            WHERE panel_id = %s
        """, (panel_id,))
        dents = cursor.fetchall()

        panel_dent_total = sum(Decimal(str(d[4] or 0)) for d in dents)

        # Get R&I items for this panel
        cursor.execute("""
            SELECT id, item_name, price
            FROM rin_items
            WHERE panel_id = %s
        """, (panel_id,))
        rin_items = cursor.fetchall()

        panel_rin_total = sum(Decimal(str(r[2] or 0)) for r in rin_items)

        panel_totals.append({
            "panel_id": panel_id,
            "panel_name": panel_name,
            "dent_count": len(dents),
            "dent_total": float(panel_dent_total),
            "rin_count": len(rin_items),
            "rin_total": float(panel_rin_total),
            "panel_total": float(panel_dent_total + panel_rin_total)
        })

        dent_total += panel_dent_total
        rin_total += panel_rin_total

    grand_total = dent_total + rin_total

    # Update estimate total in database
    cursor.execute("""
        UPDATE pdr_estimates
        SET total_price = %s, updated_at = NOW()
        WHERE id = %s
    """, (float(grand_total), estimate_id))
    db_conn.commit()

    return {
        "estimate_id": estimate_id,
        "dent_total": float(dent_total),
        "rin_total": float(rin_total),
        "grand_total": float(grand_total),
        "panel_count": len(panels),
        "panels": panel_totals
    }


def get_default_config() -> Dict:
    """Return the default pricing configuration."""
    return DEFAULT_PRICING_CONFIG.copy()


def create_pricing_profile(db_conn, tenant_id: int, name: str, config: Dict = None, is_default: bool = False) -> int:
    """
    Create a new pricing profile for a tenant.

    Args:
        db_conn: PostgreSQL connection
        tenant_id: Tenant ID
        name: Profile name
        config: Pricing config (uses default if not provided)
        is_default: Whether this is the default profile

    Returns:
        Profile ID
    """
    if config is None:
        config = DEFAULT_PRICING_CONFIG

    cursor = db_conn.cursor()

    # If setting as default, unset other defaults for this tenant
    if is_default:
        cursor.execute("""
            UPDATE pricing_profiles SET is_default = FALSE WHERE tenant_id = %s
        """, (tenant_id,))

    cursor.execute("""
        INSERT INTO pricing_profiles (tenant_id, name, is_default, config)
        VALUES (%s, %s, %s, %s)
        RETURNING id
    """, (tenant_id, name, is_default, json.dumps(config)))

    profile_id = cursor.fetchone()[0]

    # Create initial version
    cursor.execute("""
        INSERT INTO pricing_profile_versions (profile_id, version, config)
        VALUES (%s, 1, %s)
    """, (profile_id, json.dumps(config)))

    db_conn.commit()

    return profile_id


def get_tenant_pricing_config(db_conn, tenant_id: int) -> Dict:
    """
    Get the default pricing config for a tenant.
    Falls back to system default if no profile exists.

    Args:
        db_conn: PostgreSQL connection
        tenant_id: Tenant ID

    Returns:
        Pricing configuration dict
    """
    cursor = db_conn.cursor()

    cursor.execute("""
        SELECT config FROM pricing_profiles
        WHERE tenant_id = %s AND is_default = TRUE
        LIMIT 1
    """, (tenant_id,))

    result = cursor.fetchone()
    if result:
        return result[0] if isinstance(result[0], dict) else json.loads(result[0])

    return DEFAULT_PRICING_CONFIG


def get_ri_library_items(db_conn, tenant_id: Optional[int] = None, category: Optional[str] = None) -> List[Dict]:
    """
    Get R&I library items from database.

    Args:
        db_conn: PostgreSQL connection
        tenant_id: Tenant ID (None for system items only)
        category: Optional category filter

    Returns:
        List of R&I operation dicts
    """
    cursor = db_conn.cursor()

    query = """
        SELECT id, operation_code, name, category,
               base_time_min, base_time_typical, base_time_max,
               scope_min, scope_typical, scope_max,
               tier_multipliers, common_adders
        FROM ri_library
        WHERE is_active = TRUE
          AND (tenant_id IS NULL OR tenant_id = %s)
    """
    params = [tenant_id]

    if category:
        query += " AND category = %s"
        params.append(category)

    query += " ORDER BY category, name"

    cursor.execute(query, params)
    rows = cursor.fetchall()

    items = []
    for row in rows:
        item = {
            "id": row[0],
            "operation_code": row[1],
            "name": row[2],
            "category": row[3],
            "base_time_min": float(row[4]) if row[4] else 0.25,
            "base_time_typical": float(row[5]) if row[5] else 0.5,
            "base_time_max": float(row[6]) if row[6] else 1.0,
            "scope_min": row[7] if isinstance(row[7], list) else json.loads(row[7] or "[]"),
            "scope_typical": row[8] if isinstance(row[8], list) else json.loads(row[8] or "[]"),
            "scope_max": row[9] if isinstance(row[9], list) else json.loads(row[9] or "[]"),
            "tier_multipliers": row[10] if isinstance(row[10], dict) else json.loads(row[10] or "{}"),
            "common_adders": row[11] if isinstance(row[11], list) else json.loads(row[11] or "[]") if row[11] else []
        }
        items.append(item)

    return items


def get_ri_operation(db_conn, operation_code: str, tenant_id: Optional[int] = None) -> Optional[Dict]:
    """
    Get a single R&I operation by code.

    Args:
        db_conn: PostgreSQL connection
        operation_code: The operation code (e.g., RI_HEADLINER_FULL)
        tenant_id: Tenant ID (None for system items)

    Returns:
        R&I operation dict or None
    """
    items = get_ri_library_items(db_conn, tenant_id)
    for item in items:
        if item["operation_code"] == operation_code:
            return item
    return None


def get_vehicle_tier(db_conn, make: str, model: Optional[str] = None) -> str:
    """
    Get the vehicle tier classification from database.

    Args:
        db_conn: PostgreSQL connection
        make: Vehicle make
        model: Vehicle model (optional)

    Returns:
        Tier string: economy, standard, premium, luxury, or ev_adas
    """
    cursor = db_conn.cursor()

    # Try exact make+model match first
    if model:
        cursor.execute("""
            SELECT tier FROM vehicle_tiers
            WHERE LOWER(make) = LOWER(%s) AND LOWER(model) = LOWER(%s)
            LIMIT 1
        """, (make, model))
        result = cursor.fetchone()
        if result:
            return result[0]

    # Try make-only match (model IS NULL means "all models")
    cursor.execute("""
        SELECT tier FROM vehicle_tiers
        WHERE LOWER(make) = LOWER(%s) AND model IS NULL
        LIMIT 1
    """, (make,))
    result = cursor.fetchone()

    return result[0] if result else "standard"


# Quick test
if __name__ == "__main__":
    engine = PricingEngine()

    # Test enhanced dent pricing with depth
    print("=== Enhanced Dent Pricing Tests ===")
    print("\nCoin-based sizes with depth multipliers:")
    for size in ["dime", "nickel", "quarter", "half_dollar", "silver_dollar", "oversized"]:
        for depth in ["shallow", "medium", "deep"]:
            price, breakdown = engine.calculate_dent_price(size, "center", depth)
            print(f"{size:14} {depth:8} center = ${price:>7.2f}")

    print("\n=== Zone + Depth Combined ===")
    for zone in ["center", "edge", "crease", "body_line"]:
        for depth in ["shallow", "deep"]:
            price, breakdown = engine.calculate_dent_price("quarter", zone, depth)
            print(f"quarter {zone:10} {depth:8} = ${price:>7.2f} (complexity: {breakdown['complexity']})")

    print("\n=== Legacy Size Support ===")
    for size in ["small", "medium", "large", "xlarge"]:
        price, breakdown = engine.calculate_dent_price(size, "center")
        print(f"{size:8} center = ${price:>7.2f}")

    print("\n=== Panel R&I Suggestions ===")
    # Test the new suggest_ri_for_panel function
    suggestions = engine.suggest_ri_for_panel("roof", ["edge", "crease"])
    for s in suggestions:
        print(f"  {s['name']}: {s['base_time_typical']}hrs - {s['justification']}")

    print("\n=== R&I Time Calculation ===")
    # Simulate R&I library data
    mock_ri_library = {
        "operation_code": "RI_HEADLINER_FULL",
        "name": "R&I Headliner (Full Removal)",
        "base_time_min": 1.5,
        "base_time_typical": 2.2,
        "base_time_max": 3.0,
        "tier_multipliers": {"economy": 0.85, "standard": 1.0, "premium": 1.15, "luxury": 1.4, "ev_adas": 1.3}
    }

    for tier in ["economy", "standard", "premium", "luxury", "ev_adas"]:
        time, details = engine.calculate_ri_time("RI_HEADLINER_FULL", tier, "typical", mock_ri_library)
        print(f"  {tier:10}: {time:.2f} hrs (base: {details['base_time']}, mult: {details['tier_multiplier']})")

    print("\n=== Scope Text Generation ===")
    mock_ri_library["scope_typical"] = [
        "Remove sun visors (L/R)",
        "Remove overhead console/dome light assembly",
        "Remove all assist handles (4)",
        "Disconnect all wiring harnesses attached to headliner",
        "Carefully remove headliner from vehicle",
        "Reinstall all components"
    ]
    scope_text = engine.generate_ri_scope_text(mock_ri_library, "typical", "luxury", include_time=True)
    print(scope_text)

    print("\n=== Panel Total with Depth ===")
    dents = [
        {"size": "quarter", "zone": "center", "depth": "shallow"},
        {"size": "quarter", "zone": "center", "depth": "medium"},
        {"size": "nickel", "zone": "edge", "depth": "deep"},
        {"size": "half_dollar", "zone": "crease", "depth": "severe"},
    ]
    total, priced = engine.calculate_panel_total(dents, "hood")
    print(f"Hood with {len(dents)} dents: ${total}")
    for d in priced:
        print(f"  {d['size']} {d['zone']} {d.get('depth', 'medium')}: ${d['final_price']:.2f} ({d['complexity']})")
