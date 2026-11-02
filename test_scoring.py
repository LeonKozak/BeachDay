import pytest

import scoring
from scoring import (
    find_best_window,
    get_no_window_message,
    get_sky_category,
    get_verdict,
    get_wave_category,
    get_wind_category,
    has_deal_breaker,
    is_daylight,
    rate_hour,
    score_hour,
)

SUNRISE = "2026-11-02T07:30"
SUNSET = "2026-11-02T18:30"
MIDDAY = "2026-11-02T12:00"
BEFORE_SUNRISE = "2026-11-02T07:00"
AFTER_SUNSET = "2026-11-02T19:00"

# A small step, to land just either side of a limit
STEP = 0.1


def make_hour(**changes):
    """A perfect beach hour at midday, with any values a test wants to change."""
    hour = {
        "time": MIDDAY,
        "apparent_temperature": scoring.FEELS_LIKE_MIN,
        "precipitation_probability": scoring.RAIN_CHANCE_LIMIT - STEP,
        "wind_speed_10m": scoring.WIND_LIMIT - STEP,
        "wind_gusts_10m": scoring.GUSTS_LIMIT - STEP,
        "cloud_cover": scoring.CLOUD_LIMIT - STEP,
        "wave_height": scoring.WAVES_CALM_LIMIT - STEP,
    }
    hour.update(changes)
    return hour


def test_full_marks_add_up_to_max_score():
    full_marks = (
        scoring.FEELS_LIKE_POINTS
        + scoring.RAIN_POINTS
        + scoring.WIND_POINTS
        + scoring.GUSTS_POINTS
        + scoring.CLOUD_POINTS
        + scoring.WAVES_CALM_POINTS
    )
    assert full_marks == scoring.MAX_SCORE


def test_perfect_hour_gets_max_score():
    assert score_hour(make_hour()) == scoring.MAX_SCORE


def test_worst_hour_scores_nothing():
    hour = make_hour(
        apparent_temperature=scoring.FEELS_LIKE_MIN - STEP,
        precipitation_probability=scoring.RAIN_CHANCE_LIMIT,
        wind_speed_10m=scoring.WIND_LIMIT,
        wind_gusts_10m=scoring.GUSTS_LIMIT,
        cloud_cover=scoring.CLOUD_LIMIT,
        wave_height=scoring.WAVES_MODERATE_MAX + STEP,
    )
    assert score_hour(hour) == 0


# Each row: the column, its value, and the points we expect to lose.
# The values sit right on the limits, where mistakes are most likely.
@pytest.mark.parametrize(
    "column, value, points_lost",
    [
        ("apparent_temperature", scoring.FEELS_LIKE_MIN - STEP, scoring.FEELS_LIKE_POINTS),
        ("apparent_temperature", scoring.FEELS_LIKE_MIN, 0),
        ("apparent_temperature", scoring.FEELS_LIKE_MAX, 0),
        ("apparent_temperature", scoring.FEELS_LIKE_MAX + STEP, scoring.FEELS_LIKE_POINTS),
        ("precipitation_probability", scoring.RAIN_CHANCE_LIMIT - STEP, 0),
        ("precipitation_probability", scoring.RAIN_CHANCE_LIMIT, scoring.RAIN_POINTS),
        ("wind_speed_10m", scoring.WIND_LIMIT - STEP, 0),
        ("wind_speed_10m", scoring.WIND_LIMIT, scoring.WIND_POINTS),
        ("wind_gusts_10m", scoring.GUSTS_LIMIT - STEP, 0),
        ("wind_gusts_10m", scoring.GUSTS_LIMIT, scoring.GUSTS_POINTS),
        ("cloud_cover", scoring.CLOUD_LIMIT - STEP, 0),
        ("cloud_cover", scoring.CLOUD_LIMIT, scoring.CLOUD_POINTS),
        ("wave_height", scoring.WAVES_CALM_LIMIT - STEP, 0),
        (
            "wave_height",
            scoring.WAVES_CALM_LIMIT,
            scoring.WAVES_CALM_POINTS - scoring.WAVES_MODERATE_POINTS,
        ),
        (
            "wave_height",
            scoring.WAVES_MODERATE_MAX,
            scoring.WAVES_CALM_POINTS - scoring.WAVES_MODERATE_POINTS,
        ),
        ("wave_height", scoring.WAVES_MODERATE_MAX + STEP, scoring.WAVES_CALM_POINTS),
    ],
)
def test_score_at_the_limits(column, value, points_lost):
    hour = make_hour(**{column: value})
    assert score_hour(hour) == scoring.MAX_SCORE - points_lost


