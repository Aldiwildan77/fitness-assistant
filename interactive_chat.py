import json
import logging
from datetime import datetime, timedelta

from dotenv import load_dotenv
from langchain.schema import HumanMessage, SystemMessage
from langchain_community.callbacks import get_openai_callback
from langchain_community.chat_models import ChatOllama

# Import our FitnessAgent, CalendarAgent, and DatabaseManager
from calendar_agent import CalendarAgent
from db_manager import DatabaseManager
from fitness_agent import FitnessAgent

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/interactive_chat.log"),
        # logging.StreamHandler()
    ],
)
logger = logging.getLogger("interactive_chat")

# Load environment variables
load_dotenv()


class InteractiveChat:
    def __init__(self, model_name="llama2", username="default_user"):
        logger.info(f"Initializing InteractiveChat with model: {model_name}")
        self.llm = ChatOllama(
            model=model_name,
            temperature=0.7,
            base_url="http://localhost:11434",
        )
        self.username = username
        self.fitness_agent = FitnessAgent(model_name=model_name)
        self.calendar_agent = CalendarAgent()
        self.db_manager = DatabaseManager()

        # Get or create user in database
        self.user_id, user_created = self.db_manager.get_or_create_user(username)
        if user_created:
            logger.info(f"Created new user: {username} with ID: {self.user_id}")
        else:
            logger.info(f"Using existing user: {username} with ID: {self.user_id}")

        # Initialize context with data from database if available
        self.chat_history = []
        self.context = {
            "user_profile": (
                self.db_manager.get_profile(self.user_id) if self.user_id > 0 else {}
            ),
            "current_workout_plan": None,
            "current_diet_plan": None,
            "calendar_files": [],
            "saved_workout_plans": [],
            "saved_diet_plans": [],
        }

        # Load saved plans
        if self.user_id > 0:
            self.load_saved_plans()

        # System prompt for the chat interface
        self.system_prompt = """You are a helpful fitness assistant. You can help users with:
1. Creating personalized workout plans
2. Creating diet plans
3. Scheduling workouts
4. Exporting workout plans to calendar (ICS) files
5. Answering fitness-related questions
6. Giving health and wellness advice

Be conversational, friendly, and always prioritize the user's safety and health.
If asked to create a workout or diet plan, you'll need to gather information like fitness level, goals, and preferences.
"""

    def load_saved_plans(self):
        """Load saved workout and diet plans from the database."""
        if self.user_id <= 0:
            return

        # Load workout plans
        workout_plans = self.db_manager.get_workout_plans(self.user_id)
        if workout_plans:
            self.context["saved_workout_plans"] = workout_plans
            logger.info(
                f"Loaded {len(workout_plans)} saved workout plans for user {self.username}"
            )

        # Load diet plans
        diet_plans = self.db_manager.get_diet_plans(self.user_id)
        if diet_plans:
            self.context["saved_diet_plans"] = diet_plans
            logger.info(
                f"Loaded {len(diet_plans)} saved diet plans for user {self.username}"
            )

    def process_message(self, user_input):
        """Process a user message and generate a response"""
        logger.info(f"Processing user message: {user_input}")

        # Add user message to chat history
        self.chat_history.append({"role": "user", "content": user_input})

        # Check for commands
        if user_input.lower().startswith("create workout plan"):
            return self.handle_workout_creation(user_input)
        elif user_input.lower().startswith("create diet plan"):
            return self.handle_diet_creation(user_input)
        elif user_input.lower().startswith("schedule workout"):
            return self.handle_workout_scheduling(user_input)
        elif user_input.lower().startswith(
            "export calendar"
        ) or user_input.lower().startswith("create calendar"):
            return self.handle_calendar_export(user_input)
        elif user_input.lower().startswith("view profile"):
            return self.view_profile()
        elif user_input.lower().startswith("update profile"):
            return self.handle_profile_update(user_input)
        elif user_input.lower().startswith("save workout"):
            return self.handle_save_workout(user_input)
        elif user_input.lower().startswith("save diet"):
            return self.handle_save_diet(user_input)
        elif (
            user_input.lower().startswith("list workout plans")
            or user_input.lower() == "list workouts"
        ):
            return self.list_workout_plans()
        elif (
            user_input.lower().startswith("list diet plans")
            or user_input.lower() == "list diets"
        ):
            return self.list_diet_plans()
        elif user_input.lower().startswith("help"):
            return self.show_help()
        elif user_input.lower() == "exit" or user_input.lower() == "quit":
            # Close database connection before exiting
            self.db_manager.close()
            return "Goodbye! Have a great workout!"
        else:
            # General chat handled by LLM
            return self.general_chat(user_input)

    def general_chat(self, user_input):
        """Handle general chat with the LLM"""
        messages = [
            SystemMessage(content=self.system_prompt),
        ]

        # Add chat history for context (last 10 messages)
        for message in self.chat_history[-10:]:
            if message["role"] == "user":
                messages.append(HumanMessage(content=message["content"]))
            else:
                messages.append(SystemMessage(content=message["content"]))

        # Add current context information
        context_info = f"""
Current user profile:
{json.dumps(self.context['user_profile'], indent=2) if self.context['user_profile'] else 'No profile information yet'}

Current workout plan: {'Yes' if self.context['current_workout_plan'] else 'None'}
Current diet plan: {'Yes' if self.context['current_diet_plan'] else 'None'}
Calendar files: {', '.join(self.context['calendar_files']) if self.context['calendar_files'] else 'None'}
Saved workout plans: {len(self.context['saved_workout_plans'])}
Saved diet plans: {len(self.context['saved_diet_plans'])}
        """

        # Add current message
        messages.append(
            HumanMessage(content=user_input + "\n\nContext: " + context_info)
        )

        with get_openai_callback() as cb:
            response = self.llm.invoke(messages)
            logger.info(f"Generated response using {cb.total_tokens} tokens")

        # Add response to chat history
        self.chat_history.append({"role": "assistant", "content": response.content})
        return response.content

    def handle_workout_creation(self, user_input):
        """Handle workout plan creation"""
        logger.info("Handling workout creation request")

        # Extract parameters from user input
        params = {}
        if "days:" in user_input:
            try:
                days_part = user_input.split("days:")[1].split()[0]
                params["days"] = int(days_part)
            except (ValueError, IndexError):
                params["days"] = 4  # Default
        else:
            params["days"] = 4  # Default

        if "level:" in user_input.lower():
            try:
                level_part = user_input.lower().split("level:")[1].strip()
                level = level_part.split()[0]
                params["fitness_level"] = level
            except (ValueError, IndexError):
                params["fitness_level"] = "intermediate"  # Default
        else:
            params["fitness_level"] = "intermediate"  # Default

        # Create workout plan using the fitness agent
        workout_plan = self.fitness_agent.create_workout_plan(
            days=params["days"], fitness_level=params["fitness_level"]
        )

        # Save to context
        self.context["current_workout_plan"] = workout_plan

        # Format the response
        response = f"I've created a {params['days']}-day workout plan for {params['fitness_level']} fitness level:\n\n"

        for plan in workout_plan:
            response += f"📅 {plan.day}:\n"
            response += f"⏱️ Duration: {plan.duration}\n"
            response += f"💪 Intensity: {plan.intensity}\n"
            response += "Exercises:\n"
            for exercise in plan.exercises:
                response += f"- {exercise['name']}: {exercise['sets']} sets x {exercise['reps']} reps\n"
            response += "\n"

        response += "You can ask me to schedule these workouts, save the plan, export to a calendar file, or modify the plan if needed."

        # Add response to chat history
        self.chat_history.append({"role": "assistant", "content": response})
        return response

    def handle_diet_creation(self, user_input):
        """Handle diet plan creation"""
        logger.info("Handling diet creation request")

        # Extract parameters from user input
        params = {}
        if "calories:" in user_input:
            try:
                calories_part = user_input.split("calories:")[1].split()[0]
                params["daily_calories"] = int(calories_part)
            except (ValueError, IndexError):
                params["daily_calories"] = 2200  # Default
        else:
            params["daily_calories"] = 2200  # Default

        # Create diet plan using the fitness agent
        diet_plan = self.fitness_agent.create_diet_plan(
            daily_calories=params["daily_calories"]
        )

        # Save to context
        self.context["current_diet_plan"] = diet_plan

        # Format the response
        response = f"I've created a diet plan targeting {params['daily_calories']} calories per day:\n\n"

        for meal in diet_plan:
            response += f"🍽️ {meal.meal_type}:\n"
            response += f"Calories: {meal.calories}\n"
            response += f"Macros: Protein: {meal.macros['protein']}g, Carbs: {meal.macros['carbs']}g, Fat: {meal.macros['fat']}g\n"
            response += "Foods:\n"
            for food in meal.foods:
                response += f"- {food}\n"
            response += "\n"

        response += "You can ask me to save this diet plan or modify it if needed."

        # Add response to chat history
        self.chat_history.append({"role": "assistant", "content": response})
        return response

    def handle_workout_scheduling(self, user_input):
        """Handle workout scheduling"""
        logger.info("Handling workout scheduling request")

        if not self.context["current_workout_plan"]:
            response = "You don't have a workout plan yet. Let's create one first! Try saying 'Create workout plan'."
            self.chat_history.append({"role": "assistant", "content": response})
            return response

        # Schedule workouts
        start_date = datetime.now()

        # Format the response
        response = "I've scheduled your workout plan:\n\n"

        for i, workout in enumerate(self.context["current_workout_plan"]):
            workout_date = start_date + timedelta(days=i)
            self.fitness_agent.schedule_workout(workout, workout_date)
            response += f"📅 {workout_date.strftime('%Y-%m-%d')}: {workout.day}\n"

        response += "\nYour workouts have been scheduled! Remember to set reminders on your phone."
        response += "\n\nWould you like me to export this schedule to a calendar file you can import into Google Calendar, Apple Calendar, or Outlook? Just say 'export calendar'."

        # Add response to chat history
        self.chat_history.append({"role": "assistant", "content": response})
        return response

    def handle_calendar_export(self, user_input):
        """Handle calendar export request"""
        logger.info("Handling calendar export request")

        if not self.context["current_workout_plan"]:
            response = "You don't have a workout plan yet. Let's create one first! Try saying 'Create workout plan'."
            self.chat_history.append({"role": "assistant", "content": response})
            return response

        # Extract calendar name if provided
        calendar_name = "Workout Schedule"
        if "name:" in user_input.lower():
            try:
                name_part = user_input.lower().split("name:")[1].strip()
                # Extract until the next space or end of string
                calendar_name = name_part.split()[0] if " " in name_part else name_part
            except (ValueError, IndexError):
                pass

        # Extract start date if provided, otherwise use today
        start_date = datetime.now()
        if "date:" in user_input.lower():
            try:
                date_part = user_input.lower().split("date:")[1].strip()
                date_str = date_part.split()[0] if " " in date_part else date_part
                # Try to parse date in format YYYY-MM-DD
                start_date = datetime.strptime(date_str, "%Y-%m-%d")
            except (ValueError, IndexError):
                # If date parsing fails, use today
                pass

        # Create calendar file
        calendar_path = self.calendar_agent.create_workout_calendar(
            workout_plans=self.context["current_workout_plan"],
            start_date=start_date,
            calendar_name=calendar_name,
        )

        # Save calendar file to context
        self.context["calendar_files"].append(calendar_path)

        # Get the file location for display
        calendar_link = self.calendar_agent.get_calendar_link(calendar_path)

        # Format the response
        response = f"📆 I've created a calendar file with your workout schedule!\n\n"
        response += f"File location: {calendar_path}\n\n"
        response += "How to use this file:\n"
        response += "1. In Google Calendar: Click the '+' next to 'Other calendars' > 'Import' > Select this file\n"
        response += "2. In Apple Calendar: File > Import > Select this file\n"
        response += "3. In Outlook: File > Open & Export > Import/Export > Import an iCalendar (.ics) file\n\n"
        response += "This will add all your workouts to your calendar with detailed exercise instructions."

        # Add response to chat history
        self.chat_history.append({"role": "assistant", "content": response})
        return response

    def handle_profile_update(self, user_input):
        """Handle user profile updates"""
        logger.info("Handling profile update")

        # Simple parsing of key:value pairs
        update_text = user_input.replace("update profile", "").strip()
        updates = {}

        # Parse key:value pairs
        for pair in update_text.split(","):
            if ":" in pair:
                key, value = pair.split(":", 1)
                updates[key.strip()] = value.strip()

        # Update the profile in memory
        for key, value in updates.items():
            self.context["user_profile"][key] = value

        # Save profile to database if user exists
        if self.user_id > 0:
            save_success = self.db_manager.save_profile(
                self.user_id, self.context["user_profile"]
            )
            logger.info(
                f"Profile save to database: {'Successful' if save_success else 'Failed'}"
            )

        response = "I've updated your profile with the following information:\n\n"
        for key, value in updates.items():
            response += f"- {key}: {value}\n"

        response += (
            "\nI'll use this information to better tailor your fitness recommendations."
        )

        if self.user_id > 0:
            response += "\nYour profile has been saved to the database."

        # Add response to chat history
        self.chat_history.append({"role": "assistant", "content": response})
        return response

    def handle_save_workout(self, user_input):
        """Handle saving a workout plan to the database"""
        logger.info("Handling save workout request")

        if not self.context["current_workout_plan"]:
            response = "You don't have a workout plan to save. Let's create one first! Try saying 'Create workout plan'."
            self.chat_history.append({"role": "assistant", "content": response})
            return response

        if self.user_id <= 0:
            response = "I couldn't save your workout plan because there's no active user session. Please check your database connection."
            self.chat_history.append({"role": "assistant", "content": response})
            return response

        # Extract plan name if provided
        plan_name = f"{len(self.context['current_workout_plan'])}-Day Workout Plan"
        if "name:" in user_input.lower():
            try:
                name_part = user_input.lower().split("name:")[1].strip()
                plan_name = name_part
            except (ValueError, IndexError):
                pass

        # Convert workout plans to dictionaries for database storage
        plan_data = [plan.model_dump() for plan in self.context["current_workout_plan"]]

        # Save to database
        plan_id = self.db_manager.save_workout_plan(
            user_id=self.user_id, plan_name=plan_name, plan_data=plan_data
        )

        if plan_id > 0:
            # Reload saved plans
            self.load_saved_plans()

            response = (
                f"✅ I've saved your workout plan as '{plan_name}' to your profile.\n\n"
            )
            response += "You can access this plan in future sessions by logging in with the same username."
        else:
            response = "❌ I couldn't save your workout plan. There might be an issue with the database connection."

        # Add response to chat history
        self.chat_history.append({"role": "assistant", "content": response})
        return response

    def handle_save_diet(self, user_input):
        """Handle saving a diet plan to the database"""
        logger.info("Handling save diet request")

        if not self.context["current_diet_plan"]:
            response = "You don't have a diet plan to save. Let's create one first! Try saying 'Create diet plan'."
            self.chat_history.append({"role": "assistant", "content": response})
            return response

        if self.user_id <= 0:
            response = "I couldn't save your diet plan because there's no active user session. Please check your database connection."
            self.chat_history.append({"role": "assistant", "content": response})
            return response

        # Extract plan name if provided
        plan_name = f"Diet Plan ({datetime.now().strftime('%Y-%m-%d')})"
        if "name:" in user_input.lower():
            try:
                name_part = user_input.lower().split("name:")[1].strip()
                plan_name = name_part
            except (ValueError, IndexError):
                pass

        # Convert diet plans to dictionaries for database storage
        plan_data = [plan.model_dump() for plan in self.context["current_diet_plan"]]

        # Save to database
        plan_id = self.db_manager.save_diet_plan(
            user_id=self.user_id, plan_name=plan_name, plan_data=plan_data
        )

        if plan_id > 0:
            # Reload saved plans
            self.load_saved_plans()

            response = (
                f"✅ I've saved your diet plan as '{plan_name}' to your profile.\n\n"
            )
            response += "You can access this plan in future sessions by logging in with the same username."
        else:
            response = "❌ I couldn't save your diet plan. There might be an issue with the database connection."

        # Add response to chat history
        self.chat_history.append({"role": "assistant", "content": response})
        return response

    def list_workout_plans(self):
        """List all saved workout plans"""
        logger.info("Listing saved workout plans")

        if not self.context["saved_workout_plans"]:
            response = "You don't have any saved workout plans yet. Create a plan and then say 'save workout' to save it."
        else:
            response = "Here are your saved workout plans:\n\n"
            for i, plan in enumerate(self.context["saved_workout_plans"]):
                response += f"{i+1}. {plan['plan_name']} (Created: {plan['created_at'].strftime('%Y-%m-%d')})\n"

            response += (
                "\nYou can load or view these plans in a future version of the app."
            )

        # Add response to chat history
        self.chat_history.append({"role": "assistant", "content": response})
        return response

    def list_diet_plans(self):
        """List all saved diet plans"""
        logger.info("Listing saved diet plans")

        if not self.context["saved_diet_plans"]:
            response = "You don't have any saved diet plans yet. Create a plan and then say 'save diet' to save it."
        else:
            response = "Here are your saved diet plans:\n\n"
            for i, plan in enumerate(self.context["saved_diet_plans"]):
                response += f"{i+1}. {plan['plan_name']} (Created: {plan['created_at'].strftime('%Y-%m-%d')})\n"

            response += (
                "\nYou can load or view these plans in a future version of the app."
            )

        # Add response to chat history
        self.chat_history.append({"role": "assistant", "content": response})
        return response

    def view_profile(self):
        """Show the user profile"""
        logger.info("Showing user profile")

        if not self.context["user_profile"]:
            response = "You haven't set up your profile yet. Try 'update profile age: 30, weight: 70kg, goals: lose weight'."
        else:
            response = f"Here's your current profile (User: {self.username}):\n\n"
            for key, value in self.context["user_profile"].items():
                response += f"- {key}: {value}\n"

            response += "\nYou can update your profile anytime with 'update profile'."

        # Add response to chat history
        self.chat_history.append({"role": "assistant", "content": response})
        return response

    def show_help(self):
        """Show help information"""
        logger.info("Showing help information")

        response = """Here are the commands you can use:

1. 'create workout plan [days: 5] [level: beginner]' - Create a new workout plan
2. 'create diet plan [calories: 2000]' - Create a new diet plan
3. 'schedule workout' - Schedule your current workout plan
4. 'export calendar [name: MyWorkouts] [date: 2023-06-01]' - Export workout schedule to calendar file
5. 'save workout [name: My Workout]' - Save the current workout plan to your profile
6. 'save diet [name: My Diet]' - Save the current diet plan to your profile
7. 'list workout plans' - Show your saved workout plans
8. 'list diet plans' - Show your saved diet plans
9. 'view profile' - See your current profile information
10. 'update profile age: 30, weight: 70kg, goals: lose weight' - Update your profile
11. 'help' - Show this help information
12. 'exit' or 'quit' - Exit the chat

You can also just chat with me normally about fitness topics!
"""

        # Add response to chat history
        self.chat_history.append({"role": "assistant", "content": response})
        return response


def main():
    """Main function to run the interactive chat"""
    print("\n\n╔════════════════════════════════════════════════════════════╗")
    print("║                    FITNESS CHAT ASSISTANT                    ║")
    print("╚════════════════════════════════════════════════════════════╝\n")
    print("Hello! I'm your fitness assistant. I can help you create workout")
    print("plans, diet plans, and answer fitness questions.")

    # Get username for database persistence
    username = input("Please enter your username to begin: ")
    if not username.strip():
        username = "default_user"
        print(f"Using default username: {username}")
    else:
        print(f"Welcome, {username}!")

    print("Type 'help' to see what I can do or 'exit' to quit.\n")

    chat = InteractiveChat(username=username)

    while True:
        user_input = input("\n> ")
        if user_input.lower() in ["exit", "quit"]:
            print("\nGoodbye! Stay fit and healthy!")
            # Ensure database connection is closed
            chat.db_manager.close()
            break

        response = chat.process_message(user_input)
        print(f"\n{response}")


if __name__ == "__main__":
    main()
