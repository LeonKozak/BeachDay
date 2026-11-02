"""Draw the pixel-art GIFs used by the app. Run with: python make_gifs.py"""

from math import cos, pi, sin
from pathlib import Path

from PIL import Image, ImageDraw

# Settings shared by every tile, so they all have the same retro look
WIDTH = 64  # pixels on the small canvas
HEIGHT = 32
SCALE = 6  # each small pixel becomes a 6x6 block in the final GIF
FRAMES = 12  # pictures in one animation loop

ASSETS = Path(__file__).parent / "assets"


def save_gif(path, draw_frame, settings):
    """Draw every frame with draw_frame, scale it up, and save the GIF.

    Any kind of tile can use this. It only needs its own draw_frame function.
    """
    frames = []
    for frame_number in range(FRAMES):
        image = Image.new("RGB", (WIDTH, HEIGHT))
        draw_frame(ImageDraw.Draw(image), frame_number, settings)
        # Nearest-neighbour copies pixels without blending, so they stay sharp
        big_size = (WIDTH * SCALE, HEIGHT * SCALE)
        frames.append(image.resize(big_size, Image.Resampling.NEAREST))

    path.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        path,
        save_all=True,
        append_images=frames[1:],
        duration=settings["frame_ms"],
        loop=0,  # 0 means repeat forever
    )


# Waves

BAND_HEIGHT = 3  # rows of each water colour, from the surface downwards
FOAM_THICKNESS = 4  # how quickly foam gets deeper towards a crest
NO_FOAM = 2  # wave_shape never goes above 1, so this level is never reached

WAVE_TILES = {
    "calm": {
        "frame_ms": 160,
        "sky": (158, 224, 240),
        "foam": (235, 250, 245),
        "spray_level": NO_FOAM,
        "layers": [
            {
                "base": 17,
                "amplitude": 1,
                "wavelength": 20,
                "pointiness": 0,
                "foam_level": NO_FOAM,
                "colours": [(72, 190, 205), (56, 170, 195)],
            },
            {
                "base": 20,
                "amplitude": 1,
                "wavelength": 14,
                "pointiness": 0,
                "foam_level": NO_FOAM,
                "colours": [(48, 176, 190), (34, 146, 176), (26, 120, 160)],
            },
        ],
    },
    "moderate": {
        "frame_ms": 90,
        "sky": (130, 190, 225),
        "foam": (240, 245, 240),
        "spray_level": NO_FOAM,
        "layers": [
            {
                "base": 13,
                "amplitude": 2,
                "wavelength": 30,
                "pointiness": 0.2,
                "foam_level": NO_FOAM,
                "colours": [(52, 130, 180), (40, 110, 165)],
            },
            {
                "base": 17,
                "amplitude": 3,
                "wavelength": 22,
                "pointiness": 0.4,
                "foam_level": 0.5,
                "colours": [(36, 120, 175), (26, 92, 150), (20, 70, 125)],
            },
        ],
    },
    "rough": {
        "frame_ms": 60,
        "sky": (92, 104, 125),
        "foam": (225, 232, 235),
        "spray_level": 0.6,
        "layers": [
            {
                "base": 10,
                "amplitude": 4,
                "wavelength": 34,
                "pointiness": 0.5,
                "foam_level": 0.6,
                "colours": [(38, 66, 98), (28, 52, 82)],
            },
            {
                "base": 15,
                "amplitude": 8,
                "wavelength": 28,
                "pointiness": 0.6,
                "foam_level": -0.2,
                "colours": [(22, 54, 86), (14, 38, 66), (8, 24, 46)],
            },
        ],
    },
}


def wave_shape(x, time, wavelength, pointiness):
    """Return how high the wave is at x: 1 at a crest, -1 in a trough.

    time goes from 0 to 1 over one loop, which slides the wave along by exactly
    one wavelength. The last frame therefore flows smoothly into the first.
    """
    position = x / wavelength - time
    rounded = cos(2 * pi * position)
    pointed = 1 - 2 * abs(sin(pi * position))
    return (1 - pointiness) * rounded + pointiness * pointed


