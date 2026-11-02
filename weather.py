import pandas as pd
import requests

URL = "https://api.open-meteo.com/v1/forecast"

params = {
    "latitude": 38.37,
    "longitude": -0.41,
    "hourly": [
        "temperature_2m",
        "apparent_temperature",
        "precipitation_probability",
        "cloud_cover",
        "wind_speed_10m",
        "wind_gusts_10m",
        "uv_index",
    ],
    "timezone": "Europe/Madrid",
    "forecast_days": 1,  # only today
}

response = requests.get(URL, params=params, timeout=10)
response.raise_for_status()  # stop with an error if the request failed

data = response.json()
table = pd.DataFrame(data["hourly"])

print(table.to_string(index=False))
