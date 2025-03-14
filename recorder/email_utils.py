"""
Email utility functions for the recording bot
"""

import re
import smtplib
import logging
from typing import Dict, List, Any, Optional
from email.message import EmailMessage

from config import EMAIL, PASSWORD, S3_BUCKET, email_logger


def send_email(
    subject: str, recipient: str, body: str, cc: Optional[str] = None
) -> bool:
    """
    Generic function to send emails with proper error handling

    Args:
        subject (str): Email subject
        recipient (str): Recipient email address
        body (str): Email body content
        cc (str, optional): CC recipient

    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    try:
        # Validate recipient email
        email_regex = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
        if not re.fullmatch(email_regex, recipient):
            email_logger.error(f"Invalid recipient email address: {recipient}")
            return False

        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = EMAIL
        message["To"] = recipient
        if cc:
            message["Cc"] = cc
        message.set_content(body)

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(EMAIL, PASSWORD)
        server.send_message(message)
        server.quit()

        email_logger.info(f"Email sent successfully to {recipient}")
        return True
    except smtplib.SMTPException as e:
        email_logger.error(f"SMTP error while sending email to {recipient}: {e}")
        return False
    except Exception as e:
        email_logger.error(f"Unexpected error while sending email to {recipient}: {e}")
        return False


def send_to_dj(
    show_info: Dict[str, Any],
    email: str,
    dj_name: str,
    spins_data: Optional[List[Dict[str, str]]] = None,
) -> None:
    """
    Sends an email to the DJ with a link to download their show

    Args:
        show_info (Dict[str, Any]): Show information dictionary
        email (str): DJ's email address
        dj_name (str): DJ's name
        spins_data (Optional[List[Dict[str, str]]]): List of spins during the show
    """
    try:
        # Validate required keys in show_info
        required_keys = ["showStart", "showName", "showFileName"]
        for key in required_keys:
            if key not in show_info:
                raise KeyError(f"Missing required key in show_info: {key}")

        # Format date for email
        show_start = show_info["showStart"].strftime("%m/%d/%Y")
        subject = f"{show_info['showName']} Recording Link - {show_start}"

        # Construct email body
        text = f"""
Hey {dj_name}! 

This is an automated email from KSCU. 

You can use the link below to download your show.
We only keep your recording for 90 days so you will need to download it to keep it permanently.
"""
        text += (
            "\nDownload here: "
            + f"https://{S3_BUCKET}.s3.us-west-1.amazonaws.com/"
            + show_info["showFileName"]
            + "\n"
        )

        if spins_data and isinstance(spins_data, list) and len(spins_data) > 0:
            text += "\nSpins during your show:\n"
            for spin in spins_data:
                if "song" in spin and "artist" in spin:
                    text += f"{spin['song']} - {spin['artist']}\n"
        text += """
If there's any issues with this system, please let us know by emailing web@kscu.org.
"""

        # Validate email format
        regex = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
        if re.fullmatch(regex, email) is None:
            email = "web@kscu.org"
            subject = f"Public Email Address Needs Updating - {show_info['showName']}"
            text = f"""
***********************

This is an automated email from the radio recording bot to let you know that the public email address for {dj_name} needs to be updated.

Please include the DJ's email address in the "Public Email" field on Spinitron.

This DJ's show has been recorded and can be downloaded here: https://{S3_BUCKET}.s3.us-west-1.amazonaws.com/{show_info['showFileName']}.

Forward this email to the DJ so they can access this show, but please make sure to update their email address on Spinitron for future shows.

***********************
"""

        # Send the email
        send_email(
            subject, email, text, cc="gm@kscu.org" if email == "web@kscu.org" else None
        )

    except KeyError as e:
        email_logger.error(f"KeyError in send_to_dj: {e}")
    except Exception as e:
        email_logger.error(f"An unexpected error occurred in send_to_dj: {e}")


def send_error_email(error_type: str) -> None:
    """
    Sends an error notification email

    Args:
        error_type (str): Type of error (api_key_error, ffmpeg_error, aws_error)
    """
    if error_type == "api_key_error":
        subject = "Recording Bot API Key Error"
        body = """
***********************                            

This is an automated email from the radio recording bot to let you know that there is an issue with the Spinitron API key.

The bot was unable to retrieve data from the Spinitron API after multiple attempts.

Please check the API key in config.toml and ensure it is correct.
For help, contact Aidan via email at hi@aidansmith.me

***********************
"""
    elif error_type == "ffmpeg_error":
        subject = "Recording Bot FFMPEG Error"
        body = """
***********************

This is an automated email from the radio recording bot to let you know that there is an issue with ffmpeg.

The bot was unable to record a show due to an ffmpeg error.

If this happens frequently, contact Aidan via email at hi@aidansmith.me

***********************
"""
    elif error_type == "aws_error":
        subject = "Recording Bot AWS S3 Error"
        body = """
***********************

This is an automated email from the radio recording bot to let you know that there is an issue with AWS S3.

The bot was unable to upload a recorded show to S3.

If this happens frequently, contact Aidan via email at hi@aidansmith.me
                            
***********************
"""
    else:
        subject = "Recording Bot Error"
        body = f"""
***********************

This is an automated email from the radio recording bot to let you know that there was an error: {error_type}.

Please check the logs for more information.

***********************
"""

    send_email(subject, "web@kscu.org", body, cc="gm@kscu.org")
