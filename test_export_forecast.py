import json

import scoring
from export_forecast import build_forecast_data

SUNRISE = "2026-11-02T07:30"
SUNSET = "2026-11-02T18:30"
UPDATED_AT = "2026-11-02T10:05"


def make_hour(time, verdict, score, **changes):
    """A rated hour of the combined table: calm, light wind, sunny, 21 °C."""
    hour = {
        "time": time,
        "apparent_temperature": 21.0,
        "precipitation_probability": 0.0,
        "wind_speed_10m": 5.0,
        "wind_gusts_10m": 10.0,
        "cloud_cover": 10.0,
        "wave_height": 0.2,
        "score": score,
        "verdict": verdict,
    }
    hour.update(changes)
    return hour


def make_day():
    """A short day: a night hour, two Go hours, a Stay home hour, a night hour."""
    return [
        make_hour("2026-11-02T07:00", "Night", None),
        make_hour("2026-11-02T10:00", "Go", scoring.MAX_SCORE),
        make_hour("2026-11-02T11:00", "Go", scoring.MAX_SCORE),
        make_hour("2026-11-02T12:00", "Stay home", 2, precipitation_probability=80.0),
        make_hour("2026-11-02T19:00", "Night", None),
    ]


def build(hours, current_time="2026-11-02T10:00"):
    return build_forecast_data(hours, SUNRISE, SUNSET, current_time, UPDATED_AT)


def test_update_time_and_sun_times():
    data = build(make_day())

    assert data["updated_at"] == UPDATED_AT
    assert data["sunrise"] == "07:30"
    assert data["sunset"] == "18:30"


def test_only_daylight_hours_are_listed():
    times = [hour["time"] for hour in build(make_day())["hours"]]
    assert times == ["10:00", "11:00", "12:00"]


def test_daylight_hour_has_everything_the_page_shows():
    assert build(make_day())["hours"][0] == {
        "time": "10:00",
        "score": scoring.MAX_SCORE,
        "verdict": "Go",
        "feels_like": 21.0,
        "sky": "sunny",
        "wind_speed": 5.0,
        "wind_gusts": 10.0,
        "wave_height": 0.2,
    }


def test_best_window_and_no_message_when_there_is_a_window():
    data = build(make_day())

    assert data["best_window"]["start"] == "10:00"
    assert data["best_window"]["end"] == "12:00"
    assert data["no_window_message"] is None


def test_message_and_no_window_when_good_hours_have_passed():
    data = build(make_day(), current_time="2026-11-02T12:00")

    assert data["best_window"] is None
    assert data["no_window_message"] == "No more good beach time today."


def test_current_hour_has_its_categories():
    assert build(make_day())["current_hour"] == {
        "time": "10:00",
        "verdict": "Go",
        "score": scoring.MAX_SCORE,
        "sky": "sunny",
        "wind": "light",
        "waves": "calm",
    }


def test_current_hour_at_night_has_no_score():
    current = build(make_day(), current_time="2026-11-02T19:00")["current_hour"]

    assert current["verdict"] == "Night"
    assert current["score"] is None
    assert current["sky"] == "night"


def test_current_hour_is_none_when_it_is_not_in_the_table():
    assert build(make_day(), current_time="2026-11-02T23:00")["current_hour"] is None


def test_missing_values_become_none():
    day = make_day()
    day[1]["apparent_temperature"] = float("nan")
    day[1]["wave_height"] = float("nan")

    hour = build(day)["hours"][0]

    assert hour["feels_like"] is None
    assert hour["wave_height"] is None


def test_data_can_be_written_as_json_with_missing_values():
    day = make_day()
    for hour in day:
        hour["wind_speed_10m"] = float("nan")
        hour["cloud_cover"] = float("nan")

    # allow_nan=False raises an error if any NaN is left in the data
    json.dumps(build(day), allow_nan=False)
