#################################################################################
#                                                                               #
#                   DECKIFY QR CODE CARDS CREATOR                               #
#                                                                               #
#             Developed by: Arnar Már Brynjarsson (c) 2023                      #
#              Contact: arnarrvk@gmail.com                                      #
#                                                                               #
#                                                                               #
#    Welcome to Deckify QR Code Cards Creator! This program helps you create    #
#    cards with title, artist, and year, along with a QR code to be printed     #
#    and played in the game inspired by "Hitster".                              #
#     Learn how to play Hitster:                                                #    
#         https://nordics.hitstergame.com/sv-en/how-to-play/                    #
#                                                                               #
#    Disclaimer: This game is inspired by "Hitster," but it is a separate       #
#    creation. All rights for the original game "Hitster" belong to their       #
#    respective owners.                                                         #
#                                                                               #
#    For educational purposes only!                                             #
#                                                                               #
#################################################################################

import json
import os
import re
from datetime import datetime
import time
from typing import List, Tuple, Optional
import textwrap
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt
from PIL import Image, ImageDraw, ImageFont
import qrcode
import requests
import numpy as np
import random
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from urllib.parse import urlparse, parse_qs
import reportlab
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from PIL import Image

# Constants
current_directory = os.path.dirname(os.path.abspath(__file__))

# Access to the MusicBrainz API URL
musicbrainz_base_url = 'http://musicbrainz.org/ws/2/'
recording_url = musicbrainz_base_url + 'recording'

# Card sizes for printing
card_size = (750, 750)
offset = 220
width = card_size[0] - 40

# Paths
title_font_path = os.path.join(current_directory, 'fonts', 'SF-Pro-Text-LightItalic.otf')
artist_font_path = os.path.join(current_directory, 'fonts', 'SF-Compact-Display-Medium.otf')
year_font_path = os.path.join(current_directory, 'fonts', 'SF-Compact-Display-Heavy.otf')
background_image_path = os.path.join(current_directory, 'img', 'frame.png')
music_note_path = os.path.join(current_directory, 'img', 'music-note.png')
folder_path = os.path.join(current_directory, 'cards')
output_pdf = "printable_cards.pdf"

# QR code background color. 
QR_background_color = "#FFFFFF"

# ================== MUST CHANGE HERE ==================

# # Spotify API credentials    #https://developer.spotify.com
client_id = "34730a5bede143d6b2b304214738f596"                
client_secret = "8a4269c056674765919ac06e55c893a7"

# # Discogs API credentials
token = 'FvYDrFVusgwUCtwlZpNXwsaRdXkJcVTUlhWGQIPG'
headers = {
    'Authorization': f'Discogs token={token}',
    'User-Agent': 'MyApp'
}

# ================== MUST CHANGE HERE ==================

def reverse_progress_bar(duration):
    """
    Generates a countdown progress bar for a given duration.

    Parameters:
        duration (int): The duration in seconds for the countdown.

    Returns:
        None
    """
    for i in range(duration, 0, -1):
        print(f"\033[1mTime remaining:\033[0m {i} seconds", end="\r")
        time.sleep(1)

    # This will clear the countdown at the end.
    print(' ' * (len("\033[1mTime remaining:\033[0m ") + len(str(duration)) + len(" seconds")), end='\r')

def save_card_image(card_image: Image.Image, base_name: str, index: int) -> None:
    """
    Save the card image with the specified file name.

    Args:
        card_image (PIL.Image.Image): The card image to be saved.
        base_name (str): The base name of the file.
        index (int): The index of the file.

    Returns:
        None
    """
    # Create the 'cards' directory if it doesn't exist
    os.makedirs('cards', exist_ok=True)

    # Save the card image with the specified file name
    file_name = f'{base_name}_{index}.png'
    file_path = os.path.join('cards', file_name)
    card_image.save(file_path)
    