def test_missing_value_earns_no_points():
    hour = make_hour(apparent_temperature=float("nan"))
    assert score_hour(hour) == scoring.MAX_SCORE - scoring.FEELS_LIKE_POINTS


@pytest.mark.parametrize(
    "score, expected",
    [
        (scoring.MAX_SCORE, "Go"),
        (scoring.GO_MIN_SCORE, "Go"),
        (scoring.GO_MIN_SCORE - 1, "Maybe"),
        (scoring.MAYBE_MIN_SCORE, "Maybe"),
        (scoring.MAYBE_MIN_SCORE - 1, "Stay home"),
    ],
)
def test_verdict(score, expected):
    assert get_verdict(score) == expected


# Wave categories


@pytest.mark.parametrize(
    "wave_height, expected",
    [
        (scoring.WAVES_CALM_LIMIT - STEP, "calm"),
        (scoring.WAVES_CALM_LIMIT, "moderate"),
        (scoring.WAVES_MODERATE_MAX, "moderate"),
        (scoring.WAVES_MODERATE_MAX + STEP, "rough"),
        (float("nan"), None),
    ],
)
def test_wave_category(wave_height, expected):
    assert get_wave_category(wave_height) == expected


# Sky categories


@pytest.mark.parametrize(
    "changes, expected",
    [
        ({"cloud_cover": scoring.CLOUD_LIMIT - STEP}, "sunny"),
        ({"cloud_cover": scoring.CLOUD_LIMIT}, "cloudy"),
        ({"precipitation_probability": scoring.DEAL_BREAKER_RAIN_CHANCE - STEP}, "sunny"),
        ({"precipitation_probability": scoring.DEAL_BREAKER_RAIN_CHANCE}, "rainy"),
        ({"time": BEFORE_SUNRISE}, "night"),
        ({"time": AFTER_SUNSET}, "night"),
        # Night comes first, even when rain is likely
        ({"time": AFTER_SUNSET, "precipitation_probability": scoring.DEAL_BREAKER_RAIN_CHANCE}, "night"),
        ({"cloud_cover": float("nan")}, None),
    ],
)
def test_sky_category(changes, expected):
    assert get_sky_category(make_hour(**changes), SUNRISE, SUNSET) == expected


# Wind categories


@pytest.mark.parametrize(
    "changes, expected",
    [
        ({}, "light"),
        ({"wind_speed_10m": scoring.WIND_LIMIT}, "breezy"),
        ({"wind_gusts_10m": scoring.GUSTS_LIMIT}, "breezy"),
        ({"wind_speed_10m": scoring.DEAL_BREAKER_WIND}, "breezy"),
        ({"wind_gusts_10m": scoring.DEAL_BREAKER_GUSTS}, "breezy"),
        ({"wind_speed_10m": scoring.DEAL_BREAKER_WIND + STEP}, "strong"),
        ({"wind_gusts_10m": scoring.DEAL_BREAKER_GUSTS + STEP}, "strong"),
        ({"wind_speed_10m": float("nan")}, None),
    ],
)
def test_wind_category(changes, expected):
    assert get_wind_category(make_hour(**changes)) == expected


# Night


@pytest.mark.parametrize("time", [BEFORE_SUNRISE, AFTER_SUNSET])
def test_hour_outside_daylight_is_night_with_no_score(time):
    assert rate_hour(make_hour(time=time), SUNRISE, SUNSET) == (None, "Night")


