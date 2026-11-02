import pandas as pd

from fetch import get_sea, get_sun_times, get_weather
from scoring import rate_hour

weather = get_weather()
sea = get_sea()
sunrise, sunset = get_sun_times()

# Put rows together where the "time" value is the same in both tables
table = pd.merge(weather, sea, on="time")

# A time found in only one table gets dropped by the merge, so compare row counts
if len(table) != len(weather) or len(table) != len(sea):
    print(
        "Warning: row counts differ, rows may have been lost in the merge "
        f"(weather: {len(weather)}, sea: {len(sea)}, merged: {len(table)})"
    )

scores = []
verdicts = []
for _, hour in table.iterrows():
    score, verdict = rate_hour(hour, sunrise, sunset)
    scores.append(score)
    verdicts.append(verdict)

# "Int64" keeps whole numbers and allows blanks, which appear as <NA> at night
table["score"] = pd.array(scores, dtype="Int64")
table["verdict"] = verdicts

print("Sunrise:", sunrise, " Sunset:", sunset)
print(table.to_string(index=False))
