# Beach Day: Playa de San Juan

A small Streamlit web app that tells you whether today is a good beach day at Playa de San Juan (Alicante, Spain), using free Open-Meteo forecasts.

<!-- Replace the line below with a real screenshot, e.g. ![The Beach Day app](screenshot.png) -->
*Screenshot coming soon.*

## How the beach score works

Each hour of the day is rated in three steps, in this order.

### 1. Night

Any hour outside sunrise to sunset is marked "Night" and gets no score.

### 2. Points

Each daylight hour gets a score out of 10:

| Condition | Rule | Points |
|---|---|---|
| Feels-like temperature | 20 to 32 °C | 3 |
| Rain chance | under 20% | 2 |
| Wind | under 20 km/h | 1 |
| Gusts | under 35 km/h | 1 |
| Cloud cover | under 50% | 1 |
| Waves | calm: under 0.5 m | 2 |
| | moderate: 0.5 to 1.0 m | 1 |

A missing value earns no points.

The score gives the verdict:

| Score | Verdict |
|---|---|
| 9 to 10 | Go |
| 6 to 8 | Maybe |
| 0 to 5 | Stay home |

### 3. Deal breakers

Any one of these makes the hour "Stay home", whatever its score:

- Rain chance of 50% or more
- Wind over 30 km/h
- Gusts over 50 km/h
- Waves over 1.0 m

## Run it locally

You need Python 3.11 or newer.

```
git clone https://github.com/LeonKozak/BeachDay.git
cd BeachDay
pip install -r requirements.txt
streamlit run app.py
```

To run the tests:

```
python -m pytest
```

## Data source

All forecasts come from [Open-Meteo](https://open-meteo.com/), which is free and needs no API key: the [Weather Forecast API](https://open-meteo.com/en/docs) for weather, sunrise and sunset, and the [Marine Weather API](https://open-meteo.com/en/docs/marine-weather-api) for waves. The app keeps each response for 1 hour, so a page refresh doesn't call the API again.

**Limitation: the waves are not measured at the beach.** The marine forecast uses a coarse grid with no point at the beach itself. Asking for the beach's coordinates returns a point about 9 km to the south, so the app asks for a point due east of the beach instead, about 10 km out to sea. Waves at the shore can differ from open water, especially close in where they break, so treat the wave rating as a guide and not as a measurement of the shoreline.

## How I built this

I built this app with [Claude Code](https://claude.com/claude-code), one small step at a time. I'm learning, so the rules in [CLAUDE.md](CLAUDE.md) keep the work at a pace I can follow:

- Work only on the step I ask for, and don't build ahead.
- Keep the code simple enough that I can explain every line.
- After each step, explain what was done and why, then stop.
- Claude doesn't commit. I commit each step myself.

The app grew in this order:

1. Fetch the hourly weather forecast.
2. Fetch the sea forecast for the offshore point.
3. Combine the two, with checks for missing values and lost rows.
4. Add the beach score, with the daylight rule and deal breakers.
5. Add animations for the wave, sky and wind conditions.
6. Show the best time window for the day.
7. Replace the big table with an hourly strip and a chart.
8. Prepare the app for deployment.

Working this way also made it easy to correct things as I went. For example, the best window first covered the whole day, so it could show a time that had already passed. In the next step I asked for it to consider only the hours still to come, and for tests that cover a window that's already over.