def draw_water_layer(draw, frame_number, layer, foam):
    """Draw one layer of water, one column of pixels at a time."""
    time = frame_number / FRAMES

    for x in range(WIDTH):
        shape = wave_shape(x, time, layer["wavelength"], layer["pointiness"])
        surface = round(layer["base"] - layer["amplitude"] * shape)

        # Foam only appears on the part of the wave above foam_level
        foam_depth = 0
        if shape > layer["foam_level"]:
            foam_depth = 1 + round((shape - layer["foam_level"]) * FOAM_THICKNESS)

        for y in range(surface, HEIGHT):
            depth = y - surface
            checker = (x + y) % 2 == 0  # a checkerboard, for retro dithering

            # Deeper water uses darker colours
            band = depth // BAND_HEIGHT
            # Mix the last row of a band with the next colour using the checkerboard
            if depth % BAND_HEIGHT == BAND_HEIGHT - 1 and checker:
                band += 1
            colour = layer["colours"][min(band, len(layer["colours"]) - 1)]

            # The top half of the foam is solid, and the bottom half is speckled
            if depth < foam_depth / 2:
                colour = foam
            elif depth < foam_depth and checker:
                colour = foam

            draw.point((x, y), fill=colour)


def draw_spray(draw, frame_number, layer, foam, spray_level):
    """Draw flecks of foam flying just above the highest parts of a wave."""
    time = frame_number / FRAMES

    for x in range(WIDTH):
        shape = wave_shape(x, time, layer["wavelength"], layer["pointiness"])
        # This pattern repeats every 3 frames, and 12 frames divide evenly by 3
        if shape > spray_level and (x + frame_number) % 3 == 0:
            surface = round(layer["base"] - layer["amplitude"] * shape)
            draw.point((x, surface - 2), fill=foam)


def draw_waves(draw, frame_number, settings):
    """Draw one frame of a wave tile: sky first, then water from back to front."""
    draw.rectangle((0, 0, WIDTH, HEIGHT), fill=settings["sky"])

    for layer in settings["layers"]:
        draw_water_layer(draw, frame_number, layer, settings["foam"])

    front_layer = settings["layers"][-1]
    draw_spray(draw, frame_number, front_layer, settings["foam"], settings["spray_level"])


# Sky

# Small pictures drawn as text. Each character stands for one pixel, and "." is
# see-through. draw_sprite turns the other characters into colours.
CLOUD = [
    "......###.......",
    "...######.###...",
    "..############..",
    ".##############.",
    "################",
    "++++++++++++++++",
]
MOON = [
    "..###.",
    ".###..",
    "###...",
    "###...",
    "###...",
    ".###..",
    "..###.",
]
STARS = [(5, 4), (14, 12), (22, 3), (31, 9), (38, 16), (56, 6), (9, 20), (27, 18), (59, 15)]

SUN_CENTRE = (48, 10)
SUN_RADIUS = 4
SUN_RAYS = 8
RAIN_SPACING = 12  # rows between raindrops in the same column

SKY_TILES = {
    "sunny": {
        "frame_ms": 150,
        "background": [(96, 180, 235), (130, 205, 240), (175, 228, 245)],
        "sun": True,
        "night": False,
        "rain": False,
        "clouds": [],
    },
    "cloudy": {
        "frame_ms": 180,
        "background": [(135, 160, 185), (160, 182, 200), (185, 200, 212)],
        "sun": False,
        "night": False,
        "rain": False,
        "clouds": [
            {"y": 4, "spacing": 16, "light": (205, 212, 220), "shadow": (175, 185, 198)},
            {"y": 13, "spacing": 24, "light": (240, 243, 245), "shadow": (200, 208, 216)},
        ],
    },
    "rainy": {
        "frame_ms": 80,
        "background": [(70, 82, 100), (88, 102, 120), (105, 120, 138)],
        "sun": False,
        "night": False,
        "rain": True,
        "clouds": [
            {"y": 0, "spacing": 16, "light": (95, 105, 120), "shadow": (72, 82, 98)},
            {"y": 5, "spacing": 24, "light": (120, 130, 145), "shadow": (88, 98, 114)},
        ],
    },
    "night": {
        "frame_ms": 200,
        "background": [(10, 14, 42), (18, 24, 62), (30, 38, 84)],
        "sun": False,
        "night": True,
        "rain": False,
        "clouds": [],
    },
}


