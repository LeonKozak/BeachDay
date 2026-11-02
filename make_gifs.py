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


if __name__ == "__main__":
    for name, settings in WAVE_TILES.items():
        save_gif(ASSETS / "waves" / f"{name}.gif", draw_waves, settings)
        print("Saved", name)