def fetch_tracks(spotify, spotify_id, spotify_type):
    """
    Fetches tracks from the Spotify API based on the provided Spotify ID and type.
    
    Parameters:
        spotify (object): The Spotify API object.
        spotify_id (str): The ID of the Spotify object (album or playlist).
        spotify_type (str): The type of the Spotify object (album or playlist).
    
    Returns:
        list or None: A list of tracks if successful, None otherwise.
    """
    api_methods = {
        "album": spotify.album_tracks,
        "playlist": spotify.playlist_tracks
    }
    api_method = api_methods.get(spotify_type)
    if api_method:
        try:
            return api_method(spotify_id, limit=50)
        except Exception as e:
            print(f"Error fetching tracks: {e}")
    return None

def add_tracks_to_data(results, data, spotify_type, spotify, headers):
    """
    Add tracks to the data.
    
    Parameters:
        results (dict): The results containing the tracks to add.
        data (list): The data to add the tracks to.
        spotify_type (str): The type of Spotify object.
        spotify (Spotify): The Spotify object.
        headers (dict): The headers for the API request.
    
    Returns:
        None
    """
    for item in results["items"]:
        add_track_to_data(item, data, spotify_type, spotify, headers)

def fetch_and_add_additional_tracks(spotify, results, data, spotify_type, headers):
    """
    Fetches and adds additional tracks to the data using the Spotify API.
    
    Parameters:
        spotify: The Spotify API object.
        results: The initial result set obtained from the API.
        data: The data object where the tracks will be added.
        spotify_type: The type of the Spotify object.
        headers: The headers for the API request.
    
    Returns:
        None
    """
    while results['next']:
        try:
            results = spotify.next(results)
            add_tracks_to_data(results, data, spotify_type, spotify, headers)
        except spotipy.SpotifyException as e:
            print(f"Error fetching next set of tracks: {e}")
            break

def create_data(spotify_url, spotify, data, headers):
    """
    Creates the data dictionary by extracting track information from a Spotify URL.

    Parameters:
        spotify_url (str): The Spotify URL of the album or playlist.
        spotify (spotipy.Spotify): The Spotify API client.
        data (dict): The data dictionary to be populated.
        headers (dict): Headers for the Discogs API request.
    """
    # Extract the Spotify ID and type from the URL
    spotify_id, spotify_type = extract_spotify_id_and_type(spotify_url)
    if spotify_id is None or spotify_type is None:
        print("Invalid Spotify URL. URL should be of type 'album' or 'playlist'.")
        return

    print(f"\n\033[1mExtracted Spotify ID:\033[0m {spotify_id}")
    print(f"\033[1mSpotify URL Type:\033[0m {spotify_type}\n")
    reverse_progress_bar(30)

    # Fetch the tracks
    results = fetch_tracks(spotify, spotify_id, spotify_type)
    if results is None:
        return

    # Add tracks to the data dictionary
    add_tracks_to_data(results, data, spotify_type, spotify, headers)

    # Fetch and add additional tracks if available
    fetch_and_add_additional_tracks(spotify, results, data, spotify_type, headers)

def extract_spotify_id_and_type(url):
    """Extracts the Spotify ID and type (album or playlist) from the given URL.

    Parameters:
        url (str): The Spotify URL of the album or playlist.

    Returns:
        tuple: A tuple containing the extracted Spotify ID and type ('album' or 'playlist').
               If the URL format is invalid, returns (None, None).
    """
    # Parse the URL to get the different parts
    parsed_url = urlparse(url)
    path_parts = parsed_url.path.split('/')

    # Iterate over the path parts to find the type (album or playlist) and the ID
    for i, part in enumerate(path_parts):
        if part in ['album', 'playlist']:
            # Get the part after 'album' or 'playlist'
            id_and_query = path_parts[i+1]

            # Split the part by '?' to remove any query parameters
            id_only = id_and_query.split('?')[0]

            # Return the ID and type as a tuple
            return id_only, part

    # Return None values if the URL format is invalid
    return None, None

def try_parsing_date(text: str) -> Optional[datetime]:
    """
    Attempts to parse the date from the given text using predefined date formats.

    Parameters:
        text: The text containing the date.

    Returns:
        The parsed datetime object if successful, None otherwise.
    """
    # List of predefined date formats

    date_formats = ['%Y-%m-%d', '%Y-%m', '%Y']
    # Iterate over the date formats and try to parse the text
    for fmt in date_formats:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            pass

    return None

