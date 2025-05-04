import os
import requests
import discord
import imageio
import random
import numpy as np
from PIL import Image, ImageDraw
from io import BytesIO

FRAMES_COUNT = 200
FRAME_TIME = 0.03
WIN_EXTEND_TIME = 3


def download_image(url):
    """
    Download and convert an image from URL to PIL Image object.
    
    Args:
        url (str): URL of the image to download
        
    Returns:
        PIL.Image: Downloaded image in RGBA format
    """
    response = requests.get(url)
    return Image.open(BytesIO(response.content)).convert("RGBA")


def create_frame(images, shift, size=(500, 200), highlight=False):
    """
    Create a single frame for the wheel animation.
    
    Args:
        images (list): List of PIL Image objects to use in the frame
        shift (float): Current shift value for animation
        size (tuple): Frame dimensions (width, height)
        highlight (bool): Whether to highlight the winning movie
        
    Returns:
        tuple: (PIL.Image, int) - Generated frame and winner index if highlighted
    """
    bg_color = (50, 50, 50, 255) if not highlight else (200, 180, 0, 255)
    frame = Image.new("RGBA", size, bg_color)
    draw = ImageDraw.Draw(frame)

    center_x = size[0] // 2
    base_slot_width = size[0] // 5  # Fixed width for each item

    item_height = size[1] - 40
    gap = 4

    offset = -base_slot_width * 2
    prev_right = None  # The right limit of the previous item

    new_x = None

    winner_index = None  # The winning movie index

    winner_distance = float("inf")  # Winner's distance to the center


    for i, img in enumerate(images):
        slot_x = center_x + offset - shift
        slot_y = (size[1] - item_height) // 2
        slot_center = slot_x + base_slot_width / 2

        # Definition of winner (on the last frame)

        distance_to_center = abs(slot_center - center_x)
        if highlight and distance_to_center < winner_distance:
            winner_index = i
            winner_distance = distance_to_center

        # Increasing the central poster during animation

        is_winner = abs(slot_center - center_x) < base_slot_width / 2
        if is_winner:
            new_width = int(base_slot_width * 1.2)
            new_height = int(item_height * 1.2)
            candidate_x = slot_center - new_width / 2
            if prev_right is not None and candidate_x < prev_right + gap:
                new_x = prev_right + gap
            else:
                new_x = candidate_x
            new_y = slot_y - (new_height - item_height) / 2
            if highlight and i == winner_index:
                border_size = 5
                draw.rectangle(
                    [
                        new_x - border_size,
                        new_y - border_size,
                        new_x + new_width + border_size,
                        new_y + new_height + border_size,
                    ],
                    outline="gold",
                    width=5,
                )
            img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        else:
            new_x = slot_x
            new_y = slot_y
            img_resized = img.resize((base_slot_width, item_height))

        frame.paste(img_resized, (int(new_x), int(new_y)), img_resized)
        prev_right = new_x + img_resized.width
        offset += img_resized.width + gap

    return frame, winner_index


def generate_case_opening_gif(
    images,
    output_path="case_opening.gif",
    size=(500, 200),
    frames_count=FRAMES_COUNT,
    win_delay=25,
):
    """
    Generate an animated GIF of the movie wheel selection process.
    
    Args:
        images (list): List of PIL Image objects to use in animation
        output_path (str): Path where to save the generated GIF
        size (tuple): Dimensions of the GIF (width, height)
        frames_count (int): Number of frames in the animation
        win_delay (int): Number of frames to show winner highlight
        
    Returns:
        int: Index of the winning movie, or None if generation failed
    """
    if len(images) < 2:
        print("❌ Need at least 2 movies to create animation.")
        return None

    # If movies are less than 4, repeat the list

    if len(images) < 4:
        images = images * (4 // len(images) + 1)

    images = [img.resize((size[0] // 5, size[1] - 40)) for img in images]
    extended_images = images * 10  # Animation cycles

    speeds = np.linspace(30, 1, frames_count)
    frames = []
    shift = 0
    winner_index = None

    for i, speed in enumerate(speeds):
        highlight = i >= frames_count - win_delay
        frame, winner_index = create_frame(
            extended_images, shift, size, highlight=highlight
        )
        frames.append(frame)
        shift += speed

    last_frame = frames[-1]
    delay_frames = int(WIN_EXTEND_TIME / FRAME_TIME)
    frames.extend([last_frame] * delay_frames)

    if len(frames) > 300:
        print("❌ GIF too large, reduce frame count.")
        return None

    duration = FRAME_TIME * 1000

    imageio.mimsave(output_path, frames, duration=duration, loop=0)
    print(f"GIF '{output_path}' created!")
    return winner_index  # We return the winning movie index



async def send_gif(ctx, gif_path):
    """
    Send the generated GIF to Discord channel.
    
    Args:
        ctx: Discord context
        gif_path (str): Path to the GIF file
        
    Returns:
        Message: Sent Discord message object, or None if failed
    """
    try:
        with open(gif_path, "rb") as f:
            message = await ctx.send(file=discord.File(f))
            return message

    except discord.errors.HTTPException as e:
        if e.code == 40005:
            await ctx.send("❌ GIF is too large! Try reducing the size.")
        else:
            await ctx.send("❌ An error occurred while uploading the file.")
    os.remove(gif_path)


async def delete_gif(gif_path):
    """
    Delete the generated GIF file.
    
    Args:
        gif_path (str): Path to the GIF file to delete
    """
    try:
        os.remove(gif_path)
        print("File successfully deleted")
    except FileNotFoundError:
        print("File not found")
    except PermissionError:
        print("No permission to delete file")


async def create_gif_and_get_winner_movie(ctx, movies, gif_path):
    """
    Create wheel animation GIF and determine the winning movie.
    
    Args:
        ctx: Discord context
        movies (list): List of movies to include in the wheel
        gif_path (str): Path where to save the generated GIF
        
    Returns:
        Movie: The winning movie object, or None if creation failed
    """
    if len(movies) < 2:
        await ctx.send("❌ Need at least 2 movies to create the animation.")
        return None

    random.shuffle(movies)

    images = [download_image(movie.image_url) for movie in movies]

    winner_index = generate_case_opening_gif(images, output_path=gif_path)

    if winner_index is None:
        await ctx.send("❌ Failed to create GIF.")
        return None

    # Get the winning movie by index

    winner_movie = movies[winner_index % len(movies)]  # Use modulo to avoid errors


    return winner_movie


async def anitmation_runtime(
    frames=FRAMES_COUNT, frame_timne=FRAME_TIME, extend_time_for_winner=WIN_EXTEND_TIME
):
    """
    Calculate total runtime of the animation.
    
    Args:
        frames (int): Total number of frames
        frame_timne (float): Duration of each frame
        extend_time_for_winner (float): Additional time to show winner
        
    Returns:
        float: Total animation runtime in seconds
    """
    return frames * frame_timne + extend_time_for_winner