def draw_background(draw, colours):
    """Fill the tile with horizontal colour bands, mixed where they meet."""
    band_height = HEIGHT // len(colours)

    for y in range(HEIGHT):
        band = y // band_height
        for x in range(WIDTH):
            # Mix the last row of a band with the next colour using a checkerboard
            if y % band_height == band_height - 1 and (x + y) % 2 == 0:
                colour = colours[min(band + 1, len(colours) - 1)]
            else:
                colour = colours[min(band, len(colours) - 1)]
            draw.point((x, y), fill=colour)


def draw_sprite(draw, sprite, left, top, colours):
    """Draw a text picture, with colours saying which character gets which colour."""
    for row, line in enumerate(sprite):
        for column, character in enumerate(line):
            if character in colours:
                draw.point((left + column, top + row), fill=colours[character])


def draw_sun(draw, frame_number):
    """Draw the sun, with rays that turn by one gap per loop."""
    centre_x, centre_y = SUN_CENTRE
    draw.ellipse(
        (centre_x - SUN_RADIUS, centre_y - SUN_RADIUS, centre_x + SUN_RADIUS, centre_y + SUN_RADIUS),
        fill=(255, 225, 90),
    )

    time = frame_number / FRAMES
    for ray in range(SUN_RAYS):
        # After one loop each ray sits where the next ray started, so it looks the same
        angle = 2 * pi * (ray + time) / SUN_RAYS
        for distance in (SUN_RADIUS + 2, SUN_RADIUS + 3):
            x = round(centre_x + distance * cos(angle))
            y = round(centre_y + distance * sin(angle))
            draw.point((x, y), fill=(255, 245, 170))


def draw_stars_and_moon(draw, frame_number):
    """Draw the moon and the stars, with a few stars brighter on each frame."""
    draw_sprite(draw, MOON, 46, 5, {"#": (240, 235, 200)})

    for index, position in enumerate(STARS):
        # This pattern repeats every 4 frames, and 12 frames divide evenly by 4
        if (frame_number + index) % 4 == 0:
            draw.point(position, fill=(255, 255, 230))
        else:
            draw.point(position, fill=(130, 140, 180))


