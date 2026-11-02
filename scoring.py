# What counts as good beach weather
FEELS_LIKE_MIN = 20  # °C, this value counts as good
FEELS_LIKE_MAX = 32  # °C, this value counts as good
WIND_LIMIT = 20  # km/h, must be under this
GUSTS_LIMIT = 35  # km/h, must be under this
RAIN_CHANCE_LIMIT = 20  # %, must be under this
CLOUD_LIMIT = 50  # %, must be under this
WAVES_CALM_LIMIT = 0.5  # m, under this is calm
WAVES_MODERATE_MAX = 1.0  # m, up to and including this is moderate, above is rough

# Deal breakers: any one of these forces "Stay home", whatever the score
DEAL_BREAKER_RAIN_CHANCE = 50  # %, this value or more
DEAL_BREAKER_WIND = 30  # km/h, over this
DEAL_BREAKER_GUSTS = 50  # km/h, over this
DEAL_BREAKER_WAVES = WAVES_MODERATE_MAX  # m, over this, which means rough

# Points for each rule (the full marks add up to MAX_SCORE)
MAX_SCORE = 10
FEELS_LIKE_POINTS = 3
RAIN_POINTS = 2
WIND_POINTS = 1
GUSTS_POINTS = 1
CLOUD_POINTS = 1
WAVES_CALM_POINTS = 2
WAVES_MODERATE_POINTS = 1

# Lowest score that earns each verdict
GO_MIN_SCORE = 9
MAYBE_MIN_SCORE = 6


def score_hour(hour):
    """Return a score from 0 to 10 for one hour of the combined table."""
    score = 0

    if FEELS_LIKE_MIN <= hour["apparent_temperature"] <= FEELS_LIKE_MAX:
        score += FEELS_LIKE_POINTS
    if hour["precipitation_probability"] < RAIN_CHANCE_LIMIT:
        score += RAIN_POINTS
    if hour["wind_speed_10m"] < WIND_LIMIT:
        score += WIND_POINTS
    if hour["wind_gusts_10m"] < GUSTS_LIMIT:
        score += GUSTS_POINTS
    if hour["cloud_cover"] < CLOUD_LIMIT:
        score += CLOUD_POINTS

    if hour["wave_height"] < WAVES_CALM_LIMIT:
        score += WAVES_CALM_POINTS
    elif hour["wave_height"] <= WAVES_MODERATE_MAX:
        score += WAVES_MODERATE_POINTS

    return score


def get_verdict(score):
    """Turn a score into Go, Maybe or Stay home."""
    if score >= GO_MIN_SCORE:
        return "Go"
    if score >= MAYBE_MIN_SCORE:
        return "Maybe"
    return "Stay home"


def is_daylight(time, sunrise, sunset):
    """Check if a time is between sunrise and sunset.

    All three are text like "2026-11-02T08:00". Text in this format sorts in
    time order, so we can compare it directly.
    """
    return sunrise <= time <= sunset


def has_deal_breaker(hour):
    """Check if one hour has conditions bad enough to rule out the beach."""
    return (
        hour["precipitation_probability"] >= DEAL_BREAKER_RAIN_CHANCE
        or hour["wind_speed_10m"] > DEAL_BREAKER_WIND
        or hour["wind_gusts_10m"] > DEAL_BREAKER_GUSTS
        or hour["wave_height"] > DEAL_BREAKER_WAVES
    )


def rate_hour(hour, sunrise, sunset):
    """Return the score and verdict for one hour of the combined table."""
    if not is_daylight(hour["time"], sunrise, sunset):
        return None, "Night"

    score = score_hour(hour)
    if has_deal_breaker(hour):
        return score, "Stay home"
    return score, get_verdict(score)
