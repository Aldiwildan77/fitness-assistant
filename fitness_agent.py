import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List

from dotenv import load_dotenv
from langchain.schema import HumanMessage, SystemMessage
from langchain_community.callbacks import get_openai_callback
from langchain_community.chat_models import ChatOllama
from pydantic import BaseModel

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("fitness_agent.log"), logging.StreamHandler()],
)
logger = logging.getLogger("fitness_agent")

# Load environment variables
load_dotenv()

# Define the scope for Google Calendar API
SCOPES = ["https://www.googleapis.com/auth/calendar"]

# Set up LangSmith environment variables
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGCHAIN_API_KEY", "")
os.environ["LANGCHAIN_PROJECT"] = "fitness_agent"


class WorkoutPlan(BaseModel):
    day: str
    exercises: List[Dict[str, str]]
    duration: str
    intensity: str


class DietPlan(BaseModel):
    meal_type: str
    foods: List[str]
    calories: int
    macros: Dict[str, float]


class FitnessAgent:
    def __init__(self, model_name: str = "llama2"):
        logger.info(f"Initializing FitnessAgent with model: {model_name}")
        self.llm = ChatOllama(
            model=model_name,
            temperature=0.7,
            base_url="http://localhost:11434",
            format="json",  # Enable JSON mode for better structured responses
        )
        # Skip calendar service initialization
        self.calendar_service = None
        logger.debug("FitnessAgent initialized successfully")

    def _setup_calendar_service(self):
        """Setup Google Calendar service with authentication."""
        # Skip actual calendar setup
        logger.debug("Calendar setup skipped")
        return None

    def create_workout_plan(self, days: int, fitness_level: str) -> List[WorkoutPlan]:
        """Create a personalized workout plan."""
        logger.info(f"Creating workout plan for {days} days at {fitness_level} level")
        # Enable tracing for this function
        with get_openai_callback() as cb:
            system_prompt = """You are a professional fitness trainer. Create detailed workout plans that are safe and effective.
            Format your response as a JSON array of workout plans, where each plan includes:
            - day: string
            - exercises: array of objects with name (string), sets (string), reps (string), and rest_period (string)
            - duration: string
            - intensity: string
            """

            user_prompt = f"""Create a {days}-day workout plan for someone with {fitness_level} fitness level.
            Include exercises, sets, reps, and rest periods for each day."""

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]

            logger.debug(f"Sending workout plan prompt to LLM: {user_prompt}")
            response = self.llm.invoke(messages)
            logger.debug(f"Received response from LLM: {response.content[:200]}...")

            try:
                # Parse the JSON response
                workout_data = json.loads(response.content)
                logger.debug(f"Parsed workout data: {workout_data}")

                plans = []
                for plan_data in workout_data:
                    try:
                        # Ensure exercises is a list of dictionaries
                        if "exercises" in plan_data and isinstance(
                            plan_data["exercises"], list
                        ):
                            # Make sure all exercise attributes are strings
                            for exercise in plan_data["exercises"]:
                                if isinstance(exercise, dict):
                                    for key, value in exercise.items():
                                        exercise[key] = str(value)
                                else:
                                    logger.error(
                                        f"Exercise is not a dictionary: {exercise}"
                                    )
                                    continue

                        plan = WorkoutPlan(**plan_data)
                        plans.append(plan)
                    except Exception as e:
                        logger.error(
                            f"Error creating WorkoutPlan from data: {plan_data}"
                        )
                        logger.error(f"Exception: {e}")

                if plans:
                    logger.info(
                        f"Workout plan created successfully. Tokens used: {cb.total_tokens}"
                    )
                    logger.debug(f"Created {len(plans)} workout plans")
                    return plans
                else:
                    logger.warning(
                        "No valid workout plans were created, using fallback"
                    )
                    return self._create_fallback_workout_plan(days)
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing workout plan JSON: {e}")
                logger.error(f"Raw response: {response.content}")
                return self._create_fallback_workout_plan(days)
            except Exception as e:
                logger.error(f"Unexpected error creating workout plan: {e}")
                logger.error(f"Raw response: {response.content}")
                return self._create_fallback_workout_plan(days)

    def _create_fallback_workout_plan(self, days: int) -> List[WorkoutPlan]:
        """Create a fallback workout plan when the LLM response fails."""
        logger.info(f"Creating fallback workout plan for {days} days")
        return [
            WorkoutPlan(
                day=f"Day {i+1}",
                exercises=[
                    {
                        "name": "Push-ups",
                        "sets": "3",
                        "reps": "12",
                        "rest_period": "60s",
                    },
                    {"name": "Squats", "sets": "3", "reps": "15", "rest_period": "60s"},
                    {"name": "Plank", "sets": "3", "reps": "30s", "rest_period": "60s"},
                ],
                duration="45 minutes",
                intensity="moderate",
            )
            for i in range(days)
        ]

    def create_diet_plan(self, daily_calories: int) -> List[DietPlan]:
        """Create a personalized diet plan."""
        logger.info(f"Creating diet plan for {daily_calories} calories")
        # Enable tracing for this function
        with get_openai_callback() as cb:
            system_prompt = """You are a professional nutritionist. Create detailed diet plans that are balanced and healthy.
            Format your response as a JSON array of meal plans, where each plan includes:
            - meal_type: string
            - foods: array of strings
            - calories: integer
            - macros: object with protein, carbs, and fat values as floats
            """

            user_prompt = f"""Create a diet plan targeting {daily_calories} calories per day.
            Include meal breakdowns and macro distribution."""

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]

            logger.debug(f"Sending diet plan prompt to LLM: {user_prompt}")
            response = self.llm.invoke(messages)
            logger.debug(f"Received response from LLM: {response.content[:200]}...")

            try:
                # Parse the JSON response
                diet_data = json.loads(response.content)
                logger.debug(f"Parsed diet data: {diet_data}")

                plans = []
                for meal_data in diet_data:
                    try:
                        # Ensure calories is an integer
                        if "calories" in meal_data and not isinstance(
                            meal_data["calories"], int
                        ):
                            meal_data["calories"] = int(
                                float(str(meal_data["calories"]).replace(",", ""))
                            )

                        # Ensure macros values are floats
                        if "macros" in meal_data and isinstance(
                            meal_data["macros"], dict
                        ):
                            for key, value in meal_data["macros"].items():
                                if not isinstance(value, float):
                                    meal_data["macros"][key] = float(
                                        str(value).replace(",", "")
                                    )

                        plan = DietPlan(**meal_data)
                        plans.append(plan)
                    except Exception as e:
                        logger.error(f"Error creating DietPlan from data: {meal_data}")
                        logger.error(f"Exception: {e}")

                if plans:
                    logger.info(
                        f"Diet plan created successfully. Tokens used: {cb.total_tokens}"
                    )
                    logger.debug(f"Created {len(plans)} diet plans")
                    return plans
                else:
                    logger.warning("No valid diet plans were created, using fallback")
                    return self._create_fallback_diet_plan()
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing diet plan JSON: {e}")
                logger.error(f"Raw response: {response.content}")
                return self._create_fallback_diet_plan()
            except Exception as e:
                logger.error(f"Unexpected error creating diet plan: {e}")
                logger.error(f"Raw response: {response.content}")
                return self._create_fallback_diet_plan()

    def _create_fallback_diet_plan(self) -> List[DietPlan]:
        """Create a fallback diet plan when the LLM response fails."""
        logger.info("Creating fallback diet plan")
        return [
            DietPlan(
                meal_type="Breakfast",
                foods=["Oatmeal", "Banana", "Protein Shake"],
                calories=500,
                macros={"protein": 30.0, "carbs": 60.0, "fat": 10.0},
            ),
            DietPlan(
                meal_type="Lunch",
                foods=["Chicken Breast", "Brown Rice", "Broccoli"],
                calories=700,
                macros={"protein": 40.0, "carbs": 45.0, "fat": 15.0},
            ),
            DietPlan(
                meal_type="Dinner",
                foods=["Salmon", "Sweet Potato", "Asparagus"],
                calories=600,
                macros={"protein": 35.0, "carbs": 35.0, "fat": 30.0},
            ),
            DietPlan(
                meal_type="Snack",
                foods=["Greek Yogurt", "Almonds", "Berries"],
                calories=300,
                macros={"protein": 20.0, "carbs": 15.0, "fat": 15.0},
            ),
        ]

    def schedule_workout(self, workout: WorkoutPlan, date: datetime):
        """Print workout schedule information instead of actually scheduling it."""
        print(f"\nScheduled Workout for {date.strftime('%Y-%m-%d')}:")
        print(f"Day: {workout.day}")
        print(f"Duration: {workout.duration}")
        print(f"Intensity: {workout.intensity}")
        print("Exercises:")
        for exercise in workout.exercises:
            print(
                f"- {exercise['name']}: {exercise['sets']} sets x {exercise['reps']} reps"
            )
        print("-" * 50)

    def get_workout_schedule(self, start_date: datetime, days: int) -> List[Dict]:
        """Return a mock schedule instead of actual calendar events."""
        mock_schedule = []
        for i in range(days):
            mock_schedule.append(
                {
                    "summary": f"Workout: Day {i+1}",
                    "start": {
                        "dateTime": (start_date + timedelta(days=i)).isoformat(),
                        "timeZone": "UTC",
                    },
                    "end": {
                        "dateTime": (
                            start_date + timedelta(days=i, hours=1)
                        ).isoformat(),
                        "timeZone": "UTC",
                    },
                }
            )
        return mock_schedule

    def validate_workout_plan(self, plan: List[WorkoutPlan]) -> bool:
        """Validate the workout plan for safety and effectiveness."""
        logger.info("Validating workout plan")
        # Enable tracing for this function
        with get_openai_callback() as cb:
            system_prompt = """You are a fitness safety expert. Validate the workout plan for safety and effectiveness.
            Return a JSON object with:
            - is_valid: boolean
            - issues: array of strings (empty if valid)
            """

            # Convert plan to JSON string for the prompt
            plan_json = json.dumps([p.model_dump() for p in plan])
            user_prompt = f"Validate this workout plan: {plan_json}"

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]

            logger.debug(f"Sending validation prompt to LLM for {len(plan)} plans")
            response = self.llm.invoke(messages)
            logger.debug(
                f"Received validation response from LLM: {response.content[:200]}..."
            )

            try:
                validation = json.loads(response.content)
                is_valid = validation.get("is_valid", False)
                logger.info(
                    f"Workout plan validation completed. Tokens used: {cb.total_tokens}"
                )
                logger.debug(
                    f"Validation result: {is_valid}, issues: {validation.get('issues', [])}"
                )
                return is_valid
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing validation JSON: {e}")
                logger.error(f"Raw response: {response.content}")
                return False
            except Exception as e:
                logger.error(f"Unexpected error validating workout plan: {e}")
                return False

    def refine_workout_context(
        self, user_feedback: str, current_plan: List[WorkoutPlan]
    ) -> List[WorkoutPlan]:
        """Refine the workout plan based on user feedback."""
        logger.info(f"Refining workout plan based on feedback: {user_feedback}")
        # Enable tracing for this function
        with get_openai_callback() as cb:
            system_prompt = """You are a professional fitness trainer. Refine the workout plan based on user feedback.
            Format your response as a JSON array of refined workout plans, maintaining the same structure as the input."""

            # Convert current plan to JSON string for the prompt
            plan_json = json.dumps([p.model_dump() for p in current_plan])
            user_prompt = f"""Based on the following feedback: {user_feedback}
            Refine this workout plan: {plan_json}"""

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]

            logger.debug(f"Sending refinement prompt to LLM: {user_feedback}")
            response = self.llm.invoke(messages)
            logger.debug(
                f"Received refinement response from LLM: {response.content[:200]}..."
            )

            try:
                # Parse the JSON response
                refined_data = json.loads(response.content)
                logger.debug(f"Parsed refined data: {refined_data}")

                plans = []
                for plan_data in refined_data:
                    try:
                        # Ensure exercises is a list of dictionaries with string values
                        if "exercises" in plan_data and isinstance(
                            plan_data["exercises"], list
                        ):
                            for exercise in plan_data["exercises"]:
                                if isinstance(exercise, dict):
                                    for key, value in exercise.items():
                                        exercise[key] = str(value)
                                else:
                                    logger.error(
                                        f"Exercise is not a dictionary: {exercise}"
                                    )
                                    continue

                        plan = WorkoutPlan(**plan_data)
                        plans.append(plan)
                    except Exception as e:
                        logger.error(
                            f"Error creating refined WorkoutPlan from data: {plan_data}"
                        )
                        logger.error(f"Exception: {e}")

                if plans:
                    logger.info(
                        f"Workout plan refined successfully. Tokens used: {cb.total_tokens}"
                    )
                    logger.debug(f"Refined {len(plans)} workout plans")
                    return plans
                else:
                    logger.warning(
                        "No valid refined workout plans were created, returning original"
                    )
                    return current_plan
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing refined plan JSON: {e}")
                logger.error(f"Raw response: {response.content}")
                logger.info("Returning original plan due to error")
                return current_plan
            except Exception as e:
                logger.error(f"Unexpected error refining workout plan: {e}")
                logger.info("Returning original plan due to unexpected error")
                return current_plan


