// Shows the forecast from forecast.json. All the scoring was already done in Python.

// Put text into the element with this id
function setText(id, text) {
  document.getElementById(id).textContent = text;
}

function showBestWindow(data) {
  const best = data.best_window;

  if (best === null) {
    const message = document.getElementById("no-window");
    message.textContent = data.no_window_message;
    message.hidden = false;
    return;
  }

  setText("best-title", `Best time today: ${best.start} to ${best.end}`);
  setText(
    "best-details",
    `${best.verdict}, average score ${best.average_score.toFixed(1)} / ` +
      `${data.max_score}: ${best.reason}`
  );
}

// Add one GIF with a caption, like "Sky: sunny", to the row of tiles
function addTile(folder, category) {
  if (category === null) {
    return; // null means the data is missing, so there's no GIF to show
  }

  const figure = document.createElement("figure");
  const image = document.createElement("img");
  const caption = document.createElement("figcaption");

  image.src = `assets/${folder}/${category}.gif`;
  image.alt = `${folder} ${category}`;
  // Capitalise the folder name: "sky" becomes "Sky"
  caption.textContent = `${folder[0].toUpperCase()}${folder.slice(1)}: ${category}`;

  figure.append(image, caption);
  document.getElementById("tiles").append(figure);
}

function showRightNow(data) {
  const current = data.current_hour;

  if (current === null) {
    setText("now-title", "No forecast found for this hour.");
    return;
  }

  setText("now-title", `Right now: ${current.verdict}`);
  if (current.verdict !== "Night") {
    // night hours have no score
    setText("now-score", `Score: ${current.score} / ${data.max_score}`);
  }

  addTile("sky", current.sky);
  addTile("wind", current.wind);
  addTile("waves", current.waves);
}

async function loadForecast() {
  try {
    const response = await fetch("forecast.json");
    if (!response.ok) {
      throw new Error(`status ${response.status}`);
    }
    const data = await response.json();

    // updated_at looks like "2026-11-09T15:06", and slice(11, 13) picks out "15"
    setText("updated", `Updated at ${data.updated_at.slice(11, 13)}:00`);
    showBestWindow(data);
    showRightNow(data);
  } catch (error) {
    console.error("Could not load the forecast:", error); // for the browser console
    setText("updated", "The forecast couldn't be loaded. Please try again later.");
  }
}

loadForecast();
