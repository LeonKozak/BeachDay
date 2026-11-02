import pytest

import scoring
from scoring import get_verdict, has_deal_breaker, is_daylight, rate_hour, score_hour

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