def clean_song_title(title: str) -> str:
    """
    Clean a song title by removing any text inside parentheses, square brackets, curly braces, and anything after a hyphen.
    
    Parameters:
        title (str): The song title to clean.
    
    Returns:
        str: The cleaned song title, with leading and trailing spaces removed.
    """
    
    title = re.sub(r'\s*\(.*?\)\s*', '', title)  # Remove anything inside parentheses
    title = re.sub(r'\s*\[.*?\]\s*', '', title)  # Remove anything inside square brackets
    title = re.sub(r'\s*{.*?}\s*', '', title)    # Remove anything inside curly braces
    title = re.sub(r'\s*-.*', '', title)    # Remove anything after a hyphen
    return title.strip()  # Remove leading and trailing spaces

def get_release_year_musicbrainz(artist_name: str, song_title: str) -> str:
    """Gets the release year of a song by querying the MusicBrainz API.

    Parameters:
        artist_name (str): The name of the artist.
        song_title (str): The title of the song.

    Returns:
        str: The release year of the song if found, or 'N/A' if not found.
    """
    # Prepare the query parameters
    song_title = clean_song_title(song_title)  # Clean the song title
    query = f'artist:{artist_name} AND recording:{song_title}'
    params = {
        'query': query,
        'fmt': 'json'
    }

    # Send the API request
    try:
        response = requests.get(recording_url, params=params)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error querying MusicBrainz API: {e}")
        return "N/A"

    # Check if the request was successful
    if response.status_code == 200:
        # Extract the recordings from the response
        try:
            recordings = response.json()['recordings']
        except (KeyError, ValueError) as e:
            print(f"Error parsing MusicBrainz API response: {e}")
            return "N/A"

        # If no recordings found, return 'N/A'
        if not recordings:
            return "N/A"

        # Iterate over the releases and filter out unwanted entries
        releases = [
            (
                release['title'],
                release['date'] if try_parsing_date(release['date']) is not None else "N/A",
                release['artist-credit'][0]['artist']['name'] if 'artist-credit' in release and release['artist-credit'] else "N/A"
            )
            for release in recordings[0]['releases'] if 'date' in release
        ]
        releases = [release for release in releases if release[2] != 'Various Artists']
        releases = [release for release in releases if release[1] != "N/A"]

        # Sort the releases by date and get the most recent one
        releases.sort(key=lambda x: try_parsing_date(x[1]), reverse=False)
        if releases:
            return releases[0][1]
        else:
            return "N/A"
    else:
        return "N/A"

def extract_track_info(item, spotify_type):
    """
    Extracts track information from an item based on the Spotify type.
    
    Parameters:
        item (dict): The item from which to extract track information.
        spotify_type (str): The type of item ('playlist' or 'track').
    
    Returns:
        dict: A dictionary containing the extracted track information. The dictionary has the following keys:
        'id' (str): The ID of the track.
        'name' (str): The name of the track.
        'artists' (list): A list of artist names associated with the track.
        'album' (str or None): The name of the album the track belongs to. None if not available.
        'url' (str): The external URL of the track on Spotify.
        
    If any error occurs during the extraction process, None is returned.
    """
    try:
        if spotify_type == 'playlist':
            track_data = item['track']
        else:
            track_data = item
        track_id = track_data['id']
        name = track_data['name']
        url = track_data["external_urls"]["spotify"]
        artists = [artist['name'] for artist in track_data['artists']]
        album = track_data['album']['name'] if 'album' in track_data else None
        
        return {'id': track_id, 'name': name, 'artists': artists, 'album': album, 'url': url}
    
    except Exception as e:
        print(f"Error in extract_track_info: {e}")
        return None

