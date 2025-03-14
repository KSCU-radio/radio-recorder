"""
Scheduler for recording shows
"""

import sched
import time
import threading
from datetime import datetime
from typing import Dict, List, Any

from config import schedule_logger
from recorder.recording import record
from recorder.api import get_todays_shows


class RecordingScheduler:
    """
    Class to manage show recording schedules with fault tolerance
    """

    def __init__(self):
        self.scheduler = sched.scheduler(time.time, time.sleep)
        self.is_running = False
        self.lock = threading.Lock()
        self.next_refresh_time = None

    def schedule_recording(self, show_info: Dict[str, Any]) -> bool:
        """
        Schedule a recording task

        Args:
            show_info (Dict[str, Any]): Show information dictionary

        Returns:
            bool: True if scheduled, False if show start is in the past
        """
        epoch_start = int(show_info["showStart"].strftime("%s"))
        current_time = int(time.time())

        # Only schedule if start time is in the future
        if epoch_start <= current_time:
            schedule_logger.warning(
                f"Show {show_info['showName']} start time "
                f"{show_info['showStart'].strftime('%Y-%m-%d %H:%M:%S')} "
                f"is in the past, skipping"
            )
            return False

        time_until_start = epoch_start - current_time
        schedule_logger.info(
            f"Scheduling {show_info['showName']} to record in {time_until_start//60} minutes "
            f"at {show_info['showStart'].strftime('%Y-%m-%d %H:%M:%S')}"
        )

        with self.lock:
            event = self.scheduler.enterabs(
                epoch_start, 0, self._safe_record, argument=(show_info,)
            )

        return True

    def _safe_record(self, show_info: Dict[str, Any]) -> None:
        """
        Wrapper around record function to handle exceptions

        Args:
            show_info (Dict[str, Any]): Show information dictionary
        """
        try:
            record(None, show_info)
        except Exception as e:
            schedule_logger.error(
                f"Error during recording of {show_info['showName']}: {e}"
            )
            # Optionally send an error email here
            from recorder.email_utils import send_error_email

            send_error_email(f"Recording error for {show_info['showName']}: {e}")

    def schedule_refresh(self, delay_hours: float = 1.0) -> None:
        """
        Schedule a refresh of the show list

        Args:
            delay_hours (float): Hours to wait before refreshing
        """
        next_refresh = time.time() + (delay_hours * 3600)
        self.next_refresh_time = datetime.fromtimestamp(next_refresh)

        schedule_logger.info(
            f"Scheduling next schedule refresh at {self.next_refresh_time.strftime('%Y-%m-%d %H:%M:%S')}"
        )

        with self.lock:
            self.scheduler.enterabs(next_refresh, 1, self._safe_refresh, ())

    def _safe_refresh(self) -> None:
        """
        Safely refresh the schedule and reschedule next refresh
        """
        try:
            schedule_logger.info("Refreshing show schedule")
            shows = get_todays_shows()

            for show_info in shows:
                self.schedule_recording(show_info)

            # Schedule next refresh
            self.schedule_refresh()
        except Exception as e:
            schedule_logger.error(f"Error during schedule refresh: {e}")
            # Schedule another refresh sooner since this one failed
            self.schedule_refresh(delay_hours=0.25)  # Try again in 15 minutes

    def run(self) -> None:
        """
        Run the scheduler in a fault-tolerant way
        """
        self.is_running = True

        while self.is_running:
            try:
                with self.lock:
                    # Run any pending events without blocking indefinitely
                    self.scheduler.run(blocking=False)

                # Sleep for a short time to prevent CPU spinning
                # but be responsive to new events
                time.sleep(1)
            except Exception as e:
                schedule_logger.error(f"Error in scheduler loop: {e}")
                # Keep running despite errors

    def start(self) -> threading.Thread:
        """
        Start the scheduler in a background thread

        Returns:
            threading.Thread: The scheduler thread
        """
        thread = threading.Thread(target=self.run, name="SchedulerThread")
        thread.daemon = True
        thread.start()
        return thread

    def stop(self) -> None:
        """
        Stop the scheduler
        """
        self.is_running = False

    def get_queue_info(self) -> Dict[str, Any]:
        """
        Get information about queued events

        Returns:
            Dict[str, Any]: Information about scheduled events
        """
        with self.lock:
            queue = list(self.scheduler.queue)

        return {
            "queue_length": len(queue),
            "next_event_time": (
                datetime.fromtimestamp(queue[0].time).strftime("%Y-%m-%d %H:%M:%S")
                if queue
                else None
            ),
            "next_refresh": (
                self.next_refresh_time.strftime("%Y-%m-%d %H:%M:%S")
                if self.next_refresh_time
                else None
            ),
        }


def run_schedule(todays_recording_sched: List[Dict[str, Any]]) -> None:
    """
    Runs the schedule for the day

    Args:
        todays_recording_sched (List[Dict[str, Any]]): List of shows to schedule
    """
    schedule_logger.info("Initializing recording schedule")

    if not todays_recording_sched:
        schedule_logger.warning("No shows to schedule for recording")
        return

    # For each of the items in today's schedule
    # Add to recording schedule
    # Convert to epoch time for the enterabs function
    recorder_schedule = sched.scheduler(time.time, time.sleep)

    for show_info in todays_recording_sched:
        epoch_start = int(show_info["showStart"].strftime("%s"))
        current_time = int(time.time())

        # Only schedule if start time is in the future
        if epoch_start > current_time:
            time_until_start = epoch_start - current_time
            schedule_logger.info(
                f"Scheduling {show_info['showName']} to record in {time_until_start//60} minutes "
                f"at {show_info['showStart'].strftime('%Y-%m-%d %H:%M:%S')}"
            )
            recorder_schedule.enterabs(
                epoch_start, 0, record, argument=(show_info["duration"], show_info)
            )
        else:
            schedule_logger.warning(
                f"Show {show_info['showName']} start time {show_info['showStart'].strftime('%Y-%m-%d %H:%M:%S')} "
                f"is in the past (now: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}), skipping"
            )

    schedule_logger.info(
        f"Schedule initialized with {len(recorder_schedule.queue)} events"
    )
    recorder_schedule.run()
    schedule_logger.info("Schedule execution completed")