@pytest.mark.parametrize("time", [SUNRISE, MIDDAY, SUNSET])
def test_daylight_includes_sunrise_and_sunset(time):
    assert is_daylight(time, SUNRISE, SUNSET)


def test_night_beats_a_deal_breaker():
    hour = make_hour(
        time=AFTER_SUNSET,
        wind_speed_10m=scoring.DEAL_BREAKER_WIND + STEP,
    )
    assert rate_hour(hour, SUNRISE, SUNSET) == (None, "Night")


# Deal breakers

# Each row: the column and the lowest value that counts as a deal breaker
DEAL_BREAKERS = [
    ("precipitation_probability", scoring.DEAL_BREAKER_RAIN_CHANCE),
    ("wind_speed_10m", scoring.DEAL_BREAKER_WIND + STEP),
    ("wind_gusts_10m", scoring.DEAL_BREAKER_GUSTS + STEP),
    ("wave_height", scoring.DEAL_BREAKER_WAVES + STEP),
]


@pytest.mark.parametrize("column, value", DEAL_BREAKERS)
def test_deal_breaker_forces_stay_home_despite_the_score(column, value):
    hour = make_hour(**{column: value})
    score, verdict = rate_hour(hour, SUNRISE, SUNSET)

    assert verdict == "Stay home"
    # Without the deal breaker this score would have earned a better verdict
    assert get_verdict(score) != "Stay home"


# Each row: the column and the highest value that is not a deal breaker
JUST_UNDER_DEAL_BREAKERS = [
    ("precipitation_probability", scoring.DEAL_BREAKER_RAIN_CHANCE - STEP),
    ("wind_speed_10m", scoring.DEAL_BREAKER_WIND),
    ("wind_gusts_10m", scoring.DEAL_BREAKER_GUSTS),
    ("wave_height", scoring.DEAL_BREAKER_WAVES),
]


@pytest.mark.parametrize("column, value", JUST_UNDER_DEAL_BREAKERS)
def test_value_just_under_a_deal_breaker_is_allowed(column, value):
    assert not has_deal_breaker(make_hour(**{column: value}))


# Best window

# Before every hour of the test day, so no hour counts as already over
START_OF_DAY = "2026-11-02T00:00"

GO = "Go"
MAYBE = "Maybe"
HOME = "Stay home"
NIGHT = "Night"

# A score that fits each verdict
SCORE_FOR_VERDICT = {
    GO: scoring.GO_MIN_SCORE,
    MAYBE: scoring.MAYBE_MIN_SCORE,
    HOME: 0,
    NIGHT: None,
}


def make_day(verdicts, first_hour=8):
    """Consecutive rated hours, one for each verdict, starting at first_hour."""
    hours = []
    for offset, verdict in enumerate(verdicts):
        hours.append(
            make_hour(
                time=f"2026-11-02T{first_hour + offset:02d}:00",
                verdict=verdict,
                score=SCORE_FOR_VERDICT[verdict],
            )
        )
    return hours


@pytest.mark.parametrize(
    "verdicts",
    [
        [],
        [NIGHT, NIGHT],
        [NIGHT, HOME, HOME, HOME, NIGHT],
    ],
)
def test_day_with_no_good_hours_has_no_window(verdicts):
    assert find_best_window(make_day(verdicts), SUNRISE, SUNSET, START_OF_DAY) is None


def test_two_windows_picks_the_longer_one_even_when_it_is_later():
    day = make_day([GO, HOME, GO, GO, GO, HOME])
    window = find_best_window(day, SUNRISE, SUNSET, START_OF_DAY)

    assert window["start"] == "10:00"
    assert window["end"] == "13:00"


def test_two_equally_long_windows_picks_the_earlier_one():
    day = make_day([GO, GO, HOME, GO, GO])
    window = find_best_window(day, SUNRISE, SUNSET, START_OF_DAY)

    assert window["start"] == "08:00"
    assert window["end"] == "10:00"


