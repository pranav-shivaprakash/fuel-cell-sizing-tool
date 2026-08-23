"""
Fuel Cell Candidate Comparison
---------------------------------
Runs the sizing tool once per fuel cell profile (real datasheet specs)
against the actual UAV mission, and compares results -- including a
check on whether the sizing choice is actually achievable given each
product's rated power limit.

Usage:
    python3 compare_fuel_cells.py                  # compares all profiles
    python3 compare_fuel_cells.py horizon_fcs_ul500 # view one profile only
    python3 compare_fuel_cells.py ie_s800           # view one profile only
"""

import sys
import matplotlib.pyplot as plt

from mission_profile import multi_phase_mission, mission_energy_wh, mission_peak_power_w
from fuel_cell_sizing import size_full_system
from fuel_cell_profiles import FUEL_CELL_PROFILES, get_profile
from cylinder_profiles import CYLINDER_PROFILES, get_cylinder
from battery_profiles import BATTERY_PROFILES, get_battery


def get_real_mission():
    """The real Evolonic VTOL UAV mission: takeoff/cruise/landing at measured current draws."""
    phases = [
        {"name": "takeoff", "duration_hours": 1.25 / 60, "power_w": 60 * 22.2},
        {"name": "cruise", "duration_hours": 59.5 / 60, "power_w": 10 * 22.2},
        {"name": "landing", "duration_hours": 1.0 / 60, "power_w": 27.5 * 22.2},
    ]
    return multi_phase_mission(phases)


def size_with_profile(profile_key, peak_power_w, total_energy_wh,
                       stack_fraction_of_peak=0.6, mass_budget_kg=3.5,
                       use_rated_power_cap=False, num_units=1,
                       label_suffix="", cylinder_key=None, battery_key=None):
    """
    Run the sizing tool using a specific fuel cell's real specs.

    Parameters
    ----------
    use_rated_power_cap : bool
        If True, caps the fuel cell's power output at its real rated power
        (x num_units) instead of deriving it from stack_fraction_of_peak.
        Use this when modelling a specific real product's hard limit
        (e.g. a single UL500 can't be pushed past 500W no matter what
        stack_fraction_of_peak implies).
    num_units : int
        Number of this fuel cell used in parallel.
    label_suffix : str
        Extra text appended to the result's display name, to distinguish
        multiple configurations of the same underlying product.
    cylinder_key : str or None
        If given, a key from cylinder_profiles.CYLINDER_PROFILES -- sizes
        hydrogen storage against this real cylinder instead of the
        generic gravimetric-fraction assumption.
    battery_key : str or None
        If given, a key from battery_profiles.BATTERY_PROFILES -- sizes
        the battery buffer using this real cell's specific power instead
        of the generic 2000 W/kg default.
    """
    profile = get_profile(profile_key)
    cylinder_profile = get_cylinder(cylinder_key) if cylinder_key else None
    battery_specific_power_w_per_kg = (
        get_battery(battery_key)["specific_power_w_per_kg"] if battery_key else 2000
    )

    result = size_full_system(
        peak_power_w, total_energy_wh,
        fc_specific_power_w_per_kg=profile["specific_power_w_per_kg"],
        battery_specific_power_w_per_kg=battery_specific_power_w_per_kg,
        system_efficiency=profile["system_efficiency"],
        stack_fraction_of_peak=stack_fraction_of_peak,
        bop_fraction_of_stack=profile.get("bop_fraction_of_stack", 0.5),
        mass_budget_kg=mass_budget_kg,
        rated_power_w=profile["rated_power_w"] if use_rated_power_cap else None,
        num_units=num_units,
        cylinder_profile=cylinder_profile,
    )

    result["fuel_cell_name"] = profile["name"] + label_suffix
    result["rated_power_w"] = profile["rated_power_w"] * num_units
    result["exceeds_rated_power"] = result["fuel_cell_stack_power_w"] > result["rated_power_w"]

    if battery_key:
        import math
        battery = get_battery(battery_key)
        num_batteries = max(1, math.ceil(result["battery_buffer_power_w"] / battery["max_continuous_power_w"]))
        result["num_batteries"] = num_batteries
        result["battery_name"] = battery["name"]
        # Recompute battery mass using the real cell's actual mass, not the
        # generic specific-power-derived estimate, since real cells come in
        # fixed increments rather than continuously scalable mass.
        result["battery_mass_kg"] = num_batteries * battery["mass_kg"]
        result["total_system_mass_kg"] = (
            result["fuel_cell_stack_mass_kg"] + result["battery_mass_kg"]
            + result["tank_system_mass_kg"] + result["balance_of_plant_mass_kg"]
        )
        if "mass_budget_kg" in result:
            result["within_budget"] = result["total_system_mass_kg"] <= result["mass_budget_kg"]
            result["margin_kg"] = result["mass_budget_kg"] - result["total_system_mass_kg"]

    return result


def size_with_best_cylinder(profile_key, peak_power_w, total_energy_wh, mass_budget_kg,
                             preferred_cylinder_key="xfiber_s3", fallback_cylinder_key="xfiber_s2",
                             **kwargs):
    """
    Try the preferred (larger) cylinder first; if the resulting system exceeds
    the mass budget, fall back to the smaller cylinder instead. Larger
    cylinders carry more hydrogen margin for a given mission, so they're
    preferred whenever the mass budget allows it.
    """
    result = size_with_profile(profile_key, peak_power_w, total_energy_wh,
                                mass_budget_kg=mass_budget_kg,
                                cylinder_key=preferred_cylinder_key, **kwargs)
    if result["total_system_mass_kg"] > mass_budget_kg:
        result = size_with_profile(profile_key, peak_power_w, total_energy_wh,
                                    mass_budget_kg=mass_budget_kg,
                                    cylinder_key=fallback_cylinder_key, **kwargs)
    return result


