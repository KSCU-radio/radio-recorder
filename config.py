"""Used to initialize the environment variables for the email and password"""
import os
import logging
from dotenv import load_dotenv

load_dotenv()

EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")

logging.info("Email and password loaded from environment variables")
