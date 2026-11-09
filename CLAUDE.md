# Beach Day: Playa de San Juan

A small Streamlit web app that tells me whether today is a good beach day at Playa de San Juan (Alicante, Spain), hour by hour, using free Open-Meteo weather and sea forecasts. It shows the best beach window for the rest of the day, an hourly strip, a score chart and original 16-bit pixel-art tiles for the sky, waves and wind.

## Rules
- Work only on the step I ask for. Don't build ahead.
- Keep the code simple. I'm learning and must be able to explain every line.
- After each step, briefly explain what you did and why, then stop.
- Don't commit. I'll commit myself.
- Out of scope unless I ask: historical data, other beaches, accounts, notifications.

## Current goal: move from Streamlit to a static site
The live app moves from Streamlit Community Cloud to GitHub Pages, so it never sleeps.
- A GitHub Action runs every hour: runs the tests, runs the Python pipeline, and
  writes the results to `site/forecast.json`, then deploys `site/` to GitHub Pages.
- `site/` is a plain static page (HTML, CSS, a little JavaScript, no framework)
  that only displays forecast.json. All scoring stays in Python.
- The page shows the forecast as of the last hourly run, with the update time.