"""
Contains the main functions for the recording bot.
This bot is responsible for recording shows and sending emails to DJs with their shows.
"""
from email.message import EmailMessage
from datetime import (
    datetime,
    timezone,
    timedelta,
)  # https://docs.python.org/3/library/datetime.html
import sched
import time  # https://pythontic.com/concurrency/scheduler/introduction
import os
import subprocess
import smtplib
import re
import logging
from logging.handlers import RotatingFileHandler
from dateutil import parser
import requests

# Error handling functions
from error_handling import (
    send_api_key_error_email,
    send_ffmpeg_error_email,
    send_aws_error_email,
)

from config import EMAIL, PASSWORD

# Must use old syntax to support Python 3.8
# root_logger = logging.getLogger()
# root_logger.setLevel(logging.INFO)
# handler = logging.FileHandler("info.log", "w", "utf-8")
# root_logger.addHandler(handler)

# Configure the logger
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

# Set up the rotating file handler
LOG_FILE = "info.log"
MAX_SIZE = 10 * 1024 * 1024  # 10 MB
BACKUP_COUNT = 2  # Number of backup files to keep

handler = RotatingFileHandler(
    LOG_FILE, maxBytes=MAX_SIZE, backupCount=BACKUP_COUNT, encoding="utf-8"
)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)

# Add the handler to the logger
root_logger.addHandler(handler)

logging.info("Hello, world!")

API_KEY = os.getenv("API_KEY")
FFMPEG = "/usr/bin/ffmpeg"
recorder_schedule = sched.scheduler(time.time, time.sleep)


def get_dj_info(link):
    """
    Grabs the DJ's name and email from the Spinitron API
    """
    persona_req = requests.get(url=link, timeout=5)
    # Check for a successful request
    if persona_req.status_code == 200:
        persona = persona_req.json()
    else:
        return False

    dj_info = {}
    dj_info["email"] = persona["email"]
    dj_info["id"] = persona["id"]
    dj_info["name"] = persona["name"]
    return dj_info


def log_pretty_schedule(todays_recording_sched):
    """
    Logs the day's schedule in a pretty table format
    """
    headers = ["Start Time", "End Time", "Title", "DJ", "Email"]
    rows = []
    for show in todays_recording_sched:
        for dj_info in show["djs"]:
            rows.append(
                [
                    show["showStart"].strftime("%Y-%m-%d %H:%M:%S"),
                    show["showEnd"].strftime("%Y-%m-%d %H:%M:%S"),
                    show["showName"],
                    dj_info["name"],
                    dj_info["email"],
                ]
            )

    # Calculate the maximum widths for each column
    max_widths = [len(header) for header in headers]
    for row in rows:
        for i, cell in enumerate(row):
            max_widths[i] = max(max_widths[i], len(cell))

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
            + " | ".join([f"{cell:<{max_widths[i]}}" for i, cell in enumerate(row)])
            + " |"
        )

    logging.info("Today's Schedule:\n%s", table)


