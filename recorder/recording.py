"""
Recording functions for the recording bot
"""

import time
from datetime import datetime
from typing import Any, Dict, Optional

from config import STREAM_URL, API_KEY, recording_logger
from recorder.file_ops import record_stream, send_to_s3
from recorder.api import request_spins
from recorder.email_utils import send_to_dj


def record(_, show_info: Dict[str, Any]) -> None:
    """
    Records a show for the specified duration

    Args:
        _ (Any): Placeholder parameter for scheduler compatibility
        show_info (Dict[str, Any]): Show information dictionary
    """
    recording_logger.info(
        f"Starting recording at {datetime.now().strftime('%H:%M:%S')}"
    )

    # Calculate actual remaining duration
    duration = int(show_info["showEnd"].strftime("%s")) - int(time.time())

    # If duration is less than 300s (5min), don't record
    if duration < 300:
        recording_logger.warning(
            f"Show {show_info['showName']} has less than 5min remaining, skipping recording"
        )
        return

    recording_logger.info(
        f"Recording {show_info['showName']} ({show_info['showFileName']}) "
        f"with scheduled duration {show_info['duration']} - actual duration {duration}"
    )

    # Record the stream
    success = record_stream(STREAM_URL, duration, show_info["showFileName"])

    if not success:
        recording_logger.error(f"Recording of {show_info['showName']} failed")
        return

    recording_logger.info(
        f"Recording of {show_info['showName']} completed successfully"
    )

    # Upload to S3
    if not send_to_s3(show_info["showFileName"]):
        recording_logger.error(f"Failed to upload {show_info['showFileName']} to S3")
        return

    # Request spin data
    recording_logger.debug("Requesting spin data for the show")
    spins_data = request_spins(show_info["showStart"], show_info["duration"], API_KEY)

    # Send emails to DJs
    from config import email_logger

    email_logger.info(
        f"Sending emails to {len(show_info['djs'])} DJs for show {show_info['showName']}"
    )

    for cur_dj in show_info["djs"]:
        send_to_dj(
            show_info,
            cur_dj["email"],
            cur_dj["name"],
            spins_data,
        )
