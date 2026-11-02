import pandas as pd
import requests
import streamlit as st

WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
SEA_URL = "https://marine-api.open-meteo.com/v1/marine"
CACHE_SECONDS = 3600  # keep each Open-Meteo response for 1 hour


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

    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()  # stop with an error if the request failed

    table = pd.DataFrame(response.json()["hourly"])

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

    response = requests.get(WEATHER_URL, params=params, timeout=10)
    response.raise_for_status()  # stop with an error if the request failed

    daily = response.json()["daily"]
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
