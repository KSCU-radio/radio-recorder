#!/usr/bin/env python3
"""
Main entry point for the radio show recording bot.
"""
import time
import sys
import signal
import logging
from datetime import datetime

# Import configuration
import config
from config import logger

# Import recorder components
from recorder.api import get_todays_shows
from recorder.scheduler import RecordingScheduler
from recorder.email_utils import send_email

# Global scheduler instance
scheduler = None


def signal_handler(sig, frame):
    """
    Handle interrupt signals
    """
    logger.info("Received interrupt signal, shutting down gracefully...")
    if scheduler:
        scheduler.stop()
    sys.exit(0)


def main():
    """
    Main function with improved fault tolerance and efficiency
    """
    global scheduler

    logger.info("Recording bot started")

    try:
        # Register signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Initialize the scheduler
        scheduler = RecordingScheduler()

        # Initial schedule load
        shows = get_todays_shows()

        if not shows:
            logger.warning("No shows found to schedule. Will retry later.")

        # Schedule all shows
        for show_info in shows:
            scheduler.schedule_recording(show_info)

        # Schedule next refresh
        scheduler.schedule_refresh()

        # Start scheduler in background thread
        scheduler_thread = scheduler.start()

        # Main monitoring loop
        while True:
            try:
                # Report health status periodically
                queue_info = scheduler.get_queue_info()
                logger.info(
                    f"Bot healthy: {queue_info['queue_length']} shows in queue. "
                    f"Next refresh at {queue_info['next_refresh']}"
                )

                # Sleep for a minute
                time.sleep(60)
            except KeyboardInterrupt:
                logger.info("Received keyboard interrupt, shutting down...")
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                # Continue despite errors

    except Exception as e:
        logger.critical(f"Critical error in main function: {e}")
        # Send an email about the critical failure
        send_email(
            subject="Recording Bot Critical Failure",
            recipient="web@kscu.org",
            body=f"The recording bot has encountered a critical error and may need restart: {e}",
            cc="hi@aidansmith.me",
        )
    finally:
        if scheduler:
            scheduler.stop()
        logger.info("Recording bot shutting down")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # Last resort error handling
        logger.critical(f"Unhandled exception: {e}")
        # Try to send an email, but don't crash if it fails
        try:
            send_email(
                subject="Recording Bot Crashed",
                recipient="web@kscu.org",
                body=f"The recording bot has crashed with an unhandled exception: {e}",
                cc="hi@aidansmith.me",
            )
        except Exception as email_error:
            print(f"Failed to send error email: {email_error}")
            pass
