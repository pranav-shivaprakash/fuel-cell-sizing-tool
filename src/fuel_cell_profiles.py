"""
Fuel Cell Profiles
--------------------
Real component specifications extracted from manufacturer datasheets,
for use with fuel_cell_sizing.py. Each profile bundles the specific
power and efficiency figures needed by size_full_system(), plus rated
power for checking whether a sizing result is actually achievable
with that specific product.

Sources:
  - Horizon FCS-UL500 Fuel Cell Stack User Manual, V3.1
  - Intelligent Energy S800 Fuel Cell Power System User Manual, rev 1.1
"""

FUEL_CELL_PROFILES = {
    "horizon_fcs_ul500": {
        "name": "Horizon FCS-UL500",
        "rated_power_w": 500,
        "mass_kg": 1.750,  # measured: stack+housing+blowers+valves (1332g) + controller+cables+LCD+dissipation plate (346g) + tubes/screws/fittings/H2 connectors (72g)
        "specific_power_w_per_kg": 500 / 1.750,
        "system_efficiency": 0.40,  # datasheet: stack efficiency >= 40%
        "bop_fraction_of_stack": 0.0,  # tubes/fittings/H2 connectors already included in mass_kg above -- don't double-count
        "voltage_range_v": (22.5, 44.1),
        "notes": "Air-cooled, self-humidifying PEM stack. 45 cells. Mass includes full accessory kit (tubes, fittings, H2 connectors) -- comparable in scope to IE S800's balance-of-plant allowance.",
    },
    "ie_s800": {
        "name": "Intelligent Energy S800",
        "rated_power_w": 800,
        "mass_kg": 1.49,  # combined mass with cabling (fuel cell + power module)
        "specific_power_w_per_kg": 800 / 1.49,
        "system_efficiency": 0.485,  # back-calculated from 50g H2/hr @ 800W, LHV 33000 Wh/kg
        "bop_fraction_of_stack": 0.1,  # cabling already included; small allowance left for H2 tubing/fittings not covered by datasheet mass
        "voltage_range_v": (25, 50),
        "notes": "Includes redundant hybrid battery architecture natively.",
    },
    "horizon_ul1000": {
        "name": "Horizon UL-1000",
        "rated_power_w": 1000,
        "mass_kg": 3.070,  # measured: stack+housing+blowers+valves (2266g) + controller+cables+LCD+dissipation plate (728g) + tubes/screws/fittings/H2 connectors (76g)
        "specific_power_w_per_kg": 1000 / 3.070,
        "system_efficiency": 0.40,  # H-1000 datasheet: 40% at 43V (same family as UL500)
        "bop_fraction_of_stack": 0.0,  # tubes/fittings/H2 connectors already included in mass_kg above
        "voltage_range_v": (39, 69),
        "notes": "Larger sibling of the UL500. Mass includes full accessory kit (tubes, fittings, H2 connectors).",
    },
}


def get_profile(key):
    """Look up a fuel cell profile by key. Raises KeyError with a helpful message if not found."""
    if key not in FUEL_CELL_PROFILES:
        available = ", ".join(FUEL_CELL_PROFILES.keys())
        raise KeyError(f"Unknown fuel cell '{key}'. Available options: {available}")
    return FUEL_CELL_PROFILES[key]


if __name__ == "__main__":
    for key, profile in FUEL_CELL_PROFILES.items():
        print(f"\n{profile['name']} ({key})")
        print(f"  Rated power:      {profile['rated_power_w']} W")
        print(f"  Mass:             {profile['mass_kg']} kg")
        print(f"  Specific power:   {profile['specific_power_w_per_kg']:.1f} W/kg")
        print(f"  System efficiency: {profile['system_efficiency']*100:.1f}%")