def fetch_discogs_data(artist, title, headers):
    """
    Fetches data from the Discogs API based on the provided artist and title.
    
    Parameters:
        artist (str): The name of the artist.
        title (str): The title of the track.
        headers (dict): The headers to be included in the request.
    
    Returns:
        dict or None: The JSON response from the Discogs API if successful, None otherwise.
    """
    try:
        url = f'https://api.discogs.com/database/search?artist={artist}&track={title}&type=master'
        response = requests.get(url, headers=headers)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error querying Discogs API: {e}")
        return None

    return response.json()

def extract_year_from_discogs_data(discogs_data, artist, title, spotify, item):
    """
    Extract the release year from the given discogs data. If no year is found, it falls back to the MusicBrainz API, 
    and if that fails, it attempts to get the release year from the Spotify API.
    
    Parameters:
        discogs_data (dict): The discogs data containing potential release year.
        artist (str): The artist of the song.
        title (str): The title of the song.
        spotify (spotipy.client.Spotify): A Spotify client object to interact with the Spotify API.
        item (dict): The Spotify data for a specific song.
    
    Returns:
        str: The release year if found, "N/A" otherwise.
    """
    
    # Check if there are any results with a year
    if 'results' in discogs_data:
        results_with_year = [result for result in discogs_data['results'] if 'year' in result]
        results_with_year.sort(key=lambda x: x['year'])

        # If there are results with a year, use the earliest one
        if results_with_year:
            return results_with_year[0]['year']
        else:
            # If there are no results with a year, query the MusicBrainz API for the release year
            date = get_release_year_musicbrainz(artist, title)

            # If a release year is found, extract the year
            if date != "N/A":
                return date.split('-')[0]
            else:
                # If no release year is found, set year to "N/A"
                return prompt_for_year(artist, title)
    else:
        # If there are no results from the Discogs API, query the MusicBrainz API for the release year
        date = get_release_year_musicbrainz(artist, title)

        # If a release year is found, extract the year
        if date != "N/A":
            return date.split('-')[0]
        else:
            # If no release year is found, try to get it from the Spotify API
            album_id = item["album"]["id"]
            album = spotify.album(album_id)
            return album["release_date"].split('-')[0] if "release_date" in album else "N/A"

    return prompt_for_year(artist, title)

def prompt_for_year(artist: str, title: str) -> str:
    """
    Prompts the user to manually input a year if not found automatically.

    Parameters:
        artist (str): Name of the artist.
        title (str): Title of the track.

    Returns:
        str: The year entered by the user.
    """
    print(f"No year found for '{title}' by {artist}.")
    while True:
        year = input("Please enter the release year (or press Enter to skip): ")
        if not year or year.isdigit():
            return year if year else "N/A"

def generate_qr_code(url):
    """
    Generate a QR code for the given URL.
    
    Parameters:
        url (str): The URL to generate a QR code for.
    
    Returns:
        qrcode.image.pil.PilImage: The generated QR code image with white fill and custom background color.
    """
    
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)
    qr_code = qr.make_image(fill="white", back_color=QR_background_color)

    return qr_code

def add_overlay_to_qr_code(qr_code_image):
    """
    Adds an overlay image to a QR code image.
    
    Parameters:
        qr_code_image (PIL.Image.Image): The QR code image to add the overlay to.
    
    Returns:
        PIL.Image.Image: The QR code image with the overlay added.
    """
    music_note_image = Image.open(music_note_path)

    # Calculate the dimensions to place the image at the center of the QR code
    qr_code_width, qr_code_height = qr_code_image.size
    overlay_size = min(qr_code_width, qr_code_height) // 3
    overlay_x = (qr_code_width - overlay_size) // 2
    overlay_y = (qr_code_height - overlay_size) // 2

    # Resize the overlay image
    resized_music_note = music_note_image.resize((overlay_size, overlay_size))

    # Place the overlay image onto the QR code
    qr_code_image.paste(resized_music_note, (overlay_x, overlay_y), resized_music_note)

    return qr_code_image