def print_result(result):
    print(f"\n--- {result['fuel_cell_name']} ---")
    print(f"Fuel cell stack power required: {result['fuel_cell_stack_power_w']:.1f} W "
          f"(rated: {result['rated_power_w']} W)")
    if result["exceeds_rated_power"]:
        print(f"  *** WARNING: required stack power EXCEEDS this product's rated power. ***")
        print(f"      Lower stack_fraction_of_peak, or this product cannot cover this mission alone.")
    print(f"Fuel cell stack mass:    {result['fuel_cell_stack_mass_kg']:.3f} kg")
    print(f"Battery buffer power:    {result['battery_buffer_power_w']:.1f} W")
    print(f"Battery buffer mass:     {result['battery_mass_kg']:.3f} kg")
    if "num_batteries" in result:
        print(f"Battery cells needed:    {result['num_batteries']}x {result['battery_name']}")
    print(f"Hydrogen mass needed:    {result['hydrogen_mass_kg']*1000:.1f} g")
    if "num_cylinders" in result:
        print(f"Cylinder:                {result['num_cylinders']}x {result['cylinder_name']}")
    print(f"Hydrogen + tank mass:    {result['tank_system_mass_kg']:.3f} kg")
    print(f"Balance of plant mass:   {result['balance_of_plant_mass_kg']:.3f} kg")
    print(f"TOTAL SYSTEM MASS:       {result['total_system_mass_kg']:.3f} kg")
    if "mass_budget_kg" in result:
        status = "WITHIN BUDGET" if result["within_budget"] else "OVER BUDGET"
        print(f"Mass budget check:       {status} (margin: {result['margin_kg']:.3f} kg)")


def plot_comparison(results, save_path="../notebooks/fuel_cell_comparison.png"):
    """Bar chart comparing battery buffer mass and total mass across fuel cell candidates."""
    names = [r["fuel_cell_name"] for r in results]
    stack_mass = [r["fuel_cell_stack_mass_kg"] for r in results]
    battery_mass = [r["battery_mass_kg"] for r in results]
    tank_mass = [r["tank_system_mass_kg"] for r in results]
    bop_mass = [r["balance_of_plant_mass_kg"] for r in results]

    fig, ax = plt.subplots(figsize=(14, 8))
    x = range(len(names))

    bottom = [0] * len(names)
    for values, label in [(stack_mass, "Fuel cell stack"), (battery_mass, "Battery buffer"),
                           (tank_mass, "Hydrogen + tank"), (bop_mass, "Balance of plant")]:
        ax.bar(x, values, bottom=bottom, label=label)
        bottom = [b + v for b, v in zip(bottom, values)]

    for i, total in enumerate(bottom):
        ax.text(i, total + 0.05, f"{total:.2f} kg", ha="center", fontweight="bold")

    ax.set_ylim(0, max(bottom) * 1.15)

    ax.set_xticks(list(x))
    import textwrap
    wrapped_names = ["\n".join(textwrap.wrap(n, width=18)) for n in names]
    ax.set_xticklabels(wrapped_names, fontsize=11)
    ax.set_ylabel("Mass (kg)")
    ax.set_title("Fuel Cell Candidate Comparison: System Mass Breakdown")
    ax.legend()
    ax.grid(alpha=0.3, axis="y")
    fig.tight_layout()
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    print(f"\nSaved comparison chart to {save_path}")
    plt.close(fig)


if __name__ == "__main__":
    mission = get_real_mission()
    peak_power_w = mission_peak_power_w(mission)
    total_energy_wh = mission_energy_wh(mission)

    print(f"Mission peak power: {peak_power_w:.1f} W | Total energy: {total_energy_wh:.1f} Wh\n")

    results = []

    # Config 1: single UL500 (500W cap) -> 832W buffer -> needs >=1249mAh
    result_1 = size_with_best_cylinder(
        "horizon_fcs_ul500", peak_power_w, total_energy_wh, mass_budget_kg=4.0,
        use_rated_power_cap=True, num_units=1,
        label_suffix=" (1x, rated-power capped)",
        battery_key="cnhl_130c_1300mah",
    )
    print_result(result_1)
    results.append(result_1)

    # Config 2: IE S800 (800W cap) -> 532W buffer -> needs >=799mAh
    result_2 = size_with_best_cylinder(
        "ie_s800", peak_power_w, total_energy_wh, mass_budget_kg=4.0,
        use_rated_power_cap=True, num_units=1,
        label_suffix=" (1x, rated-power capped)",
        battery_key="gnb_120c_930mah",
    )
    print_result(result_2)
    results.append(result_2)

    # Config 3: single UL-1000 (1000W cap) -> 332W buffer -> needs >=498mAh
    result_3 = size_with_best_cylinder(
        "horizon_ul1000", peak_power_w, total_energy_wh, mass_budget_kg=4.0,
        use_rated_power_cap=True, num_units=1,
        label_suffix=" (1x, rated-power capped)",
        battery_key="gnb_80c_550mah",
    )
    print_result(result_3)
    results.append(result_3)

    plot_comparison(results, save_path="../notebooks/fuel_cell_comparison.png")
    