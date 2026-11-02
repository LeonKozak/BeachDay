import time

import pandas as pd
import requests
import streamlit as st

WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
SEA_URL = "https://marine-api.open-meteo.com/v1/marine"
CACHE_SECONDS = 3600  # keep each Open-Meteo response for 1 hour
RETRY_WAITS = [1, 2, 4]  # seconds to wait before each retry


def is_worth_retrying(error):
    """Return True for problems that may clear up: timeouts, lost connections, 5xx."""
    if isinstance(error, requests.exceptions.HTTPError):
        return error.response.status_code >= 500
    return isinstance(
        error, (requests.exceptions.Timeout, requests.exceptions.ConnectionError)
    )


def request_json(url, params):
    """Make one request to Open-Meteo and return the JSON it sends back."""
    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()  # stop with an error if the request failed
    return response.json()


def request_json_with_retries(url, params):
    """Like request_json, but retry when the problem may clear up.

    That's one first try plus one retry for each wait in RETRY_WAITS. If the last
    try also fails, its error goes up to whoever called this.
    """
    for wait in RETRY_WAITS:
        try:
            return request_json(url, params)
        except requests.exceptions.RequestException as error:
            if not is_worth_retrying(error):
                raise  # trying again wouldn't help, so pass the error on now
            print(f"Request failed, retrying in {wait}s: {error}")
        time.sleep(wait)

    return request_json(url, params)  # the last try


@st.cache_data(ttl=CACHE_SECONDS)
def get_hourly(url, latitude, longitude, variables):
    """Ask Open-Meteo for today's hourly values and return them as a table."""
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": variables,
        "timezone": "Europe/Madrid",
        "forecast_days": 1,  # only today
    }

    table = pd.DataFrame(request_json_with_retries(url, params)["hourly"])

    # Count missing values per column and keep only columns that have some
    missing = table.isna().sum()
    missing = missing[missing > 0]
    if not missing.empty:
        print("Warning: missing values from", url)
        print(missing.to_string())

    return table


@st.cache_data(ttl=CACHE_SECONDS)
def get_sun_times():
    """Today's sunrise and sunset at the beach, as text in local time."""
    params = {
        "latitude": 38.37,
        "longitude": -0.41,
        "daily": ["sunrise", "sunset"],
        "timezone": "Europe/Madrid",
        "forecast_days": 1,  # only today
    }

    daily = request_json_with_retries(WEATHER_URL, params)["daily"]
    return daily["sunrise"][0], daily["sunset"][0]  # [0] is the first day: today


def get_weather():
    """Today's hourly weather at the beach."""
    variables = [
        "temperature_2m",
        "apparent_temperature",
        "precipitation_probability",
        "cloud_cover",
        "wind_speed_10m",
        "wind_gusts_10m",
        "uv_index",
    ]
    return get_hourly(WEATHER_URL, 38.37, -0.41, variables)


def get_sea():
    """Today's hourly waves out to sea, due east of the beach."""
    variables = ["wave_height", "wave_period", "wave_direction"]
    return get_hourly(SEA_URL, 38.375, -0.29, variables)