# Add this function to your code
def request_spins(show_start, duration, api_key) -> list:
    """
    This function requests the spins from the Spinitron API
    and filters them by the show's start time.
    """
    count = int(duration // 3600) * 30
    count = min(count, 200)

    spins_url = (
        f"\nhttps://spinitron.com/api/spins?access-token={api_key}&count={count}"
    )
    spins_req = requests.get(url=spins_url, timeout=5)

    if spins_req.status_code != 200:
        return []

    spins_data = spins_req.json()["items"]
    filtered_spins = []

    for spin in spins_data:
        spin_start = parser.parse(spin["start"])
        if spin_start < show_start:
            break

        filtered_spins.append({"song": spin["song"], "artist": spin["artist"]})
    reversed_list = list(reversed(filtered_spins))
    return reversed_list


def get_todays_shows():
    """
    Grabs the next 24 shows from the Spinitron API
    """
    max_retries = 400
    retries = 0
    while retries < max_retries:
        station_data = requests.get(
            url=f"https://spinitron.com/api/shows?access-token={API_KEY}&count=24",
            timeout=5,
        )
        # Check for a successful request and break the loop if successful
        if station_data.status_code == 200:
            break
        logging.error("Error getting Spinitron data, trying again in 5 seconds")
        time.sleep(15)
        retries += 1
    if retries == max_retries:
        send_api_key_error_email()
        return []

    station_data = station_data.json()

    todays_recording_sched = []
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

    for show_info in station_data["items"]:
        djs = []
        for i in range(len(show_info["_links"]["personas"])):
            dj_info = get_dj_info(show_info["_links"]["personas"][i]["href"])
            if dj_info:
                djs.append(dj_info)
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

        show_name = show_info["title"]
        show_file_name = "".join(c for c in show_name if c not in illegal_chars)
        if show_file_name == "":
            show_file_name = show_info["id"]

        # Only add show if it starts the same day or the next day until 5am
        if show_info["category"] != "Automation" and int(show_end.strftime("%s")) > int(
            time.time()
        ):
            # Check if the show starts on the same day or the next day until 5am
            now = datetime.now()
            next_day_5am = (now + timedelta(days=1)).replace(
                hour=5, minute=0, second=0, microsecond=0
            )

            if show_start.date() == now.date() or (
                show_start.date() == next_day_5am.date()
                and show_start.time() < next_day_5am.time()
                and show_end.time() <= next_day_5am.time()
            ):
                # Need to add API hit to get email address
                todays_recording_sched.append(
                    {
                        "showName": show_name,
                        "showFileName": show_file_name
                        + "_"
                        + str(show_start.date())
                        + ".mp3",
                        "showStart": show_start,
                        "showEnd": show_end,
                        "duration": show_info["duration"],
                        "djs": djs,
                    }
                )
    logging.info("Grabbing next 24 shows complete")
    log_pretty_schedule(todays_recording_sched)
    return todays_recording_sched


def send_to_dj(show_info, email, dj_name, spins_data):
    """
    Sends an email to the DJ with a link to download their show
    """
    show_start = show_info["showStart"].strftime("%m/%d/%Y")
    subject = f"Recording Link - {show_info['showName']} - {show_start}"
    # ie https://kscu.s3.us-west-1.amazonaws.com/2022-10-17_TheSaladBowl.mp3
    text = f"""
Hey {dj_name}! 

This is an automated email from KSCU. 

You can use the link below to download your show and save it to your computer.
We only keep your recording for 90 days so you will need to download it to your computer to keep it permanently.
"""
    text += (
        "\nDownload here: "
        + "https://kscu.s3.us-west-1.amazonaws.com/"
        + show_info["showFileName"]
        + "\n"
    )
    if spins_data and len(spins_data) > 1:
        text += "\nSpins during your show:\n"
        for spin in spins_data:
            text += f"{spin['song']} - {spin['artist']}\n"
    text += """
If there's any issues with this system, please let us know by emailing web@kscu.org.

Much love from your friends at KSCU,
KSCU Bot"""
    send_cc = False
    # check for valid email
    regex = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
    if (re.fullmatch(regex, email)) is None:
        email = "web@kscu.org"
        subject = f"Public Email Address Needs Updating - {show_info['showName']}"
        send_cc = True
        text = f"""
Greetings staff member from the future!

This is an automated email from the radio recording bot to let you know that the public email address for {dj_name} needs to be updated.

Please include the DJ's email address in the "Public Email" field on Spinitron.

The DJ's show has been recorded and can be downloaded here: https://kscu.s3.us-west-1.amazonaws.com/{show_info['showFileName']}.

You can foward this email to the DJ if you'd like, but please make sure to update the email address on Spinitron.

Much love,
KSCU Bot
"""
    # Form message
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = EMAIL
    message["To"] = email
    if send_cc:
        message["Cc"] = "gm@kscu.org"
    message.set_content(text)

    # Open connection to gmail server to send message
    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(EMAIL, PASSWORD)
    server.send_message(message)
    server.quit()


def send_to_s3(file_name):
    """
    Sends a file to S3 and deletes it from EC2.
    """
    logging.info("Sending file to S3")

    send_str = "aws s3 cp " + file_name + " s3://kscu"
    result = subprocess.run(
        send_str, shell=True, stderr=subprocess.PIPE, text=True, check=False
    )
    if result.returncode != 0:
        logging.error("Sending to S3 failed: %s", result.stderr)
        send_aws_error_email()
        return

    result = subprocess.run(
        f"rm {file_name}", shell=True, stderr=subprocess.PIPE, text=True, check=False
    )
    if result.returncode != 0:
        logging.error("Deleting local file failed: %s", result.stderr)

    logging.info("File sent to S3")


def record(_, show_info):
    """
    Records a show for the specified duration
    """
    logging.info("Recording %s", datetime.now().strftime("%H:%M:%S"))

    # Calculate duration
    duration = int(show_info["showEnd"].strftime("%s")) - int(time.time())

    # If duration is less than 300s (5min), don't record
    if duration < 300:
        logging.info("Show has less than 5min remaining, not recording")
        return

    logging.info(
        "Recording %s with duration %d - actual duration %d",
        show_info["showFileName"],
        show_info["duration"],
        duration,
    )

    command_str = (
        "ffmpeg -i http://kscu.streamguys1.com:80/live -t '"
        + str(duration)
        + "' -y '"
        + show_info["showFileName"]
        + "'"
    )

    result = subprocess.run(
        command_str, shell=True, stderr=subprocess.PIPE, text=True, check=False
    )
    if result.returncode != 0:
        logging.error("Recording Failed: %s", result.stderr)
        send_ffmpeg_error_email()
        return

    logging.info("Recording Complete")
    send_to_s3(show_info["showFileName"])
    spins_data = request_spins(show_info["showStart"], show_info["duration"], API_KEY)
    # Proccess show info to send emails to DJs
    for cur_dj in show_info["djs"]:
        send_to_dj(
            show_info,
            cur_dj["email"],
            cur_dj["name"],
            spins_data,
        )


def run_schedule(todays_recording_sched):
    """
    Runs the schedule for the day
    """
    logging.info("Running Schedule")
    # For each of the items in today's schedule
    # Add to recording schedule
    # Convert to epoch time for the enterabs function
    for show_info in todays_recording_sched:
        epoch_start = int(show_info["showStart"].strftime("%s"))
        recorder_schedule.enterabs(
            epoch_start, 0, record, argument=(show_info["duration"], show_info)
        )
    recorder_schedule.run()
    logging.info("Schedule Complete")


def main():
    """
    Main function
    """
    while True:
        if recorder_schedule.empty() and datetime.now().strftime("%H:%M")[-2:] == "00":
            print("Grabbing next 24 Shows")
            run_schedule(get_todays_shows())
        time.sleep(1)


if __name__ == "__main__":
    main()
