"""
Error handling functions for the recording bot.
"""

from recorder.email_utils import send_error_email


def send_api_key_error_email():
    """
    Sends an error email when there's an issue with the Spinitron API key.
    """
    send_error_email("api_key_error")


def send_ffmpeg_error_email():
    """
    Sends an error email when there's an issue with ffmpeg.
    """
    send_error_email("ffmpeg_error")


def send_aws_error_email():
    """
    Sends an error email when there's an issue with AWS S3.
    """
    send_error_email("aws_error")
