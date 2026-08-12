"""
Fuel Cell System Sizing
-------------------------
Given a mission's energy and power requirements, size the three main
components of a hydrogen fuel cell propulsion system:

  1. Fuel cell stack  -- sized by PEAK power demand (stacks respond
     relatively slowly, so a battery buffer covers sudden spikes)
  2. Battery buffer    -- sized to cover the gap between the fuel cell's
     steady output and any short peak power demands (takeoff, climb)
  3. Hydrogen tank     -- sized by TOTAL energy required for the mission,
     converted through hydrogen's energy density and system efficiency

This is a first-order sizing tool: good for comparing design trade-offs
and getting realistic ballpark numbers, not a substitute for detailed
thermal/fluid system design.
"""

import numpy as np
import pandas as pd

# --- Physical constants ---
H2_ENERGY_DENSITY_WH_PER_KG = 33_000   # lower heating value of hydrogen, Wh/kg
H2_TANK_GRAVIMETRIC_FRACTION = 0.05    # typical fraction of tank+H2 mass that is USABLE H2
                                        # (rest is tank structure/pressure vessel weight)
                                        # e.g. 0.05 means a tank system is ~20x heavier than
                                        # the hydrogen it carries (typical for high-pressure
                                        # composite tanks, not liquid H2)


def size_fuel_cell_stack(peak_power_w, fc_specific_power_w_per_kg, stack_fraction_of_peak=0.6):
    """
    Size the fuel cell stack.

    Parameters
    ----------
    peak_power_w : float
        Peak power demand from the mission profile.
    fc_specific_power_w_per_kg : float
        Fuel cell stack specific power (W/kg). Typical PEM stacks: 300-800 W/kg.
    stack_fraction_of_peak : float
        Fraction of peak power the fuel cell itself needs to cover; the rest
        is covered by the battery buffer during short spikes (e.g. takeoff).
        0.6 means the fuel cell covers 60% of peak power continuously, and
        the battery covers the remaining 40% during peaks.

    Returns
    -------
    dict with stack_power_w, stack_mass_kg
    """
    stack_power_w = peak_power_w * stack_fraction_of_peak
    stack_mass_kg = stack_power_w / fc_specific_power_w_per_kg
    return {"stack_power_w": stack_power_w, "stack_mass_kg": stack_mass_kg}


def size_battery_buffer(peak_power_w, stack_power_w, battery_specific_power_w_per_kg,
                         buffer_duration_s=120):
    """
    Size the battery buffer that covers the gap between what the fuel cell
    stack supplies and what peak power demands require.

    Parameters
    ----------
    peak_power_w : float
        Peak power demand from the mission profile.
    stack_power_w : float
        Continuous power the fuel cell stack supplies (from size_fuel_cell_stack).
    battery_specific_power_w_per_kg : float
        Battery specific power (W/kg). Typical Li-ion for high power: 1000-3000 W/kg.
    buffer_duration_s : float
        How long the battery needs to sustain the power gap (e.g. duration
        of takeoff/climb phase). Default 120s is a reasonable first guess.

    Returns
    -------
    dict with buffer_power_w, buffer_energy_wh, battery_mass_kg
    """
    buffer_power_w = max(peak_power_w - stack_power_w, 0)
    buffer_energy_wh = buffer_power_w * (buffer_duration_s / 3600.0)
    battery_mass_kg = buffer_power_w / battery_specific_power_w_per_kg
    return {
        "buffer_power_w": buffer_power_w,
        "buffer_energy_wh": buffer_energy_wh,
        "battery_mass_kg": battery_mass_kg,
    }


def size_hydrogen_tank(total_energy_wh, system_efficiency=0.5):
    """
    Size the hydrogen tank based on total mission energy required.

    Parameters
    ----------
    total_energy_wh : float
        Total mission energy requirement (from mission_energy_wh()).
    system_efficiency : float
        Overall efficiency converting hydrogen's chemical energy into
        usable electrical energy (fuel cell stack efficiency, typically
        45-60% for PEM systems).

    Returns
    -------
    dict with h2_mass_kg, tank_system_mass_kg
    """
    h2_energy_needed_wh = total_energy_wh / system_efficiency
    h2_mass_kg = h2_energy_needed_wh / H2_ENERGY_DENSITY_WH_PER_KG
    tank_system_mass_kg = h2_mass_kg / H2_TANK_GRAVIMETRIC_FRACTION
    return {"h2_mass_kg": h2_mass_kg, "tank_system_mass_kg": tank_system_mass_kg}


