"""Provides EmailMessage class for generating email messages"""
from email.message import EmailMessage
import smtplib

from recorder import EMAIL, PASSWORD

# Error handling functions
def send_api_key_error_email():
    """
    Sends an email to web@kscu.org when the API key might need updating
    """
    print("Sending API key error email")
    subject = "Spinitron API key might need updating"
    text = """
    Hello,

    This is an automated email from the radio recording bot.

    The Spinitron API has returned an error 400 times in a row. 
    
    The API key may be invalid, or Spinitron simply may be unavaliable. If this error persists, you can email me at 'aidansmith.me'.

    Best regards,
    KSCU Bot
    """

    # Form message
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = EMAIL
    message["To"] = "web@kscu.org"
    message["Cc"] = "gm@kscu.org"
    message.set_content(text)

    # Open connection to Gmail server to send message
    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(EMAIL, PASSWORD)
    server.send_message(message)
    server.quit()
    print("API key error email sent")


def send_ffmpeg_error_email():
    """
    Sends an email to web@kscu.org when ffmpeg fails to record a show
    """
    print("Sending ffmpeg error email")
    subject = "ffmpeg failed to record a show"
    text = """
    Hello,

    This is an automated email from the radio recording bot.

    ffmpeg has failed to record a show. You likely can ignore this email, but if it happens regularly, you can email me at 'aidansmith.me'.

    Best regards,
    KSCU Bot
    """

    # Form message
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = EMAIL
    message["To"] = "web@kscu.org"
    message["Cc"] = "gm@kscu.org"
    message.set_content(text)

    # Open connection to Gmail server to send message
    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(EMAIL, PASSWORD)
    server.send_message(message)
    server.quit()
    print("ffmpeg error email sent")


def send_aws_error_email():
    """
    Sends an email to web@kscu.org to notify them that AWS has failed to upload a show to S3
    """
    print("Sending AWS error email")
    subject = "AWS failed to upload a show to S3"
    text = """
    Hello,

    This is an automated email from the radio recording bot.

    AWS has failed to upload a show to S3. You likely can ignore this email, but if it happens regularly, you can email me at 'aidansmith.me'.

    Best regards,
    KSCU Bot
    """

    # Form message
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = EMAIL
    message["To"] = "web@kscu.org"
    message["Cc"] = "gm@kscu.org"
    message.set_content(text)

    # Open connection to Gmail server to send message
    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(EMAIL, PASSWORD)
    server.send_message(message)
    server.quit()
    print("AWS error email sent")
