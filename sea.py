import pandas as pd
import requests

URL = "https://marine-api.open-meteo.com/v1/marine"

params = {
    "latitude": 38.375,  # out to sea, due east of the beach
    "longitude": -0.29,
    "hourly": ["wave_height", "wave_period", "wave_direction"],
    "timezone": "Europe/Madrid",
    "forecast_days": 1,  # only today
}

response = requests.get(URL, params=params, timeout=10)
response.raise_for_status()  # stop with an error if the request failed

data = response.json()
table = pd.DataFrame(data["hourly"])

# The API uses the nearest point on its own grid, so show which one we got
print("Grid point used:", data["latitude"], data["longitude"])
print()
print(table.to_string(index=False))
print()
print("Missing values per column:")
print(table.isna().sum().to_string())
