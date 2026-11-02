import pandas as pd

from fetch import get_sea, get_weather

weather = get_weather()
sea = get_sea()

# Put rows together where the "time" value is the same in both tables
table = pd.merge(weather, sea, on="time")

# A time found in only one table gets dropped by the merge, so compare row counts
if len(table) != len(weather) or len(table) != len(sea):
    print(
        "Warning: row counts differ, rows may have been lost in the merge "
        f"(weather: {len(weather)}, sea: {len(sea)}, merged: {len(table)})"
    )

print(table.to_string(index=False))
