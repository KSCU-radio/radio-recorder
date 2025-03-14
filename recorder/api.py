"""
API interaction functions for Spinitron
"""

import time
import requests
import logging
from functools import wraps
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone, timedelta
from requests.exceptions import RequestException
from dateutil import parser

from config import API_KEY, api_logger


@wraps(requests.get)
def retry_api_call(max_retries=3, delay=5):
    """
    Decorator to retry API calls on failure

    Args:
        max_retries (int): Maximum number of retry attempts
        delay (int): Base delay between retries in seconds
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            while retries <= max_retries:
                try:
                    return func(*args, **kwargs)
                except RequestException as e:
                    retries += 1
                    if retries > max_retries:
                        api_logger.error(f"Maximum retries reached. Last error: {e}")
                        raise
                    wait_time = delay * retries  # Exponential backoff
                    api_logger.warning(
                        f"API call failed: {e}. Retrying in {wait_time}s (attempt {retries}/{max_retries})"
                    )
                    time.sleep(wait_time)

        return wrapper

    return decorator


@retry_api_call(max_retries=3, delay=5)
def safe_api_get(url: str, timeout: int = 10) -> Dict[str, Any]:
    """
    Make a GET request to API with proper error handling and validation

    Args:
        url (str): URL to request
        timeout (int): Request timeout in seconds

    Returns:
        dict: JSON response from API

    Raises:
        RequestException: If request fails after retries
        ValueError: If response is not valid JSON or status code is not 200
    """
    api_logger.debug(f"Making API request to {url}")
    response = requests.get(url, timeout=timeout)

    if response.status_code != 200:
        api_logger.error(
            f"API request failed with status {response.status_code}: {response.text}"
        )
        response.raise_for_status()

    try:
        data = response.json()
        return data
    except ValueError as e:
        api_logger.error(f"Invalid JSON response: {response.text[:100]}...")
        raise ValueError(f"API returned invalid JSON response: {e}")


def get_dj_info(link: str) -> Optional[Dict[str, Any]]:
    """
    Grabs the DJ's name and email from the Spinitron API

    Args:
        link (str): Link to the DJ's persona

    Returns:
        Optional[Dict[str, Any]]: Dictionary with DJ info or None if request failed
    """
    try:
        api_logger.debug(f"Requesting DJ info from {link}")
        persona = safe_api_get(link)

        # Ensure required fields exist
        if not all(key in persona for key in ["email", "id", "name"]):
            api_logger.error(f"Missing required fields in DJ info response")
            return None

        return {"email": persona["email"], "id": persona["id"], "name": persona["name"]}
    except Exception as e:
        api_logger.error(f"Error retrieving DJ info: {e}")
        return None


def request_spins(
    show_start: datetime, duration: int, api_key: str
) -> List[Dict[str, str]]:
    """
    Requests the spins from the Spinitron API and filters them by the show's start time

    Args:
        show_start (datetime): Start time of the show
        duration (int): Duration of the show in seconds
        api_key (str): Spinitron API key

    Returns:
        List[Dict[str, str]]: List of spins with song and artist
    """
    try:
        # Calculate number of spins to request based on show duration
        # Assuming roughly 10 songs per hour (1 song per 6 minutes on average)
        count = int(duration // 360) + 10  # Add some buffer
        count = min(count, 200)  # API limit

        spins_url = (
            f"https://spinitron.com/api/spins?access-token={api_key}&count={count}"
        )
        api_logger.debug(f"Requesting spins with count={count}")

        spins_data = safe_api_get(spins_url)["items"]
        api_logger.debug(f"Retrieved {len(spins_data)} spins")

        # Filter spins to only include those that occurred during the show
        filtered_spins = []
        show_end = show_start + timedelta(seconds=duration)

        for spin in spins_data:
            spin_time = parser.parse(spin["start"])

            # Only include spins during the show timeframe
            if show_start <= spin_time <= show_end:
                filtered_spins.append(
                    {
                        "song": spin.get("song", "Unknown Song"),
                        "artist": spin.get("artist", "Unknown Artist"),
                    }
                )

        # Reverse to get chronological order
        filtered_spins.reverse()
        api_logger.debug(f"Filtered to {len(filtered_spins)} spins for the show")
        return filtered_spins

    except Exception as e:
        api_logger.error(f"Error retrieving spins: {e}")
        return []


def get_todays_shows() -> List[Dict[str, Any]]:
    """
    Retrieves the next 24 shows from the Spinitron API and filters them

    Returns:
        List[Dict[str, Any]]: List of show information dictionaries
    """
    max_retries = 5
    retries = 0

    while retries < max_retries:
        try:
            api_logger.debug("Requesting show data from Spinitron API")
            url = f"https://spinitron.com/api/shows?access-token={API_KEY}&count=24"
            station_data = safe_api_get(url)

            # If we get here, the request was successful
            api_logger.debug("Successfully retrieved show data")
            break

        except Exception as e:
            api_logger.error(f"Error getting Spinitron data: {e}")
            retries += 1

            if retries == max_retries:
                api_logger.critical(
                    "Maximum retries reached. Could not retrieve data from Spinitron API."
                )
                from recorder.email_utils import send_error_email

                send_error_email("api_key_error")
                return []

            sleep_time = 15 * retries  # Exponential backoff
            api_logger.info(
                f"Retrying in {sleep_time} seconds (attempt {retries}/{max_retries})"
            )
            time.sleep(sleep_time)

    # Process the retrieved data
    todays_recording_sched = []

    # Characters not allowed in filenames
    illegal_chars = {
        "#",
        "%",
        "&",
        "{",
        "}",
        "\\",
        "$",
        "!",
        "'",
        '"',
        ":",
        "@",
        "<",
        ">",
        "*",
        "?",
        "/",
        "+",
        "`",
        "|",
        "=",
        " ",
        ".",
        "_",
        "-",
        ",",
        "(",
        ")",
    }

    now = datetime.now()
    next_day_5am = (now + timedelta(days=1)).replace(
        hour=5, minute=0, second=0, microsecond=0
    )

    for show_info in station_data["items"]:
        # Skip automation shows
        if show_info["category"] == "Automation":
            continue

        # Parse dates
        show_start = (
            parser.parse(show_info["start"])
            .replace(tzinfo=timezone.utc)
            .astimezone(tz=None)
        )
        show_end = (
            parser.parse(show_info["end"])
            .replace(tzinfo=timezone.utc)
            .astimezone(tz=None)
        )

        # Skip shows that have already ended
        if int(show_end.strftime("%s")) <= int(time.time()):
            continue

        # Check if the show is within our recording window
        # (today or tomorrow before 5am)
        is_today = show_start.date() == now.date()
        is_tomorrow_early = (
            show_start.date() == next_day_5am.date()
            and show_start.time() < next_day_5am.time()
            and show_end.time() <= next_day_5am.time()
        )

        if not (is_today or is_tomorrow_early):
            continue

        # Get DJs information
        djs = []
        if "_links" in show_info and "personas" in show_info["_links"]:
            for persona_link in show_info["_links"]["personas"]:
                dj_info = get_dj_info(persona_link["href"])
                if dj_info:
                    djs.append(dj_info)

        # Create filename
        show_name = show_info["title"]
        show_file_name = "".join(c for c in show_name if c not in illegal_chars)
        if show_file_name == "":
            show_file_name = show_info["id"]

        # Add show to schedule
        todays_recording_sched.append(
            {
                "showName": show_name,
                "showFileName": f"{show_file_name}_{show_start.date()}.mp3",
                "showStart": show_start,
                "showEnd": show_end,
                "duration": show_info["duration"],
                "djs": djs,
            }
        )

    from config import schedule_logger

    schedule_logger.info(
        f"Retrieved {len(todays_recording_sched)} shows to be recorded"
    )
    log_pretty_schedule(todays_recording_sched)
    return todays_recording_sched


def log_pretty_schedule(shows: List[Dict[str, Any]]) -> None:
    """
    Logs the day's schedule in a pretty table format

    Args:
        shows (List[Dict[str, Any]]): List of show information dictionaries
    """
    if not shows:
        from config import schedule_logger

        schedule_logger.info("No shows to display in schedule")
        return

    headers = ["Start Time", "End Time", "Title", "DJ", "Email"]
    rows = []

    for show in shows:
        for dj_info in show.get("djs", []):
            rows.append(
                [
                    show["showStart"].strftime("%Y-%m-%d %H:%M:%S"),
                    show["showEnd"].strftime("%Y-%m-%d %H:%M:%S"),
                    show["showName"],
                    dj_info.get("name", "Unknown DJ"),
                    dj_info.get("email", "No email"),
                ]
            )

    # If no rows were created (no DJs), add at least one row with show info
    if not rows and shows:
        for show in shows:
            rows.append(
                [
                    show["showStart"].strftime("%Y-%m-%d %H:%M:%S"),
                    show["showEnd"].strftime("%Y-%m-%d %H:%M:%S"),
                    show["showName"],
                    "No DJ info",
                    "No email",
                ]
            )

    # Calculate the maximum widths for each column
    max_widths = [len(header) for header in headers]
    for row in rows:
        for i, cell in enumerate(row):
            max_widths[i] = max(max_widths[i], len(str(cell)))

    # Add some padding
    max_widths = [width + 1 for width in max_widths]

    # Create the table header
    table = (
        "| "
        + " | ".join([f"{header:<{max_widths[i]}}" for i, header in enumerate(headers)])
        + " |"
    )
    table += "\n" + "-" * (sum(max_widths) + len(headers) * 3 - 1)

    # Create the table rows
    for row in rows:
        table += (
            "\n| "
            + " | ".join(
                [f"{str(cell):<{max_widths[i]}}" for i, cell in enumerate(row)]
            )
            + " |"
        )

    from config import schedule_logger

    schedule_logger.info("Today's Schedule:\n%s", table)