def size_battery_only_system(peak_power_w, total_energy_wh,
                              battery_specific_power_w_per_kg=2000,
                              battery_specific_energy_wh_per_kg=200):
    """
    Size a pure battery-powered system covering the same mission, for
    comparison against the hydrogen fuel cell system.

    A battery must be sized by whichever requirement is larger: enough
    power capability for peak demand, OR enough energy capacity for the
    full mission. Unlike a fuel cell + tank, one battery pack has to do
    both jobs at once.

    Parameters
    ----------
    peak_power_w : float
        Peak power demand from the mission profile.
    total_energy_wh : float
        Total mission energy requirement.
    battery_specific_power_w_per_kg : float
        Battery specific power (W/kg).
    battery_specific_energy_wh_per_kg : float
        Battery specific energy (Wh/kg). Typical high-energy Li-ion: 150-250 Wh/kg.

    Returns
    -------
    dict with mass_from_power_kg, mass_from_energy_kg, battery_only_mass_kg
    """
    mass_from_power_kg = peak_power_w / battery_specific_power_w_per_kg
    mass_from_energy_kg = total_energy_wh / battery_specific_energy_wh_per_kg
    # the battery must satisfy BOTH constraints, so mass is set by whichever is larger
    battery_only_mass_kg = max(mass_from_power_kg, mass_from_energy_kg)
    return {
        "mass_from_power_kg": mass_from_power_kg,
        "mass_from_energy_kg": mass_from_energy_kg,
        "battery_only_mass_kg": battery_only_mass_kg,
    }


def size_full_system(peak_power_w, total_energy_wh,
                      fc_specific_power_w_per_kg=500,
                      battery_specific_power_w_per_kg=2000,
                      stack_fraction_of_peak=0.6,
                      buffer_duration_s=120,
                      system_efficiency=0.5):
    """
    Run the full sizing pipeline and return a summary of all components
    plus total system mass.
    """
    stack = size_fuel_cell_stack(peak_power_w, fc_specific_power_w_per_kg, stack_fraction_of_peak)
    battery = size_battery_buffer(peak_power_w, stack["stack_power_w"],
                                   battery_specific_power_w_per_kg, buffer_duration_s)
    tank = size_hydrogen_tank(total_energy_wh, system_efficiency)

    total_mass_kg = stack["stack_mass_kg"] + battery["battery_mass_kg"] + tank["tank_system_mass_kg"]

    return {
        "fuel_cell_stack_power_w": stack["stack_power_w"],
        "fuel_cell_stack_mass_kg": stack["stack_mass_kg"],
        "battery_buffer_power_w": battery["buffer_power_w"],
        "battery_mass_kg": battery["battery_mass_kg"],
        "hydrogen_mass_kg": tank["h2_mass_kg"],
        "tank_system_mass_kg": tank["tank_system_mass_kg"],
        "total_system_mass_kg": total_mass_kg,
    }


if __name__ == "__main__":
    # Example: size a system for the mission profile we built earlier
    from mission_profile import multi_phase_mission, mission_energy_wh, mission_peak_power_w

    phases = [
        {"name": "takeoff", "duration_hours": 0.05, "power_w": 4000},
        {"name": "climb", "duration_hours": 0.15, "power_w": 2500},
        {"name": "cruise", "duration_hours": 3.0, "power_w": 1200},
        {"name": "descent", "duration_hours": 0.1, "power_w": 600},
        {"name": "landing", "duration_hours": 0.05, "power_w": 3000},
    ]
    mission = multi_phase_mission(phases)

    peak_power_w = mission_peak_power_w(mission)
    total_energy_wh = mission_energy_wh(mission)

    result = size_full_system(peak_power_w, total_energy_wh)

    print("--- Fuel Cell System Sizing Results ---")
    for key, value in result.items():
        print(f"{key:28s}: {value:10.2f}")
