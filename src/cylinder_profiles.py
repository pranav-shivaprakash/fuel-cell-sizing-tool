"""
Hydrogen Cylinder Profiles
-----------------------------
Real composite cylinder specifications, used to replace the generic
gravimetric-fraction assumption in fuel_cell_sizing.py with actual
product data.

Source: X-Fiber cylinder datasheet (S2 / S3 models).
"""

# Real-gas hydrogen density at 300 bar, ~15 degC ambient.
# This is a standard reference value for compressed H2 storage
# calculations -- real hydrogen deviates from ideal gas behaviour
# significantly at this pressure (compressibility factor Z > 1),
# so density is noticeably lower than the ideal gas law would predict.
H2_DENSITY_AT_300BAR_KG_PER_M3 = 20.7

CYLINDER_PROFILES = {
    "xfiber_s2": {
        "name": "X-Fiber S2",
        "volume_l": 2,
        "empty_mass_kg": 1.3,
        "max_pressure_bar": 300,
        "diameter_mm": 113,
        "length_mm": 369,
    },
    "xfiber_s3": {
        "name": "X-Fiber S3",
        "volume_l": 3,
        "empty_mass_kg": 1.6,
        "max_pressure_bar": 300,
        "diameter_mm": 119,
        "length_mm": 440,
    },
}


def h2_capacity_kg(cylinder_profile):
    """Usable hydrogen mass (kg) this cylinder can hold when filled to its rated pressure."""
    volume_m3 = cylinder_profile["volume_l"] / 1000.0
    return volume_m3 * H2_DENSITY_AT_300BAR_KG_PER_M3


def get_cylinder(key):
    if key not in CYLINDER_PROFILES:
        available = ", ".join(CYLINDER_PROFILES.keys())
        raise KeyError(f"Unknown cylinder '{key}'. Available options: {available}")
    return CYLINDER_PROFILES[key]


if __name__ == "__main__":
    for key, profile in CYLINDER_PROFILES.items():
        capacity = h2_capacity_kg(profile)
        total_filled_mass = profile["empty_mass_kg"] + capacity
        gravimetric_fraction = capacity / total_filled_mass
        print(f"\n{profile['name']} ({key})")
        print(f"  Empty mass:            {profile['empty_mass_kg']} kg")
        print(f"  H2 capacity:           {capacity*1000:.1f} g")
        print(f"  Total filled mass:     {total_filled_mass:.3f} kg")
        print(f"  Real gravimetric frac: {gravimetric_fraction*100:.1f}%")