def draw_rain(draw, frame_number):
    """Draw raindrops that fall by exactly RAIN_SPACING rows per loop."""
    for x in range(0, WIDTH, 3):
        # Each column starts at a different height, so the rain looks uneven
        fall = (frame_number * RAIN_SPACING // FRAMES + x * 5) % RAIN_SPACING
        for start in range(-RAIN_SPACING, HEIGHT, RAIN_SPACING):
            y = start + fall
            draw.line((x, y, x - 1, y + 1), fill=(170, 195, 225))


def draw_cloud_row(draw, frame_number, row):
    """Draw evenly spaced clouds that drift by exactly one space per loop."""
    time = frame_number / FRAMES
    colours = {"#": row["light"], "+": row["shadow"]}

    shift = round(time * row["spacing"])
    for left in range(-len(CLOUD[0]), WIDTH, row["spacing"]):
        draw_sprite(draw, CLOUD, left + shift, row["y"], colours)


def draw_sky(draw, frame_number, settings):
    """Draw one frame of a sky tile, from the back to the front."""
    draw_background(draw, settings["background"])

    if settings["sun"]:
        draw_sun(draw, frame_number)
    if settings["night"]:
        draw_stars_and_moon(draw, frame_number)
    if settings["rain"]:
        draw_rain(draw, frame_number)
    for row in settings["clouds"]:
        draw_cloud_row(draw, frame_number, row)


# Wind

GROUND_TOP = 26  # the sand starts on this row
POLE_X = 12
POLE_TOP = 5
FLAG_TOP = 7
FLAG_HEIGHT = 5
FLAG_WAVELENGTH = 10

WIND_TILES = {
    "light": {
        "frame_ms": 200,
        "sky": (168, 220, 240),
        "streak": (225, 243, 250),
        "laps": 1,  # how many times the streaks cross the tile per loop
        "streaks": [(4, 40, 4), (18, 8, 3)],  # each is (row, starting x, length)
        "flag_length": 12,
        "droop": 0.5,  # rows the flag falls for each pixel along it
        "flap": 1,  # how far the end of the flag moves up and down
    },
    "breezy": {
        "frame_ms": 100,
        "sky": (140, 195, 225),
        "streak": (225, 240, 248),
        "laps": 2,
        "streaks": [(3, 30, 6), (15, 2, 5), (19, 44, 7), (23, 20, 5)],
        "flag_length": 16,
        "droop": 0.15,
        "flap": 2,
    },
    "strong": {
        "frame_ms": 60,
        "sky": (110, 135, 160),
        "streak": (225, 232, 238),
        "laps": 3,
        "streaks": [
            (2, 10, 12),
            (4, 42, 10),
            (14, 0, 12),
            (16, 30, 14),
            (19, 52, 10),
            (21, 18, 12),
            (24, 38, 10),
        ],
        "flag_length": 20,
        "droop": 0,
        "flap": 3,
    },
}


def draw_ground(draw):
    """Draw the sand along the bottom of the tile."""
    for y in range(GROUND_TOP, HEIGHT):
        for x in range(WIDTH):
            if y == GROUND_TOP and (x + y) % 2 == 0:
                draw.point((x, y), fill=(210, 180, 120))
            else:
                draw.point((x, y), fill=(232, 208, 150))


def draw_streaks(draw, frame_number, settings):
    """Draw lines of wind that cross the tile a whole number of times per loop."""
    time = frame_number / FRAMES
    shift = round(time * settings["laps"] * WIDTH)

    for row, start, length in settings["streaks"]:
        for offset in range(length):
            # % WIDTH makes a line leaving the right edge come back on the left
            x = (start + shift + offset) % WIDTH
            draw.point((x, row), fill=settings["streak"])


def draw_flag(draw, frame_number, settings):
    """Draw a pole and a flag, using the same wave shape as the water."""
    time = frame_number / FRAMES
    draw.rectangle((POLE_X, POLE_TOP, POLE_X + 1, GROUND_TOP - 1), fill=(90, 70, 55))

    for along in range(settings["flag_length"]):
        shape = wave_shape(along, time, FLAG_WAVELENGTH, 0)
        # The flag is held still at the pole and moves most at its free end
        flap = settings["flap"] * shape * along / settings["flag_length"]
        top = FLAG_TOP + round(settings["droop"] * along + flap)

        x = POLE_X + 2 + along
        # Parts of the flag rising towards a crest catch the light
        colour = (215, 60, 50) if shape > 0 else (170, 40, 40)
        draw.line((x, top, x, top + FLAG_HEIGHT - 1), fill=colour)


def draw_wind(draw, frame_number, settings):
    """Draw one frame of a wind tile, from the back to the front."""
    draw.rectangle((0, 0, WIDTH, HEIGHT), fill=settings["sky"])
    draw_ground(draw)
    draw_streaks(draw, frame_number, settings)
    draw_flag(draw, frame_number, settings)


if __name__ == "__main__":
    # Each entry: the folder, the tiles to save there, and the function that draws them
    TILE_GROUPS = [
        ("waves", WAVE_TILES, draw_waves),
        ("sky", SKY_TILES, draw_sky),
        ("wind", WIND_TILES, draw_wind),
    ]

    for folder, tiles, draw_frame in TILE_GROUPS:
        for name, settings in tiles.items():
            save_gif(ASSETS / folder / f"{name}.gif", draw_frame, settings)
            print("Saved", folder, name)
