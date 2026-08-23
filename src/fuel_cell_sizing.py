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


def size_fuel_cell_stack(peak_power_w, fc_specific_power_w_per_kg, stack_fraction_of_peak=0.6,
                          rated_power_w=None, num_units=1):
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
        Ignored if rated_power_w is given (see below).
    rated_power_w : float or None
        If given, caps stack_power_w at this real product rating (times
        num_units), instead of deriving it from stack_fraction_of_peak.
        Use this to model a specific real fuel cell product's hard limit.
    num_units : int
        Number of fuel cell units used in parallel (e.g. 2 for two stacks
        side by side). Multiplies both power and mass.

    Returns
    -------
    dict with stack_power_w, stack_mass_kg
    """
    if rated_power_w is not None:
        stack_power_w = rated_power_w * num_units
    else:
        stack_power_w = peak_power_w * stack_fraction_of_peak

    single_unit_mass_kg = (stack_power_w / num_units) / fc_specific_power_w_per_kg
    stack_mass_kg = single_unit_mass_kg * num_units
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
    Size the hydrogen tank based on total mission energy required, using
    a generic gravimetric fraction assumption. See size_hydrogen_tank_real()
    for sizing against a specific real cylinder product instead -- that
    is the more accurate option once a candidate cylinder is known, since
    small composite cylinders' real gravimetric fraction is well below
    generic large-tank estimates.

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


def size_hydrogen_tank_real(total_energy_wh, system_efficiency, cylinder_profile):
    """
    Size the hydrogen storage using a specific real cylinder product,
    instead of a generic gravimetric fraction assumption.

    Determines how many of the given cylinder are needed to carry the
    required hydrogen mass, and returns the resulting total mass
    (empty cylinders + hydrogen, not counting fill fraction -- assumes
    each cylinder used is filled to its full rated capacity except
    possibly the last one).

    Parameters
    ----------
    total_energy_wh : float
        Total mission energy requirement.
    system_efficiency : float
        Fuel cell system efficiency (chemical to electrical).
    cylinder_profile : dict
        A profile from cylinder_profiles.CYLINDER_PROFILES, e.g.
        get_cylinder("xfiber_s2").

    Returns
    -------
    dict with h2_mass_kg, num_cylinders, cylinder_mass_kg (total empty
    mass of all cylinders used), tank_system_mass_kg (cylinders + H2)
    """
    from cylinder_profiles import h2_capacity_kg
    import math

    h2_energy_needed_wh = total_energy_wh / system_efficiency
    h2_mass_kg = h2_energy_needed_wh / H2_ENERGY_DENSITY_WH_PER_KG

    capacity_per_cylinder_kg = h2_capacity_kg(cylinder_profile)
    num_cylinders = max(1, math.ceil(h2_mass_kg / capacity_per_cylinder_kg))

    cylinder_mass_kg = num_cylinders * cylinder_profile["empty_mass_kg"]
    tank_system_mass_kg = cylinder_mass_kg + h2_mass_kg

    return {
        "h2_mass_kg": h2_mass_kg,
        "num_cylinders": num_cylinders,
        "cylinder_name": cylinder_profile["name"],
        "cylinder_mass_kg": cylinder_mass_kg,
        "tank_system_mass_kg": tank_system_mass_kg,
    }


def size_battery_only_system(peak_power_w, total_energy_wh,
                              battery_specific_power_w_per_kg=2000,
                              battery_specific_energy_wh_per_kg=188):
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
        Battery specific energy (Wh/kg). Default 188 Wh/kg matches the
        measured 6S1P 16000mAh 22.2V pack (355.2 Wh / 1.89 kg) used as
        the baseline battery-only system for comparison.

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
                      system_efficiency=0.5,
                      bop_fraction_of_stack=0.5,
                      mass_budget_kg=None,
                      rated_power_w=None,
                      num_units=1,
                      cylinder_profile=None):
    """
    Run the full sizing pipeline and return a summary of all components
    plus total system mass.

    Parameters
    ----------
    bop_fraction_of_stack : float
        Balance-of-plant mass (power electronics, DC/DC converter, valves,
        wiring, hoses, fittings) as a fraction of stack mass. 0.5 is a
        commonly cited first-order estimate for small PEM systems where
        BOP is not yet component-specified; refine with real component
        datasheets (DC/DC converter, wiring gauge/length, hose fittings)
        as the design matures.
    mass_budget_kg : float or None
        If given, the result includes a check of whether the sized
        system fits within this mass budget.
    rated_power_w : float or None
        If given, caps the fuel cell's output at this real product rating
        (times num_units) instead of deriving it from stack_fraction_of_peak.
        Use this to model a specific real product's hard power limit.
    num_units : int
        Number of fuel cell units used in parallel.
    cylinder_profile : dict or None
        If given (a profile from cylinder_profiles.CYLINDER_PROFILES),
        sizes hydrogen storage against this real cylinder product instead
        of the generic gravimetric fraction assumption.
    """
    stack = size_fuel_cell_stack(peak_power_w, fc_specific_power_w_per_kg, stack_fraction_of_peak,
                                  rated_power_w=rated_power_w, num_units=num_units)
    battery = size_battery_buffer(peak_power_w, stack["stack_power_w"],
                                   battery_specific_power_w_per_kg, buffer_duration_s)

    if cylinder_profile is not None:
        tank = size_hydrogen_tank_real(total_energy_wh, system_efficiency, cylinder_profile)
    else:
        tank = size_hydrogen_tank(total_energy_wh, system_efficiency)

    bop_mass_kg = stack["stack_mass_kg"] * bop_fraction_of_stack

    total_mass_kg = (stack["stack_mass_kg"] + battery["battery_mass_kg"]
                      + tank["tank_system_mass_kg"] + bop_mass_kg)

    result = {
        "fuel_cell_stack_power_w": stack["stack_power_w"],
        "fuel_cell_stack_mass_kg": stack["stack_mass_kg"],
        "battery_buffer_power_w": battery["buffer_power_w"],
        "battery_mass_kg": battery["battery_mass_kg"],
        "hydrogen_mass_kg": tank["h2_mass_kg"],
        "tank_system_mass_kg": tank["tank_system_mass_kg"],
        "balance_of_plant_mass_kg": bop_mass_kg,
        "total_system_mass_kg": total_mass_kg,
    }

    if "num_cylinders" in tank:
        result["num_cylinders"] = tank["num_cylinders"]
        result["cylinder_name"] = tank["cylinder_name"]

    if mass_budget_kg is not None:
        result["mass_budget_kg"] = mass_budget_kg
        result["within_budget"] = total_mass_kg <= mass_budget_kg
        result["margin_kg"] = mass_budget_kg - total_mass_kg

    return result


if __name__ == "__main__":
    # Real mission: Evolonic VTOL UAV fuel cell retrofit thesis
    from mission_profile import multi_phase_mission, mission_energy_wh, mission_peak_power_w

    phases = [
        {"name": "takeoff", "duration_hours": 1.25 / 60, "power_w": 60 * 22.2},
        {"name": "cruise", "duration_hours": 59.5 / 60, "power_w": 10 * 22.2},
        {"name": "landing", "duration_hours": 1.0 / 60, "power_w": 27.5 * 22.2},
    ]
    mission = multi_phase_mission(phases)

    peak_power_w = mission_peak_power_w(mission)
    total_energy_wh = mission_energy_wh(mission)

    # Check against a 3.5 kg target (midpoint of the 3-4 kg budget)
    result = size_full_system(peak_power_w, total_energy_wh, mass_budget_kg=3.5)

    print("--- Fuel Cell System Sizing Results (Evolonic VTOL UAV) ---")
    for key, value in result.items():
        if isinstance(value, bool):
            print(f"{key:28s}: {value}")
        else:
            print(f"{key:28s}: {value:10.2f}")