def add_track_to_data(item, data, spotify_type, spotify, headers):
    """
    Adds track information to the data dictionary.

    Parameters:
        item (dict): The track data from the Spotify API.
        data (dict): The data dictionary to be populated.
        spotify_type (str): The type of the Spotify URL ('album' or 'playlist').
        headers (dict): Headers for the Discogs API request.
    """
    track_info = extract_track_info(item, spotify_type)
    if track_info is None:
        return
    
    # Safely extract all artist names
    if isinstance(track_info['artists'], list):
        artist = ", ".join(track_info['artists'])
    else:
        artist = None
    title = track_info['name']
    discogs_data = fetch_discogs_data(artist, title, headers)
    if discogs_data is None:
        return
    
    year = extract_year_from_discogs_data(discogs_data, artist, title, spotify, item)
    url = track_info["url"]
    
    qr_img = generate_qr_code(url)
    qr_img = add_overlay_to_qr_code(qr_img)
    
    data["Artist"].append(artist)
    data["Title"].append(title)
    data["Year"].append(year)
    data["URL"].append(url)
    data["QR Code"].append(qr_img)
    
def create_card_front(index: int, row: pd.Series, base_name: str) -> Image.Image:
    """
    Creates the front of a card with dynamic font sizing.

    Parameters:
        index: The index of the track in the data.
        row: The data row representing the track.
        base_name: The base name for the card image file.

    Returns:
        Image.Image: The created card image.
    """
    artist = row['Artist']
    title = row['Title']
    year = row['Year']

    # Create a smooth RGB gradient background
    gradient = Image.new('RGB', card_size, color="black")
    for y in range(card_size[1]):
        r = int(255 * (y / card_size[1]))
        g = int(100 + 155 * (1 - abs((y / card_size[1]) - 0.5) * 2))  # Smooth green gradient
        b = int(255 * (1 - y / card_size[1]))
        for x in range(card_size[0]):
            gradient.putpixel((x, y), (r, g, b))

    # Add cohesive circular glowing shapes (bubbles) with blending
    gradient_draw = ImageDraw.Draw(gradient)
    num_bubbles = 15  # Fewer bubbles for a more cohesive design
    bubble_color = (255, 200, 100)  # A unified bright orange glow for bubbles
    for i in range(num_bubbles):
        radius = random.randint(80, 150)
        x = random.randint(-radius // 2, card_size[0] - radius + radius // 2)  # Allow slight overflow
        y = random.randint(-radius // 2, card_size[1] - radius + radius // 2)
        bubble_color_with_alpha = tuple(min(255, c + random.randint(-30, 30)) for c in bubble_color)
        gradient_draw.ellipse(
            [x, y, x + radius, y + radius],
            fill=bubble_color_with_alpha,
            outline=None
        )

    # Add semi-transparent overlay for overall unification
    overlay = Image.new('RGBA', card_size, (0, 0, 0, 120))
    gradient.paste(overlay, (0, 0), overlay)

    # Draw text layout on top of the background
    draw = ImageDraw.Draw(gradient)

    # Load fonts dynamically
    year_font = load_font_dynamic(year_font_path, 150, year, card_size[0] - 40)
    artist_font = load_font_dynamic(artist_font_path, 100, artist, card_size[0] - 40)
    title_font = load_font_dynamic(title_font_path, 70, title, card_size[0] - 40)

    # Position the year in the center
    year_width, year_height = year_font.getbbox(year)[2:4]
    year_x = (card_size[0] - year_width) // 2
    year_y = (card_size[1] // 2) - (year_height // 2) - 50
    draw.text((year_x, year_y), year, font=year_font, fill="white")

    # Position the artist name below the year
    artist_width, artist_height = artist_font.getbbox(artist)[2:4]
    artist_x = (card_size[0] - artist_width) // 2
    artist_y = year_y + year_height + 30
    draw.text((artist_x, artist_y), artist, font=artist_font, fill="white")

    # Position the title at the bottom
    wrapped_title = textwrap.wrap(title, width=30)
    title_y = artist_y + artist_height + 40
    for line in wrapped_title:
        line_width, line_height = title_font.getbbox(line)[2:4]
        line_x = (card_size[0] - line_width) // 2
        draw.text((line_x, title_y), line, font=title_font, fill="white")
        title_y += line_height + 5  # Small spacing between lines

    return gradient

def load_font_dynamic(font_path: str, max_size: int, text: str, max_width: int) -> ImageFont.FreeTypeFont:
    """
    Dynamically adjusts font size to fit the text within the given maximum width.

    Parameters:
        font_path (str): Path to the font file.
        max_size (int): Maximum font size.
        text (str): The text to fit.
        max_width (int): Maximum allowed width for the text.

    Returns:
        ImageFont.FreeTypeFont: The loaded font with adjusted size.
    """
    if not os.path.exists(font_path):
        raise FileNotFoundError(f"Font file not found at: {font_path}")
    if not text:
        raise ValueError("Text cannot be empty or None.")

    size = max_size
    while size > 10:
        try:
            font = ImageFont.truetype(font_path, size)
            text_left, text_top, text_right, text_bottom = font.getbbox(text)
            text_width = text_right - text_left
            if text_width <= max_width:
                return font
        except Exception as e:
            raise RuntimeError(f"Error creating font with size {size}: {e}")
        size -= 2
    return ImageFont.truetype(font_path, 10)  # Minimum font size


def create_card_back(index: int, row: pd.Series, base_name: str) -> None:
    """
    Creates an image card for a track.

    Parameters:
        index: The index of the track in the data.
        row: The data row representing the track.
        base_name: The base name for the card image file.
    """
    # Extract necessary data from the row
    qr_images = row['QR Code']

    # Create a blank card image
    card = Image.new('RGB', card_size, 'white')
    d = ImageDraw.Draw(card)

    # Load the background image and resize it to fit the card size
    img = Image.open(background_image_path).resize(card_size)
    card.paste(img)

    # Resize and paste the QR code images on the card
    qr = qr_images.resize((400, 400))

    card.paste(qr, ((card_size[0] // 2) - 200, (card_size[1] // 2) - 200))

    return card

def create_printable_pdf_from_folder(folder: str, output_file: str, cards_per_row=3, cards_per_column=3):
    """
    Creates a printable PDF for double-sided printing with multiple cards per page,
    leaving white space and adding cutting marks at the outer edges of the PDF.
    Back images are flipped horizontally to ensure alignment for double-sided printing.

    Parameters:
        folder (str): Path to the folder containing images with `_front_<index>.png` and `_back_<index>.png` filenames.
        output_file (str): Path to save the output PDF file.
        cards_per_row (int): Number of cards per row.
        cards_per_column (int): Number of cards per column.

    Returns:
        None
    """

    # Convert 7.5 cm to points
    card_width = card_height = 212.6  # 7.5 cm in points
    page_width, page_height = letter

    # Calculate spacing and margins
    horizontal_spacing = (page_width - (cards_per_row * card_width)) / (cards_per_row + 1)
    vertical_spacing = (page_height - (cards_per_column * card_height)) / (cards_per_column + 1)

    # Regex patterns to match front and back files
    front_pattern = re.compile(r"_front_(\d+)\.png$")
    back_pattern = re.compile(r"_back_(\d+)\.png$")

    # Gather front and back images with matching indexes
    fronts = {}
    backs = {}

    for filename in os.listdir(folder):
        front_match = front_pattern.search(filename)
        back_match = back_pattern.search(filename)
        if front_match:
            index = int(front_match.group(1))
            fronts[index] = os.path.join(folder, filename)
        elif back_match:
            index = int(back_match.group(1))
            backs[index] = os.path.join(folder, filename)

    # Ensure all front and back indexes match
    if set(fronts.keys()) != set(backs.keys()):
        unmatched = set(fronts.keys()).symmetric_difference(set(backs.keys()))
        raise ValueError(f"Unmatched indexes found: {unmatched}")

    # Sort by index to process pairs in order
    sorted_indexes = sorted(fronts.keys())

    # Initialize PDF canvas
    pdf = canvas.Canvas(output_file, pagesize=letter)

    def draw_outer_cutting_marks():
        """
        Draw cutting alignment marks at the outer edges of the PDF.
        """
        mark_length = 10  # Length of the cutting marks
        pdf.setStrokeColorRGB(0, 0, 0)  # Black color for cutting marks

        # Vertical marks (left and right edges)
        for row in range(cards_per_column + 1):
            y = page_height - vertical_spacing - row * (card_height + vertical_spacing)
            pdf.line(horizontal_spacing, y, horizontal_spacing - mark_length, y)  # Left mark
            pdf.line(page_width - horizontal_spacing, y, page_width - horizontal_spacing + mark_length, y)  # Right mark

        # Horizontal marks (top and bottom edges)
        for col in range(cards_per_row + 1):
            x = horizontal_spacing + col * (card_width + horizontal_spacing)
            pdf.line(x, page_height - vertical_spacing + mark_length, x, page_height - vertical_spacing)  # Top mark
            pdf.line(x, vertical_spacing - mark_length, x, vertical_spacing)  # Bottom mark

    def draw_cards(images, reverse_rows=False):
        """
        Draw a grid of cards on a single page.
        If reverse_rows is True, the rows are reversed for proper alignment on the back side.
        """
        card_index = 0
        for row in range(cards_per_column):
            for col in range(cards_per_row):
                if card_index >= len(images):
                    return  # No more images to draw
                # Reverse the column layout for rows on the back side
                if reverse_rows:
                    col = cards_per_row - col - 1
                image_path = images[card_index]
                x = horizontal_spacing + col * (card_width + horizontal_spacing)
                y = page_height - vertical_spacing - (row + 1) * (card_height + vertical_spacing)
                try:
                    img = Image.open(image_path).convert("RGB")
                    img = img.resize((int(card_width), int(card_height)), Image.Resampling.LANCZOS)
                    pdf.drawImage(image_path, x, y, width=card_width, height=card_height)
                except Exception as e:
                    print(f"Error processing image {image_path}: {e}")
                card_index += 1

    # Draw fronts on odd pages and backs on even pages
    for page in range(0, len(sorted_indexes), cards_per_row * cards_per_column):
        # Draw front side
        draw_cards([fronts[idx] for idx in sorted_indexes[page: page + cards_per_row * cards_per_column]])
        draw_outer_cutting_marks()  # Add cutting marks at the outer edges
        pdf.showPage()  # Add a new page

        # Draw back side (adjusted layout)
        draw_cards([backs[idx] for idx in sorted_indexes[page: page + cards_per_row * cards_per_column]], reverse_rows=True)
        draw_outer_cutting_marks()  # Add cutting marks at the outer edges
        pdf.showPage()  # Add a new page

    # Save PDF
    try:
        pdf.save()
        print(f"Printable PDF saved to {output_file}")
    except Exception as e:
        print(f"Error saving PDF: {e}")


def main():
    
    try:
        print("""
        ===================================================================
        =                        Deckify                                 =
        =                by Arnar M. Brynjarsson                         =
        =             the digital song QR card maker                     =
        ===================================================================
        """)

        start_time = time.time()

        spotify = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials(client_id, client_secret))

        data = {
            "Artist": [],
            "Title": [],
            "Year": [],
            "URL": [],
            "QR Code": []
        }

        spotify_url = input("\nPlease enter the Spotify URL of your album or playlist and hit Enter \n\nURL:  ")

        create_data(spotify_url, spotify, data, headers)

        df = pd.DataFrame(data)

        base_name = input("\n\033[1mPlease enter the base name for the cards:\033[0m ")

        for index, row in df.iterrows():
            card_front = create_card_front(index, row, base_name)
            card_back = create_card_back(index, row, base_name)
            save_card_image(card_front, base_name + '_front', index)
            save_card_image(card_back, base_name + '_back', index)

        create_printable_pdf_from_folder(folder_path, output_pdf, cards_per_row=2, cards_per_column=3)

        elapsed_time = time.time() - start_time
        rounded_time = round(elapsed_time)

        print(f"\n\033[1mYour music deck, \033[3m{base_name}\033[1m, is ready!\033[0m")
        print(f"\033[1mThe program ran for: {rounded_time:.2f} seconds\033[0m\n")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()