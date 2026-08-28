"""
Emergency Battery Sizing (Fuel-Cell-Failure Contingency)
-----------------------------------------------------------
fuel_cell_sizing.py's battery buffer is a WEIGHT-OPTIMIZED, short-duration
peak-shaver: size_battery_buffer() only covers the gap between the fuel
cell's steady output and instantaneous peak demand, for buffer_duration_s
(default 120 s) -- and it assumes the fuel cell keeps working throughout.

This module asks a different, safety-critical question instead: if the
fuel cell fails completely mid-flight, can the battery buffer -- alone,
with zero help from the fuel cell -- supply enough POWER and ENERGY to
fly a safe abort/landing sequence?

Failure contingency profile (first-order, conservative):
  1. Emergency climb / go-around: full takeoff-equivalent power
     (60 A x 22.2 V = 1332 W) for 1.5 minutes -- enough to climb clear
     of obstacles and divert to a safe landing site.
  2. Emergency landing: landing power (27.5 A x 22.2 V = 611 W) for
     1 minute -- matches the measured landing phase in mission_profile.py.

Both phases are flown on battery power alone, so the pack has to satisfy
the POWER and ENERGY requirements of the profile simultaneously, not
whichever is convenient -- the same "both constraints, take the larger"
logic as size_battery_only_system() in fuel_cell_sizing.py, just applied
to a much shorter, harsher profile than the full mission.

The contingency profile is built with mission_profile.py's own
multi_phase_mission() -- to the sizing math, "fly the aircraft without
the fuel cell" is just another mission.
"""

import math

from mission_profile import multi_phase_mission, mission_energy_wh, mission_peak_power_w
from battery_profiles import BATTERY_PROFILES, get_battery


def get_emergency_profile(climb_minutes=1.5, landing_minutes=1.0,
                           climb_current_a=60, landing_current_a=27.5, voltage_v=22.2):
    """
    Build the fuel-cell-failure contingency profile: full takeoff-equivalent
    power for climb_minutes (climb-away/go-around), then landing power for
    landing_minutes. Defaults match the real measured currents already used
    for takeoff/landing in mission_profile.py's real mission.
    """
    phases = [
        {"name": "emergency_climb", "duration_hours": climb_minutes / 60,
         "power_w": climb_current_a * voltage_v},
        {"name": "emergency_landing", "duration_hours": landing_minutes / 60,
         "power_w": landing_current_a * voltage_v},
    ]
    return multi_phase_mission(phases)


def size_emergency_battery_generic(peak_power_w, total_energy_wh,
                                    battery_specific_power_w_per_kg=2000,
                                    battery_specific_energy_wh_per_kg=188,
                                    depth_of_discharge=0.8):
    """
    First-order mass estimate using generic specific power/energy figures
    (same style as size_battery_only_system() in fuel_cell_sizing.py).

    Parameters
    ----------
    depth_of_discharge : float
        Usable fraction of nameplate energy. A pack is not run to 0% in
        practice (voltage sag near empty, cell damage risk); 0.8 is a
        conservative usable-energy assumption for a reserve that must
        still deliver full power near the end of discharge.

    Returns
    -------
    dict with mass_from_power_kg, mass_from_energy_kg, emergency_battery_mass_kg
    """
    mass_from_power_kg = peak_power_w / battery_specific_power_w_per_kg
    mass_from_energy_kg = (total_energy_wh / depth_of_discharge) / battery_specific_energy_wh_per_kg
    emergency_battery_mass_kg = max(mass_from_power_kg, mass_from_energy_kg)
    return {
        "mass_from_power_kg": mass_from_power_kg,
        "mass_from_energy_kg": mass_from_energy_kg,
        "emergency_battery_mass_kg": emergency_battery_mass_kg,
    }


