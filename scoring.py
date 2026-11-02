import math

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

    wave_category = get_wave_category(hour["wave_height"])
    if wave_category == "calm":
        score += WAVES_CALM_POINTS
    elif wave_category == "moderate":
        score += WAVES_MODERATE_POINTS

    return score


def get_wave_category(wave_height):
    """Return "calm", "moderate" or "rough", or None if the height is missing."""
    if wave_height < WAVES_CALM_LIMIT:
        return "calm"
    if wave_height <= WAVES_MODERATE_MAX:
        return "moderate"
    if wave_height > WAVES_MODERATE_MAX:
        return "rough"
    return None  # a missing value (NaN) fails every comparison above


def get_sky_category(hour, sunrise, sunset):
    """Return "night", "rainy", "sunny" or "cloudy", or None if data is missing."""
    if not is_daylight(hour["time"], sunrise, sunset):
        return "night"
    if hour["precipitation_probability"] >= DEAL_BREAKER_RAIN_CHANCE:
        return "rainy"
    if hour["cloud_cover"] < CLOUD_LIMIT:
        return "sunny"
    if hour["cloud_cover"] >= CLOUD_LIMIT:
        return "cloudy"
    return None  # a missing value (NaN) fails every comparison above


def get_wind_category(hour):
    """Return "strong", "breezy" or "light", or None if data is missing."""
    wind = hour["wind_speed_10m"]
    gusts = hour["wind_gusts_10m"]

    if wind > DEAL_BREAKER_WIND or gusts > DEAL_BREAKER_GUSTS:
        return "strong"
    if wind >= WIND_LIMIT or gusts >= GUSTS_LIMIT:
        return "breezy"
    if wind < WIND_LIMIT and gusts < GUSTS_LIMIT:
        return "light"
    return None  # a missing value (NaN) fails every comparison above


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


def split_into_runs(hours, verdict):
    """Return a list of runs, where a run is consecutive hours with this verdict."""
    runs = []
    current_run = []

    for hour in hours:
        if hour["verdict"] == verdict:
            current_run.append(hour)
        elif current_run:  # a different verdict ends the run we were building
            runs.append(current_run)
            current_run = []

    if current_run:  # the day ended while a run was still going
        runs.append(current_run)

    return runs


def get_worst_category(categories, worst_first):
    """Return the first of worst_first found in categories, or None if none are."""
    for category in worst_first:
        if category in categories:
            return category
    return None


def describe_window(hours, sunrise, sunset):
    """Build a short reason like "sunny, calm sea, light wind, feels like 21 °C".

    Sky, sea and wind describe the window's worst hour, so "calm sea" means calm
    throughout. The rain chance only appears when it's high enough to lose points.
    Anything with no data at all is left out.
    """
    parts = []

    sky_categories = [get_sky_category(hour, sunrise, sunset) for hour in hours]
    sky = get_worst_category(sky_categories, ["rainy", "cloudy", "sunny"])
    if sky is not None:
        parts.append(sky)

    # A missing value (NaN) fails this comparison, so it never gets into the list
    rain_chances = [
        hour["precipitation_probability"]
        for hour in hours
        if hour["precipitation_probability"] >= RAIN_CHANCE_LIMIT
    ]
    if rain_chances:
        parts.append(f"{max(rain_chances):.0f}% chance of rain")

    wave_categories = [get_wave_category(hour["wave_height"]) for hour in hours]
    sea = get_worst_category(wave_categories, ["rough", "moderate", "calm"])
    if sea is not None:
        parts.append(f"{sea} sea")

    wind_categories = [get_wind_category(hour) for hour in hours]
    wind = get_worst_category(wind_categories, ["strong", "breezy", "light"])
    if wind is not None:
        parts.append(f"{wind} wind")

    temperatures = [hour["apparent_temperature"] for hour in hours]
    temperatures = [value for value in temperatures if not math.isnan(value)]
    if temperatures:
        average = sum(temperatures) / len(temperatures)
        parts.append(f"feels like {average:.0f} °C")

    return ", ".join(parts)


def get_window_end(last_hour, sunset):
    """Return when the last hour finishes, like "16:00", but no later than sunset."""
    # [11:13] picks the hour out of text like "2026-11-02T15:00"
    next_hour = int(last_hour["time"][11:13]) + 1
    end = f"{next_hour:02d}:00"
    # Times written as "HH:MM" sort in time order, so min gives the earlier one
    return min(end, sunset[11:])


def find_best_window(hours, sunrise, sunset, current_time):
    """Return the best beach window left today as a dictionary, or None if none is.

    hours is a list of rows from the combined table, in time order. current_time
    is the current hour, written like the "time" column: "2026-11-02T13:00".
    Earlier hours are ignored, so a window already under way starts at current_time.

    The best window is the longest run of "Go" hours, or of "Maybe" hours if no
    remaining hour is "Go". If two runs are equally long, the earlier one wins.
    """
    # Text in this format sorts in time order, so we can compare it directly
    remaining_hours = [hour for hour in hours if hour["time"] >= current_time]

    for verdict in ["Go", "Maybe"]:
        runs = split_into_runs(remaining_hours, verdict)
        if runs:
            best_run = max(runs, key=len)  # max keeps the first of any ties
            scores = [hour["score"] for hour in best_run]
            return {
                "verdict": verdict,
                "start": best_run[0]["time"][11:],  # [11:] skips the date
                "end": get_window_end(best_run[-1], sunset),
                "average_score": sum(scores) / len(scores),
                "reason": describe_window(best_run, sunrise, sunset),
            }
    return None


def get_no_window_message(hours):
    """Return what to say when find_best_window finds no window.

    hours is the whole day, so any good hours in it must have already passed.
    """
    verdicts = [hour["verdict"] for hour in hours]
    if "Go" in verdicts or "Maybe" in verdicts:
        return "No more good beach time today."
    return "No good beach time today."
