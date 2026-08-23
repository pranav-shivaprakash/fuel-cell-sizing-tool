"""
Battery Buffer Profiles
--------------------------
Real battery cell specifications, used to replace the generic
battery_specific_power_w_per_kg assumption in fuel_cell_sizing.py.

Source: Ovonic 150C Racing Series 6S 1400mAh 22.2V LiPo Battery
        (confirmed across multiple Ovonic retail listings: capacity
        1400mAh, voltage 22.2V/6S1P, discharge rate 150C continuous,
        mass 227g, XT60 connector)
"""

BATTERY_PROFILES = {
    "ovonic_150c_1400mah": {
        "name": "Ovonic 150C Racing 6S 1400mAh",
        "capacity_ah": 1.4,
        "voltage_v": 22.2,
        "discharge_rate_c": 150,
        "mass_kg": 0.227,
        "max_continuous_current_a": 1.4 * 150,  # 210 A
        "max_continuous_power_w": 1.4 * 150 * 22.2,  # 4662 W
        "specific_energy_wh_per_kg": (1.4 * 22.2) / 0.227,  # ~137 Wh/kg
        "specific_power_w_per_kg": (1.4 * 150 * 22.2) / 0.227,  # ~20,536 W/kg (theoretical max)
        "connector": "XT60",
    },
}


def get_battery(key):
    if key not in BATTERY_PROFILES:
        available = ", ".join(BATTERY_PROFILES.keys())
        raise KeyError(f"Unknown battery '{key}'. Available options: {available}")
    return BATTERY_PROFILES[key]


if __name__ == "__main__":
    for key, profile in BATTERY_PROFILES.items():
        print(f"\n{profile['name']} ({key})")
        print(f"  Capacity:              {profile['capacity_ah']} Ah")
        print(f"  Voltage:               {profile['voltage_v']} V")
        print(f"  Discharge rate:        {profile['discharge_rate_c']}C")
        print(f"  Mass:                  {profile['mass_kg']*1000:.0f} g")
        print(f"  Max continuous power:  {profile['max_continuous_power_w']:.0f} W")
        print(f"  Specific energy:       {profile['specific_energy_wh_per_kg']:.1f} Wh/kg")
