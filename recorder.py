"""Provides EmailMessage class for generating email messages"""
from email.message import EmailMessage
from datetime import (
    datetime,
    timezone,
)  # https://docs.python.org/3/library/datetime.html
import sched
import time  # https://pythontic.com/concurrency/scheduler/introduction
import os
import smtplib
import re
from dateutil import parser
import requests
from dotenv import load_dotenv

# Error handling functions
from error_handling import (
    send_api_key_error_email,
    send_ffmpeg_error_email,
    send_aws_error_email,
)

load_dotenv()

API_KEY = os.getenv("API_KEY")
EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")
FFMPEG = "/usr/bin/ffmpeg"
recorder_schedule = sched.scheduler(time.time, time.sleep)


def get_dj_info(link):
    """
    Grabs the DJ's name and email from the Spinitron API
    """
    persona_req = requests.get(url=link, timeout=5)
    # Check for a successful request
    if persona_req.status_code != 200:
        persona = persona_req.json()
    else:
        return False

    dj_info = {}
    dj_info["email"] = persona["email"]
    dj_info["id"] = persona["id"]
    dj_info["dj"] = persona["name"]
    return dj_info


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
        print("Error getting Spinitron data, trying again in 5 seconds")
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
    }

    for show_info in station_data["items"]:
        djs = []
        for i in range(len(show_info["_links"]["personas"])):
            dj_info = get_dj_info(show_info["_links"]["personas"][i]["href"])
            if dj_info:
                djs.append(dj_info)
        show_id = show_info["id"]
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
        duration = show_info["duration"]
        show_name = show_info["title"]
        show_file_name = "".join(c for c in show_name if c not in illegal_chars)
        if show_file_name == "":
            show_file_name = show_id

        # Only add show if it starts the same day and is not autoplay
        if show_info["category"] != "Automation" and int(show_end.strftime("%s")) > int(
            time.time()
        ):
            # Need to add API hit to get email address
            todays_recording_sched.append(
                {
                    "showName": show_name,
                    "showFileName": str(show_start.date())
                    + "_"
                    + show_file_name
                    + ".mp3",
                    "showStart": show_start,
                    "showEnd": show_end,
                    "duration": duration,
                    "djs": djs,
                }
            )
    print("Grabbing next 24 shows complete")
    return todays_recording_sched


def send_to_dj(file_name, email, show_name, dj_name):
    """
    Sends an email to the DJ with a link to download their show
    """
    print("Sending email to DJ")
    subject = f"Recording Link - {show_name}"
    download_str = "https://kscu.s3.us-west-1.amazonaws.com/" + file_name
    # ie https://kscu.s3.us-west-1.amazonaws.com/2022-10-17_TheSaladBowl.mp3
    cc_addr = False
    text = f"""
	Hey {dj_name}! 
	
	This is an automated email from KSCU. 

	You can use the link below to download your show and save it to your computer.
	We only keep your recording for 90 days so you will need to download it to your computer to keep it permanently.
	"""
    text += download_str + "\n\n"
    text += """If there's any issues with this system, please let us know by emailing web@kscu.org.
	
	Much love from your friends at KSCU,
	KSCU Bot
	"""
    # check for valid email
    regex = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
    if (re.fullmatch(regex, email)) is None:
        email = "gm@kscu.org"
        subject = f"Public Email Address Needs Updating - {show_name}"
        cc_addr = True
        text = f"""
		Greetings staff member from the future!

		This is an automated email from the radio recording bot to let you know that the public email address for {dj_name} needs to be updated.

		Please include the DJ's email address in the "Public Email" field on Spinitron.

		Much love,
		KSCU Bot
		"""
    # Form message
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = EMAIL
    message["To"] = email
    if cc_addr:
        message["Cc"] = "gm@kscu.org"
    message.set_content(text)

    # Open connection to gmail server to send message
    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(EMAIL, PASSWORD)

    # message = 'Subject: {}\n\n{}'.format(subject, text).encode()
    # s.sendmail(EMAIL, email, message)

    server.send_message(message)
    server.quit()
    print("Email sent to DJ")


def send_to_s3(file_name):
    """
    Sends a file to S3 and deletes it from EC2
    """
    print("Sending file to S3")
    # Old files can be removed automatically through S3
    # Send files from EC2 to S3 and delete them in EC2
    send_str = "aws s3 cp " + file_name + " s3://kscu"
    ret_val = os.system(send_str)
    if ret_val != 0:
        print("Sending to S3 failed")
        send_aws_error_email()
        return

    os.system("rm " + file_name)
    print("File sent to S3")


def record(duration, show_info):
    """
    Records a show for the specified duration
    """
    print("Recording " + datetime.now().strftime("%H:%M:%S"))
    # Create string in the format below:
    # 'ffmpeg -i http://kscu.streamguys1.com:80/live -t "3600" -y output.mp3'
    command_str = (
        "ffmpeg -i http://kscu.streamguys1.com:80/live -t '"
        + duration
        + "' -y "
        + show_info["showFileName"]
    )
    ret_val = os.system(command_str)
    if ret_val != 0:
        print("Recording Failed")
        send_ffmpeg_error_email()
        return

    print("Recording Complete")
    send_to_s3(show_info["showFileName"])
    # Proccess show info to send emails to DJs
    for cur_dj in show_info["djs"]:
        send_to_dj(
            show_info["showFileName"],
            cur_dj["email"],
            show_info["showName"],
            cur_dj["name"],
        )


def run_schedule(todays_recording_sched):
    """
    Runs the schedule for the day
    """
    print("Running Schedule")
    # For each of the items in today's schedule
    # Add to recording schedule
    # Convert to epoch time for the enterabs function
    for show_info in todays_recording_sched:
        duration = str(show_info["duration"])
        epoch_start = int(show_info["showStart"].strftime("%s"))
        recorder_schedule.enterabs(
            epoch_start, 0, record, argument=(duration, show_info)
        )
    recorder_schedule.run()
    print("Schedule Complete")
    # At the end of the day, files will be sent out
    # Avoid recording delay from uploading files between shows


def main():
    """
    Main function
    """
    while True:
        if recorder_schedule.empty() and datetime.now().strftime("%H:%M")[-2:] == "00":
            print("Grabbing next 24 Shows")
            run_schedule(get_todays_shows())
        time.sleep(1)  # If there is not sleep, the CPU usage goes crazy while waiting


if __name__ == "__main__":
    main()