def size_emergency_battery_real(peak_power_w, total_energy_wh, battery_key,
                                 depth_of_discharge=0.8):
    """
    Size the emergency reserve against a specific real cell from
    battery_profiles.py, by whole-cell count -- the same approach
    compare_fuel_cells.py uses for the normal buffer.

    A cell has to cover its share of peak_power_w AND its share of
    total_energy_wh on the SAME flight, so the pack needs as many cells
    as the more demanding of the two constraints, not the average.
    """
    battery = get_battery(battery_key)
    usable_energy_wh = total_energy_wh / depth_of_discharge

    num_by_power = math.ceil(peak_power_w / battery["max_continuous_power_w"])
    num_by_energy = math.ceil(usable_energy_wh / (battery["capacity_ah"] * battery["voltage_v"]))
    num_batteries = max(1, num_by_power, num_by_energy)

    return {
        "battery_key": battery_key,
        "battery_name": battery["name"],
        "num_by_power": num_by_power,
        "num_by_energy": num_by_energy,
        "num_batteries": num_batteries,
        "limiting_factor": "power" if num_by_power >= num_by_energy else "energy",
        "emergency_battery_mass_kg": num_batteries * battery["mass_kg"],
    }


def check_normal_pack_survives_failure(normal_battery_key, normal_num_batteries, emergency_result):
    """
    Compare a normal-duty pack (sized only to smooth short peaks while the
    fuel cell is healthy -- e.g. the 1x cell picks in compare_fuel_cells.py)
    against what that same slot needs to actually survive a full fuel-cell
    failure. Returns whether it survives, and the shortfall if not.
    """
    shortfall_cells = max(0, emergency_result["num_batteries"] - normal_num_batteries)
    normal_battery = get_battery(normal_battery_key)
    extra_mass_kg = shortfall_cells * normal_battery["mass_kg"]
    return {
        "normal_battery_key": normal_battery_key,
        "normal_num_batteries": normal_num_batteries,
        "emergency_num_batteries_needed": emergency_result["num_batteries"],
        "shortfall_cells": shortfall_cells,
        "extra_mass_kg": extra_mass_kg,
        "survives_failure": shortfall_cells == 0,
    }


def print_emergency_result(result):
    print(f"\n--- Emergency Reserve Sizing: {result['battery_name']} ---")
    print(f"Cells needed by power:   {result['num_by_power']}")
    print(f"Cells needed by energy:  {result['num_by_energy']}")
    print(f"Limiting factor:         {result['limiting_factor']}")
    print(f"Cells required:          {result['num_batteries']}")
    print(f"Emergency reserve mass:  {result['emergency_battery_mass_kg']:.3f} kg")


if __name__ == "__main__":
    emergency = get_emergency_profile()
    peak_power_w = mission_peak_power_w(emergency)
    total_energy_wh = mission_energy_wh(emergency)

    print("--- Fuel-Cell-Failure Contingency Profile ---")
    print(f"Peak power (emergency climb): {peak_power_w:.1f} W")
    print(f"Total energy required:        {total_energy_wh:.1f} Wh\n")

    generic = size_emergency_battery_generic(peak_power_w, total_energy_wh)
    print(f"Generic estimate (2000 W/kg, 188 Wh/kg, 80% DoD): "
          f"{generic['emergency_battery_mass_kg']:.3f} kg "
          f"(power-limited: {generic['mass_from_power_kg']:.3f} kg, "
          f"energy-limited: {generic['mass_from_energy_kg']:.3f} kg)")

    # Real-cell sizing across every candidate in battery_profiles.py
    real_results = {}
    for key in BATTERY_PROFILES:
        result = size_emergency_battery_real(peak_power_w, total_energy_wh, key)
        real_results[key] = result
        print_emergency_result(result)

    # Does the normal-duty pack picked in compare_fuel_cells.py (1x cell,
    # sized only for a 120s peak-shaving buffer) survive a real failure?
    print("\n--- Does the normal-duty buffer pack survive a fuel-cell failure? ---")
    normal_duty_picks = {
        "cnhl_130c_1300mah": 1,   # UL500 config
        "gnb_120c_930mah": 1,     # IE S800 config
        "gnb_80c_550mah": 1,      # UL-1000 config
    }
    for battery_key, normal_num in normal_duty_picks.items():
        check = check_normal_pack_survives_failure(battery_key, normal_num, real_results[battery_key])
        status = "SURVIVES" if check["survives_failure"] else "DOES NOT SURVIVE"
        print(f"\n{get_battery(battery_key)['name']}: {status}")
        print(f"  Normal-duty pack:      {check['normal_num_batteries']}x cell")
        print(f"  Needed for failure:    {check['emergency_num_batteries_needed']}x cell")
        if not check["survives_failure"]:
            print(f"  Shortfall:             {check['shortfall_cells']} more cell(s), "
                  f"+{check['extra_mass_kg']*1000:.0f} g")
