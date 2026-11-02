from pathlib import Path

import pandas as pd
import streamlit as st

from combine import build_table
from fetch import get_sun_times
from scoring import MAX_SCORE, get_wave_category

st.title("Beach Day: Playa de San Juan")

sunrise, sunset = get_sun_times()
table = build_table(sunrise, sunset)

# The current hour in Madrid, written the same way as the table's "time" column
current_time = pd.Timestamp.now(tz="Europe/Madrid").strftime("%Y-%m-%dT%H:00")
current_rows = table[table["time"] == current_time]

if current_rows.empty:
    st.warning(f"No forecast found for {current_time}.")
else:
    current = current_rows.iloc[0]
    st.header(f"Right now: {current['verdict']}")
    if current["verdict"] != "Night":  # night hours have no score
        st.write(f"Score: {current['score']} / {MAX_SCORE}")

    wave_category = get_wave_category(current["wave_height"])
    if wave_category is not None:  # None means the wave height is missing
        gif_path = Path(__file__).parent / "assets" / "waves" / f"{wave_category}.gif"
        st.image(str(gif_path), caption=f"Waves: {wave_category}")

# [11:] skips the date, leaving just the time, like "07:29"
st.write(f"Sunrise: {sunrise[11:]}  |  Sunset: {sunset[11:]}")

st.dataframe(table, hide_index=True)
