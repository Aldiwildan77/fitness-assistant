import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from uuid import uuid4

from dotenv import load_dotenv
from ics import Calendar, Event

from fitness_agent import WorkoutPlan

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/calendar_agent.log"),
        # logging.StreamHandler()
    ],
)
logger = logging.getLogger("calendar_agent")

# Load environment variables
load_dotenv()


class CalendarAgent:
    def __init__(self, output_dir: str = "calendars"):
        """Initialize the Calendar Agent.

        Args:
            output_dir: Directory to save generated ICS files
        """
        logger.info("Initializing CalendarAgent")
        self.output_dir = output_dir

        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            logger.debug(f"Created output directory: {output_dir}")

    def create_workout_calendar(
        self,
        workout_plans: List[WorkoutPlan],
        start_date: datetime,
        calendar_name: str = "Workout Schedule",
        workout_duration_minutes: int = 60,
    ) -> str:
        """Create an ICS calendar file from workout plans.

        Args:
            workout_plans: List of WorkoutPlan objects
            start_date: Start date for the first workout
            calendar_name: Name of the calendar
            workout_duration_minutes: Default duration of workout events in minutes

        Returns:
            Path to the generated ICS file
        """
        logger.info(f"Creating workout calendar with {len(workout_plans)} workouts")

        # Create a new calendar
        cal = Calendar()
        cal.creator = "Fitness Agent - Calendar Generator"

        # Add workout events to calendar
        for i, workout in enumerate(workout_plans):
            event = Event()
            event.name = f"Workout: {workout.day}"

            # Create detailed description from workout plan
            description = f"Intensity: {workout.intensity}\n"
            description += "Exercises:\n"
            for exercise in workout.exercises:
                description += f"- {exercise['name']}: {exercise['sets']} sets x {exercise['reps']} reps"
                if "rest_period" in exercise:
                    description += f" (Rest: {exercise['rest_period']})"
                description += "\n"

            event.description = description

            # Set event dates
            event_date = start_date + timedelta(days=i)
            event.begin = event_date
            event.duration = timedelta(minutes=workout_duration_minutes)

            # Generate unique ID
            event.uid = str(uuid4())

            # Add event to calendar
            cal.events.add(event)
            logger.debug(
                f"Added event for {workout.day} on {event_date.strftime('%Y-%m-%d')}"
            )

        # Save calendar to file
        filename = (
            f"{calendar_name.replace(' ', '_')}_{start_date.strftime('%Y%m%d')}.ics"
        )
        filepath = os.path.join(self.output_dir, filename)

        with open(filepath, "w") as f:
            f.write(str(cal))

        logger.info(f"Saved calendar to {filepath}")
        return filepath

    def create_custom_calendar(
        self, events: List[Dict], calendar_name: str = "Custom Calendar"
    ) -> str:
        """Create an ICS calendar file from custom events.

        Args:
            events: List of event dictionaries with keys:
                - name: Event name
                - description: Event description
                - begin: Start datetime
                - duration: Duration in minutes
                - location (optional): Event location
            calendar_name: Name of the calendar

        Returns:
            Path to the generated ICS file
        """
        logger.info(f"Creating custom calendar with {len(events)} events")

        # Create a new calendar
        cal = Calendar()
        cal.creator = "Fitness Agent - Calendar Generator"

        # Add events to calendar
        for event_data in events:
            event = Event()
            event.name = event_data["name"]
            event.description = event_data["description"]
            event.begin = event_data["begin"]
            event.duration = timedelta(minutes=event_data["duration"])

            if "location" in event_data:
                event.location = event_data["location"]

            # Generate unique ID
            event.uid = str(uuid4())

            # Add event to calendar
            cal.events.add(event)
            logger.debug(
                f"Added event: {event.name} on {event.begin.strftime('%Y-%m-%d')}"
            )

        # Save calendar to file
        filename = (
            f"{calendar_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.ics"
        )
        filepath = os.path.join(self.output_dir, filename)

        with open(filepath, "w") as f:
            f.write(str(cal))

        logger.info(f"Saved calendar to {filepath}")
        return filepath

    def add_to_existing_calendar(
        self, calendar_path: str, new_events: List[Dict]
    ) -> str:
        """Add events to an existing ICS calendar file.

        Args:
            calendar_path: Path to existing ICS file
            new_events: List of event dictionaries

        Returns:
            Path to the updated ICS file
        """
        logger.info(
            f"Adding {len(new_events)} events to existing calendar: {calendar_path}"
        )

        # Load existing calendar
        with open(calendar_path, "r") as f:
            cal = Calendar(f.read())

        # Add new events
        for event_data in new_events:
            event = Event()
            event.name = event_data["name"]
            event.description = event_data["description"]
            event.begin = event_data["begin"]
            event.duration = timedelta(minutes=event_data["duration"])

            if "location" in event_data:
                event.location = event_data["location"]

            # Generate unique ID
            event.uid = str(uuid4())

            # Add event to calendar
            cal.events.add(event)
            logger.debug(f"Added event: {event.name} to existing calendar")

        # Save updated calendar
        with open(calendar_path, "w") as f:
            f.write(str(cal))

        logger.info(f"Updated calendar saved to {calendar_path}")
        return calendar_path

    def get_calendar_link(self, calendar_path: str) -> str:
        """Get a shareable link or file path for the calendar.

        In a real application, this might upload the file to a cloud storage
        or web server to create a shareable URL. For now, we'll return the file path.

        Args:
            calendar_path: Path to the ICS file

        Returns:
            A shareable link or file path
        """
        # For now, just return the file path
        return f"file://{os.path.abspath(calendar_path)}"


def main():
    """Test function to demonstrate calendar creation"""
    from fitness_agent import FitnessAgent, WorkoutPlan

    print("Creating sample workout calendar...")

    # Create a sample workout plan
    agent = FitnessAgent(model_name="llama2")
    workout_plans = agent.create_workout_plan(days=5, fitness_level="intermediate")

    # Create a calendar
    calendar_agent = CalendarAgent()
    calendar_path = calendar_agent.create_workout_calendar(
        workout_plans=workout_plans,
        start_date=datetime.now(),
        calendar_name="My Workout Schedule",
    )

    print(f"Calendar created at: {calendar_path}")
    print(
        "You can import this file into any calendar application that supports ICS format."
    )
    print("(Google Calendar, Apple Calendar, Outlook, etc.)")


if __name__ == "__main__":
    main()