def main():
    logger.info("Starting Fitness Agent application")
    # Initialize the agent with Ollama model (default: llama2)
    agent = FitnessAgent(model_name="llama2")

    print("Agent initialized", agent)

    # Example usage
    workout_plan = agent.create_workout_plan(days=4, fitness_level="intermediate")
    diet_plan = agent.create_diet_plan(daily_calories=2200)

    print("\nGenerated Workout Plan:")
    for plan in workout_plan:
        print(f"\n{plan.day}:")
        print(f"Duration: {plan.duration}")
        print(f"Intensity: {plan.intensity}")
        print("Exercises:")
        for exercise in plan.exercises:
            print(
                f"- {exercise['name']}: {exercise['sets']} sets x {exercise['reps']} reps"
            )

    print("\nGenerated Diet Plan:")
    for meal in diet_plan:
        print(f"\n{meal.meal_type}:")
        print(f"Calories: {meal.calories}")
        print(f"Macros: {meal.macros}")
        print("Foods:")
        for food in meal.foods:
            print(f"- {food}")

    # Validate the workout plan
    is_valid = agent.validate_workout_plan(workout_plan)
    print(f"\nWorkout plan validation result: {'Valid' if is_valid else 'Invalid'}")

    # Example of refining the workout plan based on feedback
    feedback = "The leg exercises are too intense, and I need more upper body focus"
    refined_plan = agent.refine_workout_context(feedback, workout_plan)

    print("\nRefined Workout Plan:")
    for plan in refined_plan:
        print(f"\n{plan.day}:")
        print(f"Duration: {plan.duration}")
        print(f"Intensity: {plan.intensity}")
        print("Exercises:")
        for exercise in plan.exercises:
            print(
                f"- {exercise['name']}: {exercise['sets']} sets x {exercise['reps']} reps"
            )

    # Schedule workouts (now just prints the schedule)
    print("\nScheduling Workouts:")
    start_date = datetime.now()
    for i, workout in enumerate(workout_plan):
        agent.schedule_workout(workout, start_date + timedelta(days=i))

    # Get scheduled workouts (now returns mock schedule)
    schedule = agent.get_workout_schedule(start_date, days=4)
    print("\nWorkout Schedule Summary:")
    for event in schedule:
        print(f"- {event['summary']} on {event['start']['dateTime']}")

    logger.info("Fitness Agent application completed successfully")


if __name__ == "__main__":
    main()
