import altair as alt
import pandas as pd

from scoring import MAX_SCORE, get_sky_category

# The green is lighter than the red so that people with red-green colour
# blindness can still tell them apart
VERDICT_COLORS = {
    "Go": "#38BE74",  # green
    "Maybe": "#C98A06",  # amber
    "Stay home": "#C23534",  # red
}

LINE_COLOR = "#3B6FE0"  # blue, so the line doesn't look like a verdict

SKY_EMOJIS = {
    "sunny": "☀️",
    "cloudy": "☁️",
    "rainy": "🌧️",
}

# The name to show for each column of the combined table
COLUMN_NAMES = {
    "time": "Time",
    "temperature_2m": "Temperature (°C)",
    "apparent_temperature": "Feels like (°C)",
    "precipitation_probability": "Rain chance (%)",
    "cloud_cover": "Cloud cover (%)",
    "wind_speed_10m": "Wind (km/h)",
    "wind_gusts_10m": "Gusts (km/h)",
    "uv_index": "UV index",
    "wave_height": "Wave height (m)",
    "wave_period": "Wave period (s)",
    "wave_direction": "Wave direction (°)",
    "score": "Score",
    "verdict": "Verdict",
}

# Shown when a value is missing
NO_DATA = "–"

# overflow-x lets the row of cards scroll sideways on a narrow screen
STRIP_STYLE = """
<style>
.strip { display: flex; gap: 6px; overflow-x: auto; padding-bottom: 6px; }
.card {
    flex: 1 0 54px;
    padding: 8px 2px;
    text-align: center;
    border: 1px solid rgba(128, 128, 128, 0.3);
    border-radius: 8px;
}
.card-time { font-size: 0.8rem; }
.card-sky { font-size: 1.4rem; }
.card-dot {
    display: inline-block;
    width: 10px;
    height: 10px;
    border-radius: 50%;
}
</style>
"""


def get_daylight_rows(table):
    """Return only the rows of the combined table that are in daylight."""
    return table[table["verdict"] != "Night"]


def build_hour_card(hour, sunrise, sunset):
    """Return the HTML for one hour's card in the strip."""
    sky = get_sky_category(hour, sunrise, sunset)
    emoji = SKY_EMOJIS.get(sky, NO_DATA)  # get uses NO_DATA if sky isn't in the list

    feels_like = hour["apparent_temperature"]
    temperature = NO_DATA if pd.isna(feels_like) else f"{feels_like:.0f}°"

    verdict = hour["verdict"]
    color = VERDICT_COLORS[verdict]

    # title shows the verdict on hover, so the dot doesn't rely on colour alone
    return f"""
    <div class="card">
        <div class="card-time">{hour["time"][11:]}</div>
        <div class="card-sky">{emoji}</div>
        <div>{temperature}</div>
        <span class="card-dot" style="background: {color}" title="{verdict}"></span>
    </div>
    """


def build_hourly_strip(table, sunrise, sunset):
    """Return the HTML for a row of cards, one for each daylight hour."""
    cards = ""
    for _, hour in get_daylight_rows(table).iterrows():
        cards += build_hour_card(hour, sunrise, sunset)
    return f'{STRIP_STYLE}<div class="strip">{cards}</div>'


def build_chart_data(table):
    """Return the daylight hours, with just the columns the chart needs."""
    daylight = get_daylight_rows(table)
    return pd.DataFrame(
        {
            "Time": daylight["time"].str[11:],  # [11:] skips the date
            "Score": daylight["score"].astype(int),
            "Verdict": daylight["verdict"],
            "Feels like": daylight["apparent_temperature"],
        }
    )


def build_score_chart(table, window):
    """Return a chart of score bars and a feels-like line, shading the best window."""
    data = build_chart_data(table)

    # All the layers share this x axis: one equal slot per hour, in time order.
    # No padding between slots, so the shading has no gaps in it.
    x = alt.X(
        "Time:N",
        title=None,
        scale=alt.Scale(domain=list(data["Time"]), paddingInner=0, paddingOuter=0),
        # labelFlush=False keeps the first and last labels centred under their bars
        axis=alt.Axis(labelAngle=0, labelOverlap="greedy", labelFlush=False),
    )

    # What appears when you hover over a bar or a point on the line
    tooltip = [
        alt.Tooltip("Time:N"),
        alt.Tooltip("Verdict:N"),
        alt.Tooltip("Score:Q"),
        alt.Tooltip("Feels like:Q", title="Feels like (°C)", format=".0f"),
    ]

    # Layer 1: bars. The bar is 70% of its slot, which leaves a gap between bars.
    bars = (
        alt.Chart(data)
        .mark_bar(
            width=alt.RelativeBandSize(0.7),
            cornerRadiusTopLeft=4,
            cornerRadiusTopRight=4,
        )
        .encode(
            x=x,
            y=alt.Y(
                "Score:Q",
                title="Beach score (bars)",
                scale=alt.Scale(domain=[0, MAX_SCORE]),
            ),
            color=alt.Color(
                "Verdict:N",
                title=None,
                scale=alt.Scale(
                    domain=list(VERDICT_COLORS),
                    range=list(VERDICT_COLORS.values()),
                ),
                legend=alt.Legend(orient="top"),
            ),
            tooltip=tooltip,
        )
    )

    # Layer 2: the line. zero=False lets the axis fit the temperatures, not start at 0.
    line = (
        alt.Chart(data)
        .mark_line(
            color=LINE_COLOR,
            strokeWidth=2,
            point=alt.OverlayMarkDef(color=LINE_COLOR, size=50),
        )
        .encode(
            x=x,
            y=alt.Y(
                "Feels like:Q",
                title="Feels like °C (line)",
                scale=alt.Scale(zero=False),
                axis=alt.Axis(orient="right", grid=False),
            ),
            tooltip=tooltip,
        )
    )

    layers = [bars, line]
    title = "Beach score and feels-like temperature"

    if window is not None:
        # Times written as "HH:MM" sort in time order, so we can compare them directly
        in_window = (data["Time"] >= window["start"]) & (data["Time"] < window["end"])

        # With no y, each rectangle fills the chart's full height
        shading = (
            alt.Chart(data[in_window])
            .mark_rect(color="gray", opacity=0.2)
            .encode(x=x)
        )
        layers = [shading, bars, line]  # first in the list is drawn at the back
        title = alt.TitleParams(
            title,
            subtitle=f"Shaded: best time left today, {window['start']} to {window['end']}",
            subtitleColor="gray",  # readable on both light and dark pages
        )

    # "independent" gives the bars and the line a y axis each, instead of sharing one
    return (
        alt.layer(*layers, title=title)
        .resolve_scale(y="independent")
        .properties(height=300)
    )


def build_data_table(table):
    """Return the full table with readable column names and times like "13:00"."""
    data = table.rename(columns=COLUMN_NAMES)
    data["Time"] = data["Time"].str[11:]  # [11:] skips the date
    return data