def test_one_go_hour_beats_a_longer_run_of_maybe():
    day = make_day([MAYBE, MAYBE, MAYBE, HOME, GO, HOME])
    window = find_best_window(day, SUNRISE, SUNSET, START_OF_DAY)

    assert window["verdict"] == GO
    assert window["start"] == "12:00"
    assert window["end"] == "13:00"


def test_maybe_hours_are_used_when_no_hour_is_go():
    day = make_day([MAYBE, HOME, MAYBE, MAYBE, HOME])
    window = find_best_window(day, SUNRISE, SUNSET, START_OF_DAY)

    assert window["verdict"] == MAYBE
    assert window["start"] == "10:00"
    assert window["end"] == "12:00"


def test_a_maybe_hour_splits_two_go_windows():
    day = make_day([GO, GO, MAYBE, GO])
    window = find_best_window(day, SUNRISE, SUNSET, START_OF_DAY)

    assert window["start"] == "08:00"
    assert window["end"] == "10:00"


def test_window_can_run_right_up_to_the_last_hour_of_the_list():
    day = make_day([HOME, GO, GO])
    window = find_best_window(day, SUNRISE, SUNSET, START_OF_DAY)

    assert window["start"] == "09:00"
    assert window["end"] == "11:00"


def test_window_end_stops_at_sunset():
    # The 18:00 hour would finish at 19:00, but the sun sets at 18:30
    day = make_day([GO, GO], first_hour=17)
    assert find_best_window(day, SUNRISE, SUNSET, START_OF_DAY)["end"] == "18:30"


def test_average_score_only_counts_hours_in_the_window():
    day = make_day([GO, GO, HOME])
    day[0]["score"] = scoring.MAX_SCORE
    day[1]["score"] = scoring.GO_MIN_SCORE

    window = find_best_window(day, SUNRISE, SUNSET, START_OF_DAY)

    assert window["average_score"] == (scoring.MAX_SCORE + scoring.GO_MIN_SCORE) / 2


def test_reason_describes_the_conditions():
    day = make_day([GO])
    day[0]["apparent_temperature"] = 21

    window = find_best_window(day, SUNRISE, SUNSET, START_OF_DAY)

    assert window["reason"] == "sunny, calm sea, light wind, feels like 21 °C"


def test_reason_uses_the_worst_sky_sea_and_wind_and_the_average_temperature():
    day = make_day([GO, GO])
    day[0]["apparent_temperature"] = 20
    day[1]["apparent_temperature"] = 24
    day[1]["cloud_cover"] = scoring.CLOUD_LIMIT
    day[1]["wave_height"] = scoring.WAVES_CALM_LIMIT
    day[1]["wind_speed_10m"] = scoring.WIND_LIMIT

    window = find_best_window(day, SUNRISE, SUNSET, START_OF_DAY)

    assert window["reason"] == "cloudy, moderate sea, breezy wind, feels like 22 °C"


def test_reason_skips_missing_values():
    day = make_day([MAYBE, MAYBE])
    day[0]["apparent_temperature"] = float("nan")
    day[1]["apparent_temperature"] = 21
    for hour in day:
        hour["cloud_cover"] = float("nan")
        hour["wave_height"] = float("nan")

    window = find_best_window(day, SUNRISE, SUNSET, START_OF_DAY)

    assert window["reason"] == "light wind, feels like 21 °C"


# Each row: the rain chance in each hour of a two-hour window, and the text we expect
@pytest.mark.parametrize(
    "rain_chances, expected",
    [
        # Below the limit in every hour: not mentioned
        ([scoring.RAIN_CHANCE_LIMIT - STEP, 0], None),
        # Exactly on the limit counts
        ([scoring.RAIN_CHANCE_LIMIT, 0], "20% chance of rain"),
        # The highest is used, wherever it falls in the window
        ([40, 30], "40% chance of rain"),
        ([30, 40], "40% chance of rain"),
        # A missing value is skipped, wherever it falls in the window
        ([float("nan"), 40], "40% chance of rain"),
        ([40, float("nan")], "40% chance of rain"),
        ([float("nan"), float("nan")], None),
    ],
)
def test_reason_mentions_the_highest_rain_chance(rain_chances, expected):
    day = make_day([MAYBE, MAYBE])
    day[0]["precipitation_probability"] = rain_chances[0]
    day[1]["precipitation_probability"] = rain_chances[1]

    window = find_best_window(day, SUNRISE, SUNSET, START_OF_DAY)

    if expected is None:
        assert "rain" not in window["reason"]
    else:
        assert expected in window["reason"]


