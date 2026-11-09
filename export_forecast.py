"""Write today's forecast to site/forecast.json. Run with: python export_forecast.py"""

import json
from pathlib import Path

import pandas as pd

from combine import build_table
from fetch import get_sun_times
from scoring import (
    find_best_window,
    get_no_window_message,
    get_sky_category,
    get_wave_category,
    get_wind_category,
)

OUTPUT_PATH = Path(__file__).parent / "site" / "forecast.json"


def missing_to_none(value):
    """Return None for a missing value (NaN), because JSON has no NaN.

    None is written to the JSON file as null.
    """
    if pd.isna(value):
        return None
    return value


def find_hour(hours, time):
    """Return the hour whose "time" matches, or None if there isn't one."""
    for hour in hours:
        if hour["time"] == time:
            return hour
    return None


def build_current_hour(hour, sunrise, sunset):
    """Return the current hour's verdict, score and tile categories."""
    return {
        "time": hour["time"][11:],  # [11:] skips the date
        "verdict": hour["verdict"],
        "score": missing_to_none(hour["score"]),  # night hours have no score
        "sky": get_sky_category(hour, sunrise, sunset),
        "wind": get_wind_category(hour),
        "waves": get_wave_category(hour["wave_height"]),
    }


def build_daylight_hour(hour, sunrise, sunset):
    """Return what the page shows for one daylight hour."""
    return {
        "time": hour["time"][11:],
        "score": hour["score"],
        "verdict": hour["verdict"],
        "feels_like": missing_to_none(hour["apparent_temperature"]),
        "sky": get_sky_category(hour, sunrise, sunset),
        "wind_speed": missing_to_none(hour["wind_speed_10m"]),
        "wind_gusts": missing_to_none(hour["wind_gusts_10m"]),
        "wave_height": missing_to_none(hour["wave_height"]),
    }


def build_forecast_data(hours, sunrise, sunset, current_time, updated_at):
    """Return everything the page needs, as a dictionary ready for JSON.

    hours is a list of rows from the combined table, in time order. current_time
    is the current hour, written like the "time" column: "2026-11-02T13:00".
    updated_at is when this forecast was made, as text.
    """
    window = find_best_window(hours, sunrise, sunset, current_time)

    no_window_message = None
    if window is None:
        no_window_message = get_no_window_message(hours)

    current = find_hour(hours, current_time)
    current_hour = None
    if current is not None:
        current_hour = build_current_hour(current, sunrise, sunset)

    daylight_hours = []
    for hour in hours:
        if hour["verdict"] != "Night":
            daylight_hours.append(build_daylight_hour(hour, sunrise, sunset))

    return {
        "updated_at": updated_at,
        "sunrise": sunrise[11:],
        "sunset": sunset[11:],
        "best_window": window,
        "no_window_message": no_window_message,
        "current_hour": current_hour,
        "hours": daylight_hours,
    }


if __name__ == "__main__":
    # If Open-Meteo can't be reached, the error stops the script here, before
    # anything is written, so the last good forecast.json is kept
    sunrise, sunset = get_sun_times()
    table = build_table(sunrise, sunset)

    now = pd.Timestamp.now(tz="Europe/Madrid")
    current_time = now.strftime("%Y-%m-%dT%H:00")  # same format as the "time" column
    updated_at = now.strftime("%Y-%m-%dT%H:%M")

    # to_dict("records") turns the table into a list with one dictionary per row
    hours = table.to_dict("records")
    data = build_forecast_data(hours, sunrise, sunset, current_time, updated_at)

    OUTPUT_PATH.parent.mkdir(exist_ok=True)
    # allow_nan=False stops with an error if a NaN slipped through, since a
    # browser can't read NaN in JSON. ensure_ascii=False keeps "°C" readable.
    with open(OUTPUT_PATH, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False, allow_nan=False)

    print("Wrote", OUTPUT_PATH)
