from pathlib import Path

import pandas as pd
import streamlit as st

from combine import build_table
from fetch import get_sun_times
from scoring import (
    MAX_SCORE,
    find_best_window,
    get_no_window_message,
    get_sky_category,
    get_wave_category,
    get_wind_category,
)

ASSETS = Path(__file__).parent / "assets"

st.title("Beach Day: Playa de San Juan")

sunrise, sunset = get_sun_times()
table = build_table(sunrise, sunset)

# The current hour in Madrid, written the same way as the table's "time" column
current_time = pd.Timestamp.now(tz="Europe/Madrid").strftime("%Y-%m-%dT%H:00")

# to_dict("records") turns the table into a list with one dictionary per row
hours = table.to_dict("records")
window = find_best_window(hours, sunrise, sunset, current_time)

if window is None:
    st.warning(get_no_window_message(hours))
else:
    st.header(f"Best time today: {window['start']} to {window['end']}")
    st.write(
        f"{window['verdict']}, average score "
        f"{window['average_score']:.1f} / {MAX_SCORE}: {window['reason']}"
    )

current_rows =table[table["time"] == current_time]

if current_rows.empty:
    st.warning(f"No forecast found for {current_time}.")
else:
    current = current_rows.iloc[0]
    st.header(f"Right now: {current['verdict']}")
    if current["verdict"] != "Night":  # night hours have no score
        st.write(f"Score: {current['score']} / {MAX_SCORE}")

    # Each entry: the folder of GIFs, and the category for the current hour
    tiles = [
        ("sky", get_sky_category(current, sunrise, sunset)),
        ("wind", get_wind_category(current)),
        ("waves", get_wave_category(current["wave_height"])),
    ]

    columns = st.columns(len(tiles))
    for column, (folder, category) in zip(columns, tiles):
        if category is not None:  # None means the data is missing
            gif_path = ASSETS / folder / f"{category}.gif"
            column.image(str(gif_path), caption=f"{folder.title()}: {category}")

# [11:] skips the date, leaving just the time, like "07:29"
st.write(f"Sunrise: {sunrise[11:]}  |  Sunset: {sunset[11:]}")

st.dataframe(table, hide_index=True)