def test_rain_chance_comes_right_after_the_sky():
    day = make_day([MAYBE])
    day[0]["precipitation_probability"] = 40
    day[0]["apparent_temperature"] = 21

    window = find_best_window(day, SUNRISE, SUNSET, START_OF_DAY)

    assert window["reason"] == (
        "sunny, 40% chance of rain, calm sea, light wind, feels like 21 °C"
    )


def test_rain_outside_the_window_is_not_mentioned():
    day = make_day([GO, GO, HOME])
    day[2]["precipitation_probability"] = scoring.DEAL_BREAKER_RAIN_CHANCE

    window = find_best_window(day, SUNRISE, SUNSET, START_OF_DAY)

    assert "rain" not in window["reason"]


# Best window: only the hours still to come


def test_window_already_over_is_ignored():
    day = make_day([GO, GO, GO, HOME, GO])
    window = find_best_window(day, SUNRISE, SUNSET, "2026-11-02T11:00")

    assert window["start"] == "12:00"
    assert window["end"] == "13:00"


def test_window_under_way_starts_at_the_current_hour():
    day = make_day([GO, GO, GO, HOME])
    window = find_best_window(day, SUNRISE, SUNSET, "2026-11-02T09:00")

    assert window["start"] == "09:00"
    assert window["end"] == "11:00"


def test_only_the_part_of_a_window_still_to_come_counts_towards_its_length():
    # At 10:00 the morning run has 1 hour left and the later run has 2
    day = make_day([GO, GO, GO, HOME, GO, GO])
    window = find_best_window(day, SUNRISE, SUNSET, "2026-11-02T10:00")

    assert window["start"] == "12:00"
    assert window["end"] == "14:00"


def test_average_score_only_counts_hours_still_to_come():
    day = make_day([GO, GO])
    day[0]["score"] = scoring.GO_MIN_SCORE
    day[1]["score"] = scoring.MAX_SCORE

    window = find_best_window(day, SUNRISE, SUNSET, "2026-11-02T09:00")

    assert window["average_score"] == scoring.MAX_SCORE


def test_maybe_is_used_when_all_the_go_hours_are_over():
    day = make_day([GO, GO, HOME, MAYBE])
    window = find_best_window(day, SUNRISE, SUNSET, "2026-11-02T10:00")

    assert window["verdict"] == MAYBE
    assert window["start"] == "11:00"


def test_evening_with_nothing_left_has_no_window():
    day = make_day([GO, GO, GO, NIGHT, NIGHT], first_hour=16)
    assert find_best_window(day, SUNRISE, SUNSET, "2026-11-02T19:00") is None


def test_only_bad_hours_left_has_no_window():
    day = make_day([GO, GO, HOME, HOME])
    assert find_best_window(day, SUNRISE, SUNSET, "2026-11-02T10:00") is None


# Message when there is no window


@pytest.mark.parametrize(
    "verdicts",
    [
        [],
        [NIGHT, NIGHT],
        [NIGHT, HOME, HOME, NIGHT],
    ],
)
def test_message_when_the_whole_day_had_no_good_hours(verdicts):
    assert get_no_window_message(make_day(verdicts)) == "No good beach time today."


@pytest.mark.parametrize(
    "verdicts",
    [
        [GO, HOME, NIGHT],
        [MAYBE, HOME, NIGHT],
    ],
)
def test_message_when_good_hours_have_passed(verdicts):
    assert get_no_window_message(make_day(verdicts)) == "No more good beach time today."
