"""
File operations for the recording bot
"""

import subprocess
from pathlib import Path
from typing import Optional

from config import S3_BUCKET, file_logger
from recorder.email_utils import send_error_email


def record_stream(
    stream_url: str,
    duration: int,
    output_filename: str,
    ffmpeg_path: Optional[str] = None,
) -> bool:
    """
    Records a stream for a specified duration using ffmpeg

    Args:
        stream_url (str): URL of the stream to record
        duration (int): Duration to record in seconds
        output_filename (str): Output filename
        ffmpeg_path (str, optional): Path to ffmpeg executable

    Returns:
        bool: True if recording was successful, False otherwise
    """
    if ffmpeg_path is None:
        ffmpeg_path = "/usr/bin/ffmpeg"

    # Ensure paths are properly escaped and safe
    output_path = Path(output_filename).absolute()

    # Use a list of arguments instead of shell=True
    cmd = [ffmpeg_path, "-i", stream_url, "-t", str(duration), "-y", str(output_path)]

    from config import recording_logger

    recording_logger.debug(f"Running command: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, stderr=subprocess.PIPE, text=True, check=False)

        if result.returncode != 0:
            recording_logger.error(f"Recording failed: {result.stderr}")
            send_error_email("ffmpeg_error")
            return False

        recording_logger.info(f"Recording saved to {output_filename}")
        return True
    except subprocess.SubprocessError as e:
        recording_logger.error(f"Subprocess error during recording: {e}")
        return False
    except Exception as e:
        recording_logger.error(f"Unexpected error during recording: {e}")
        return False


def upload_to_s3(filename: str) -> bool:
    """
    Uploads a file to S3 using the AWS CLI

    Args:
        filename (str): Path to file to upload

    Returns:
        bool: True if upload was successful, False otherwise
    """
    file_logger.info(f"Uploading {filename} to S3 bucket {S3_BUCKET}")

    # Use a list of arguments instead of shell=True
    cmd = ["aws", "s3", "cp", filename, f"s3://{S3_BUCKET}/"]

    file_logger.debug(f"Running command: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, stderr=subprocess.PIPE, text=True, check=False)

        if result.returncode != 0:
            file_logger.error(f"S3 upload failed: {result.stderr}")
            send_error_email("aws_error")
            return False

        file_logger.info(f"File {filename} successfully uploaded to S3")
        return True
    except subprocess.SubprocessError as e:
        file_logger.error(f"Subprocess error during S3 upload: {e}")
        return False
    except Exception as e:
        file_logger.error(f"Unexpected error during S3 upload: {e}")
        return False


def delete_file(filename: str) -> bool:
    """
    Safely delete a file

    Args:
        filename (str): Path to file to delete

    Returns:
        bool: True if deletion was successful, False otherwise
    """
    try:
        file_path = Path(filename)
        if file_path.exists():
            file_path.unlink()
            file_logger.debug(f"Successfully deleted file: {filename}")
            return True
        else:
            file_logger.warning(f"File not found for deletion: {filename}")
            return False
    except Exception as e:
        file_logger.error(f"Error deleting file {filename}: {e}")
        return False


def send_to_s3(filename: str) -> bool:
    """
    Uploads a file to S3 and deletes it locally if successful

    Args:
        filename (str): Path to file to upload

    Returns:
        bool: True if the process was successful
    """
    file_logger.info(f"Sending file {filename} to S3")

    # Upload to S3
    if not upload_to_s3(filename):
        return False

    # Delete local file after successful upload
    if delete_file(filename):
        return True
    else:
        file_logger.warning(
            f"File uploaded to S3 but local file {filename} could not be deleted"
        )
        return True  # Still consider successful even if local deletion fails
