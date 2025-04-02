import json
import logging
import os
from datetime import datetime, timedelta

import streamlit as st
from langchain.schema import HumanMessage, SystemMessage

from calendar_agent import CalendarAgent
from db_manager import DatabaseManager
from fitness_agent import DietPlan, FitnessAgent, WorkoutPlan

# Set up logging
if not os.path.exists("logs"):
    os.makedirs("logs")

logging.basicConfig(
    level=logging.ERROR,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        # Use utf-8 encoding for the file handler to handle emojis
        # logging.FileHandler("logs/streamlit_app.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("streamlit_app")


# Initialize session state for storing conversation history and user data
def init_session_state():
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "username" not in st.session_state:
        st.session_state.username = None
    if "user_id" not in st.session_state:
        st.session_state.user_id = None
    if "db_manager" not in st.session_state:
        st.session_state.db_manager = DatabaseManager()
    if "fitness_agent" not in st.session_state:
        st.session_state.fitness_agent = FitnessAgent()
    if "calendar_agent" not in st.session_state:
        st.session_state.calendar_agent = CalendarAgent()
    if "current_workout_plan" not in st.session_state:
        st.session_state.current_workout_plan = None
    if "current_diet_plan" not in st.session_state:
        st.session_state.current_diet_plan = None
    if "user_profile" not in st.session_state:
        st.session_state.user_profile = {}
    if "saved_workout_plans" not in st.session_state:
        st.session_state.saved_workout_plans = []
    if "saved_diet_plans" not in st.session_state:
        st.session_state.saved_diet_plans = []
    if "page" not in st.session_state:
        st.session_state.page = "login"


# Add a message to the chat history
def add_message(role, content):
    st.session_state.chat_history.append({"role": role, "content": content})


# Load user data from database
def load_user_data(username):
    db = st.session_state.db_manager
    user_id, created = db.get_or_create_user(username)

    if user_id <= 0:
        return False

    st.session_state.user_id = user_id
    st.session_state.username = username

    # Load profile
    profile = db.get_profile(user_id)
    if profile:
        st.session_state.user_profile = profile

    # Load workout plans
    workout_plans = db.get_workout_plans(user_id)
    if workout_plans:
        st.session_state.saved_workout_plans = workout_plans

    # Load diet plans
    diet_plans = db.get_diet_plans(user_id)
    if diet_plans:
        st.session_state.saved_diet_plans = diet_plans

    return True


# Create a new workout plan
def create_workout_plan(days, fitness_level):
    try:
        workout_plan = st.session_state.fitness_agent.create_workout_plan(
            days=days, fitness_level=fitness_level
        )
        st.session_state.current_workout_plan = workout_plan
        return True, workout_plan
    except Exception as e:
        logger.error(f"Error creating workout plan: {e}")
        return False, str(e)


# Create a new diet plan
def create_diet_plan(calories):
    try:
        diet_plan = st.session_state.fitness_agent.create_diet_plan(
            daily_calories=calories
        )
        st.session_state.current_diet_plan = diet_plan
        return True, diet_plan
    except Exception as e:
        logger.error(f"Error creating diet plan: {e}")
        return False, str(e)


# Save workout plan to database
def save_workout_plan(plan_name):
    if not st.session_state.current_workout_plan:
        return False, "No workout plan to save"

    try:
        plans = st.session_state.current_workout_plan
        if not isinstance(plans, list):
            plans = [plans]

        plan_data = [plan.model_dump() for plan in plans]

        plan_id = st.session_state.db_manager.save_workout_plan(
            user_id=st.session_state.user_id, plan_name=plan_name, plan_data=plan_data
        )

        if plan_id > 0:
            # Reload workout plans
            workout_plans = st.session_state.db_manager.get_workout_plans(
                st.session_state.user_id
            )
            if workout_plans:
                st.session_state.saved_workout_plans = workout_plans
            return True, f"Workout plan '{plan_name}' saved successfully"
        else:
            return False, "Failed to save workout plan"
    except Exception as e:
        logger.error(f"Error saving workout plan: {e}")
        return False, str(e)


# Save diet plan to database
def save_diet_plan(plan_name):
    if not st.session_state.current_diet_plan:
        return False, "No diet plan to save"

    try:
        plans = st.session_state.current_diet_plan
        if not isinstance(plans, list):
            plans = [plans]

        plan_data = [plan.model_dump() for plan in plans]

        plan_id = st.session_state.db_manager.save_diet_plan(
            user_id=st.session_state.user_id, plan_name=plan_name, plan_data=plan_data
        )

        if plan_id > 0:
            # Reload diet plans
            diet_plans = st.session_state.db_manager.get_diet_plans(
                st.session_state.user_id
            )
            if diet_plans:
                st.session_state.saved_diet_plans = diet_plans
            return True, f"Diet plan '{plan_name}' saved successfully"
        else:
            return False, "Failed to save diet plan"
    except Exception as e:
        logger.error(f"Error saving diet plan: {e}")
        return False, str(e)


# Load workout plan from database
def load_workout_plan(plan_index):
    if not st.session_state.saved_workout_plans:
        return False, "No saved workout plans"

    try:
        selected_plan = st.session_state.saved_workout_plans[plan_index]
        plan_data = selected_plan["plan_data"]

        # Convert the stored JSON plan data back into WorkoutPlan objects
        workout_plans = []
        for day_plan in plan_data:
            workout_plans.append(WorkoutPlan(**day_plan))

        # Set as current workout plan
        st.session_state.current_workout_plan = workout_plans
        return True, f"Loaded workout plan: {selected_plan['plan_name']}"
    except Exception as e:
        logger.error(f"Error loading workout plan: {e}")
        return False, str(e)


# Load diet plan from database
def load_diet_plan(plan_index):
    if not st.session_state.saved_diet_plans:
        return False, "No saved diet plans"

    try:
        selected_plan = st.session_state.saved_diet_plans[plan_index]
        plan_data = selected_plan["plan_data"]

        # Convert the stored JSON plan data back into DietPlan objects
        diet_plans = []
        for meal in plan_data:
            diet_plans.append(DietPlan(**meal))

        # Set as current diet plan
        st.session_state.current_diet_plan = diet_plans
        return True, f"Loaded diet plan: {selected_plan['plan_name']}"
    except Exception as e:
        logger.error(f"Error loading diet plan: {e}")
        return False, str(e)


# Export workout plan to calendar
def export_to_calendar(calendar_name, start_date):
    if not st.session_state.current_workout_plan:
        return False, "No workout plan to export"

    try:
        calendar_path = st.session_state.calendar_agent.create_workout_calendar(
            workout_plans=st.session_state.current_workout_plan,
            start_date=start_date,
            calendar_name=calendar_name,
        )
        return True, calendar_path
    except Exception as e:
        logger.error(f"Error exporting calendar: {e}")
        return False, str(e)


# Update user profile
def update_profile(profile_data):
    try:
        # Update profile in session state
        for key, value in profile_data.items():
            st.session_state.user_profile[key] = value

        # Save to database
        success = st.session_state.db_manager.save_profile(
            st.session_state.user_id, st.session_state.user_profile
        )

        return success, (
            "Profile updated successfully" if success else "Failed to update profile"
        )
    except Exception as e:
        logger.error(f"Error updating profile: {e}")
        return False, str(e)


# Format workout plan for display
def format_workout_plan(workout_plan):
    result = ""
    for plan in workout_plan:
        result += f"📅 {plan.day}:\n"
        result += f"⏱️ Duration: {plan.duration}\n"
        result += f"💪 Intensity: {plan.intensity}\n"
        result += "Exercises:\n"
        for exercise in plan.exercises:
            exercise_info = f"- {exercise['name']}: {exercise['sets']} sets x {exercise['reps']} reps"
            if "rest_period" in exercise:
                exercise_info += f" (Rest: {exercise['rest_period']})"
            result += exercise_info + "\n"
        result += "\n"
    return result


# Format diet plan for display
def format_diet_plan(diet_plan):
    result = ""
    for meal in diet_plan:
        result += f"🍽️ {meal.meal_type}:\n"
        result += f"Calories: {meal.calories}\n"
        result += f"Macros: Protein: {meal.macros['protein']}g, Carbs: {meal.macros['carbs']}g, Fat: {meal.macros['fat']}g\n"
        result += "Foods:\n"
        for food in meal.foods:
            result += f"- {food}\n"
        result += "\n"
    return result


# Login page
def login_page():
    st.title("Fitness Assistant")
    st.subheader("Login")

    with st.form("login_form"):
        username = st.text_input("Username")
        submit = st.form_submit_button("Login")

        if submit:
            if username.strip():
                success = load_user_data(username)
                if success:
                    st.session_state.page = "main"
                    st.success(f"Welcome, {username}!")
                else:
                    st.error("Failed to connect to database. Please try again.")
            else:
                st.error("Please enter a username")


# Main page with sidebar navigation
def main_page():
    st.sidebar.title("Navigation")

    page = st.sidebar.radio(
        "Go to",
        [
            "Dashboard",
            "Create Workout",
            "Create Diet",
            "Saved Plans",
            "Calendar",
            "Profile",
            "Chat Assistant",
        ],
    )

    # Show username in sidebar
    st.sidebar.write(f"Logged in as: {st.session_state.username}")

    # Logout button
    if st.sidebar.button("Logout"):
        # Close database connection
        st.session_state.db_manager.close()
        # Reset session state
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        # Initialize session state
        init_session_state()
        st.session_state.page = "login"

    if page == "Dashboard":
        dashboard_page()
    elif page == "Create Workout":
        create_workout_page()
    elif page == "Create Diet":
        create_diet_page()
    elif page == "Saved Plans":
        saved_plans_page()
    elif page == "Calendar":
        calendar_page()
    elif page == "Profile":
        profile_page()
    elif page == "Chat Assistant":
        chat_assistant_page()


# Dashboard page
def dashboard_page():
    st.title("Fitness Dashboard")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Profile Summary")
        if st.session_state.user_profile:
            for key, value in st.session_state.user_profile.items():
                st.write(f"**{key}**: {value}")
        else:
            st.write(
                "No profile information yet. Go to the Profile page to set up your profile."
            )

    with col2:
        st.subheader("Saved Plans")
        st.write(f"Workout Plans: {len(st.session_state.saved_workout_plans)}")
        st.write(f"Diet Plans: {len(st.session_state.saved_diet_plans)}")

    st.subheader("Current Workout Plan")
    if st.session_state.current_workout_plan:
        st.write(format_workout_plan(st.session_state.current_workout_plan))

        col1, _ = st.columns(2)
        with col1:
            plan_name = st.text_input(
                "Plan Name",
                value=f"{len(st.session_state.current_workout_plan)}-Day Workout Plan",
                key="save_workout_name",
            )
            if st.button("Save Workout Plan"):
                success, message = save_workout_plan(plan_name)
                if success:
                    st.success(message)
                else:
                    st.error(message)
    else:
        st.write(
            "No current workout plan. Go to the Create Workout page to create one."
        )

    st.subheader("Current Diet Plan")
    if st.session_state.current_diet_plan:
        st.write(format_diet_plan(st.session_state.current_diet_plan))

        plan_name = st.text_input(
            "Plan Name",
            value=f"Diet Plan ({datetime.now().strftime('%Y-%m-%d')})",
            key="save_diet_name",
        )
        if st.button("Save Diet Plan"):
            success, message = save_diet_plan(plan_name)
            if success:
                st.success(message)
            else:
                st.error(message)
    else:
        st.write("No current diet plan. Go to the Create Diet page to create one.")


# Create workout page
def create_workout_page():
    st.title("Create Workout Plan")

    # Define plan_name variable at the beginning to avoid reference before assignment
    plan_name = f"Workout Plan ({datetime.now().strftime('%Y-%m-%d')})"

    # Create a form for workout parameters
    with st.form("workout_form"):
        # Use columns for inline form fields
        col1, col2 = st.columns(2)

        with col1:
            days = st.number_input("Number of Days", min_value=1, max_value=7, value=4)
        with col2:
            fitness_level = st.selectbox(
                "Fitness Level",
                ["beginner", "intermediate", "advanced"],
                index=1,
            )

        submitted = st.form_submit_button("Generate Workout Plan")

        if submitted:
            with st.spinner("Generating workout plan..."):
                try:
                    success, workout_plan = create_workout_plan(days, fitness_level)
                    if success:
                        # Display the workout plan
                        st.subheader("Generated Workout Plan")
                        for plan in workout_plan:
                            with st.expander(f"📅 {plan.day}"):
                                st.write(f"⏱️ Duration: {plan.duration}")
                                st.write(f"💪 Intensity: {plan.intensity}")
                                st.write("Exercises:")
                                for exercise in plan.exercises:
                                    st.write(
                                        f"- {exercise['name']}: {exercise['sets']} sets x {exercise['reps']} reps"
                                    )

                        # Update plan_name with the number of days
                        plan_name = f"{days}-Day Workout Plan"
                        # Add save functionality outside the form
                        plan_name = st.text_input(
                            "Plan Name",
                            value=plan_name,
                            key="new_workout_name",
                        )
                    else:
                        st.error(f"Error: {workout_plan}")
                except Exception as e:
                    st.error(f"Error creating workout plan: {str(e)}")

    # Save button outside the form
    if st.session_state.get("current_workout_plan"):
        if st.button("Save Workout Plan"):
            save_success, message = save_workout_plan(plan_name)
            if save_success:
                st.success(message)
            else:
                st.error(message)


# Create diet page
def create_diet_page():
    st.title("Create Diet Plan")

    # Define plan_name variable outside the form to avoid reference issues
    plan_name = f"Diet Plan ({datetime.now().strftime('%Y-%m-%d')})"

    with st.form("diet_form"):
        # Use columns for better layout even with single field
        col1, col2 = st.columns([1, 1])
        with col1:
            calories = st.number_input(
                "Daily Calories", min_value=500, max_value=5000, value=2200
            )

        submit = st.form_submit_button("Create Diet Plan")

        if submit:
            with st.spinner("Creating diet plan..."):
                success, result = create_diet_plan(calories)
                if success:
                    st.success(
                        f"Created a diet plan targeting {calories} calories per day"
                    )
                    st.write(format_diet_plan(result))

                    # Update plan name with calories info
                    plan_name = f"Diet Plan - {calories} calories"

                    # Move text input outside the form but display it when plan is created
                    plan_name = st.text_input(
                        "Plan Name",
                        value=plan_name,
                        key="new_diet_name",
                    )
                else:
                    st.error(f"Error creating diet plan: {result}")

    # Save button outside the form
    if st.session_state.get("current_diet_plan"):
        if st.button("Save Diet Plan"):
            save_success, message = save_diet_plan(plan_name)
            if save_success:
                st.success(message)
            else:
                st.error(message)


# Saved plans page
def saved_plans_page():
    st.title("Saved Plans")

    tab1, tab2 = st.tabs(["Workout Plans", "Diet Plans"])

    with tab1:
        st.subheader("Saved Workout Plans")
        if not st.session_state.saved_workout_plans:
            st.write("You don't have any saved workout plans yet.")
        else:
            for i, plan in enumerate(st.session_state.saved_workout_plans):
                with st.expander(
                    f"{i+1}. {plan['plan_name']} (Created: {plan['created_at'].strftime('%Y-%m-%d')})"
                ):
                    st.write("**Plan Details:**")
                    for day_plan in plan["plan_data"]:
                        st.write(f"📅 {day_plan['day']}:")
                        st.write(f"⏱️ Duration: {day_plan['duration']}")
                        st.write(f"💪 Intensity: {day_plan['intensity']}")
                        st.write("Exercises:")
                        for exercise in day_plan["exercises"]:
                            exercise_info = f"- {exercise['name']}: {exercise['sets']} sets x {exercise['reps']} reps"
                            if "rest_period" in exercise:
                                exercise_info += f" (Rest: {exercise['rest_period']})"
                            st.write(exercise_info)

                    if st.button(f"Load Plan #{i+1}", key=f"load_workout_{i}"):
                        success, message = load_workout_plan(i)
                        if success:
                            st.success(message)
                        else:
                            st.error(message)

    with tab2:
        st.subheader("Saved Diet Plans")
        if not st.session_state.saved_diet_plans:
            st.write("You don't have any saved diet plans yet.")
        else:
            for i, plan in enumerate(st.session_state.saved_diet_plans):
                with st.expander(
                    f"{i+1}. {plan['plan_name']} (Created: {plan['created_at'].strftime('%Y-%m-%d')})"
                ):
                    st.write("**Plan Details:**")
                    for meal in plan["plan_data"]:
                        st.write(f"🍽️ {meal['meal_type']}:")
                        st.write(f"Calories: {meal['calories']}")
                        macros = meal["macros"]
                        st.write(
                            f"Macros: Protein: {macros['protein']}g, Carbs: {macros['carbs']}g, Fat: {macros['fat']}g"
                        )
                        st.write("Foods:")
                        for food in meal["foods"]:
                            st.write(f"- {food}")

                    if st.button(f"Load Plan #{i+1}", key=f"load_diet_{i}"):
                        success, message = load_diet_plan(i)
                        if success:
                            st.success(message)
                        else:
                            st.error(message)


# Calendar page
def calendar_page():
    st.title("Export Workout to Calendar")

    if not st.session_state.current_workout_plan:
        st.error(
            "No workout plan to export. Please create or load a workout plan first."
        )
        return

    st.write("Current workout plan:")
    st.write(format_workout_plan(st.session_state.current_workout_plan))

    # Store result in session state to access it outside the form
    if "calendar_export_result" not in st.session_state:
        st.session_state.calendar_export_result = None
    if "calendar_file_name" not in st.session_state:
        st.session_state.calendar_file_name = None

    with st.form("calendar_form"):
        # Use columns for inline form fields
        col1, col2 = st.columns(2)
        with col1:
            calendar_name = st.text_input("Calendar Name", value="Workout Schedule")
        with col2:
            start_date = st.date_input("Start Date", value=datetime.now())

        submit = st.form_submit_button("Export to Calendar")

        if submit:
            with st.spinner("Exporting to calendar..."):
                success, result = export_to_calendar(calendar_name, start_date)
                if success:
                    st.session_state.calendar_export_result = result
                    st.session_state.calendar_file_name = calendar_name
                    st.success(f"Calendar exported successfully!")
                    st.write(f"File location: {result}")
                else:
                    st.error(f"Error exporting calendar: {result}")

    # Auto-download section (outside the form)
    if st.session_state.calendar_export_result:
        try:
            with open(st.session_state.calendar_export_result, "r") as file:
                ics_content = file.read()
                file_name = (
                    f"{st.session_state.calendar_file_name.replace(' ', '_')}.ics"
                )

                # Create automatic download
                st.markdown(f"### Your calendar file is ready! 📅")

                # Download button outside the form
                st.download_button(
                    label="Download Calendar File",
                    data=ics_content,
                    file_name=file_name,
                    mime="text/calendar",
                    key="auto_download",
                )

                st.write("Import instructions:")
                st.write(
                    "1. In Google Calendar: Click the '+' next to 'Other calendars' > 'Import' > Select this file"
                )
                st.write("2. In Apple Calendar: File > Import > Select this file")
                st.write(
                    "3. In Outlook: File > Open & Export > Import/Export > Import an iCalendar (.ics) file"
                )
        except Exception as e:
            st.error(f"Error preparing calendar file for download: {e}")


# Profile page
def profile_page():
    st.title("User Profile")

    # Display current profile
    st.subheader("Current Profile")
    if st.session_state.user_profile:
        # Display profile info in columns for better layout
        cols = st.columns(2)
        for i, (key, value) in enumerate(st.session_state.user_profile.items()):
            cols[i % 2].write(f"**{key}**: {value}")
    else:
        st.write("No profile information yet.")

    # Update profile form
    st.subheader("Update Profile")
    with st.form("profile_form"):
        # Create two columns for the basic info
        col1, col2 = st.columns(2)

        with col1:
            age = st.number_input(
                "Age",
                min_value=1,
                max_value=120,
                value=(
                    int(st.session_state.user_profile.get("age", 30))
                    if "age" in st.session_state.user_profile
                    else 30
                ),
            )
            weight = st.text_input(
                "Weight (e.g., 70kg)",
                value=st.session_state.user_profile.get("weight", ""),
            )
            goals = st.text_input(
                "Fitness Goals",
                value=st.session_state.user_profile.get("goals", ""),
            )

        with col2:
            height = st.text_input(
                "Height (e.g., 175cm)",
                value=st.session_state.user_profile.get("height", ""),
            )
            fitness_level = st.selectbox(
                "Fitness Level",
                ["beginner", "intermediate", "advanced"],
                index=(
                    ["beginner", "intermediate", "advanced"].index(
                        st.session_state.user_profile.get(
                            "fitness_level", "intermediate"
                        )
                    )
                    if "fitness_level" in st.session_state.user_profile
                    else 1
                ),
            )

        # Allow additional custom fields with inline layout
        st.write("Add any additional information:")

        # Custom field 1 - inline
        cf1_col1, cf1_col2 = st.columns(2)
        with cf1_col1:
            key1 = st.text_input("Custom Field 1 Name", key="custom_key1")
        with cf1_col2:
            value1 = st.text_input("Custom Field 1 Value", key="custom_value1")

        # Custom field 2 - inline
        cf2_col1, cf2_col2 = st.columns(2)
        with cf2_col1:
            key2 = st.text_input("Custom Field 2 Name", key="custom_key2")
        with cf2_col2:
            value2 = st.text_input("Custom Field 2 Value", key="custom_value2")

        submit = st.form_submit_button("Update Profile")

        if submit:
            # Collect profile data
            profile_data = {
                "age": age,
                "weight": weight,
                "height": height,
                "goals": goals,
                "fitness_level": fitness_level,
            }

            # Add custom fields if provided
            if key1 and value1:
                profile_data[key1] = value1
            if key2 and value2:
                profile_data[key2] = value2

            # Update profile
            success, message = update_profile(profile_data)
            if success:
                st.success(message)
            else:
                st.error(message)


# Chat assistant page
def chat_assistant_page():
    st.title("Chat with Fitness Assistant")

    # Initialize chat history in session state if it doesn't exist
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []

        # Add welcome message
        st.session_state.chat_messages.append(
            {
                "role": "assistant",
                "content": """👋 Hello! I'm your fitness assistant. I can help you with:
                
1. Creating workout plans
2. Creating diet plans
3. Managing your saved plans
4. Viewing and updating your profile
5. Exporting workouts to calendar
                
Just type your request naturally or try commands like 'create workout plan days: 5 level: intermediate' or 'create diet plan calories: 2000'.""",
            }
        )

    # Create a container for scrollable chat history
    chat_container = st.container()

    # Display chat messages in the container
    with chat_container:
        for message in st.session_state.chat_messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    # Chat input
    if prompt := st.chat_input("Type your message here..."):
        # Add user message to chat history
        st.session_state.chat_messages.append({"role": "user", "content": prompt})

        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)

        # Process the message and generate response
        with st.spinner("Thinking..."):
            response = process_chat_message(prompt)

        # Add assistant response to chat history
        st.session_state.chat_messages.append(
            {"role": "assistant", "content": response}
        )

        # Display assistant response
        with st.chat_message("assistant"):
            st.markdown(response)


# Process chat messages with direct command execution
def process_chat_message(message):
    try:
        # Check for command-like messages first
        message_lower = message.lower()

        # Add context awareness - check if we need to refer to chat history
        chat_context = get_recent_chat_context()

        # Create workout plan command
        if message_lower.startswith("create workout") or message_lower.startswith(
            "create workout plan"
        ):
            # Extract parameters
            days = 4  # Default
            level = "intermediate"  # Default

            if "days:" in message:
                try:
                    days_part = message.split("days:")[1].split()[0]
                    days = int(days_part)
                except (ValueError, IndexError):
                    pass

            if "level:" in message.lower():
                try:
                    level_part = message.lower().split("level:")[1].strip()
                    level_value = level_part.split()[0]
                    if level_value in ["beginner", "intermediate", "advanced"]:
                        level = level_value
                except (ValueError, IndexError):
                    pass

            # Create the workout plan directly
            with st.spinner("Creating workout plan..."):
                success, result = create_workout_plan(days, level)

            if success:
                plan_details = format_workout_plan(result)
                return f"✅ I've created a {days}-day workout plan for {level} fitness level:\n\n{plan_details}\n\nYou can now:\n- Say 'save workout name: My Plan' to save it\n- Say 'schedule workout' to see scheduling options\n- Say 'export calendar' to export to a calendar file"
            else:
                return f"❌ I couldn't create the workout plan: {result}"

        # Create diet plan command
        elif message_lower.startswith("create diet") or message_lower.startswith(
            "create diet plan"
        ):
            # Extract parameters
            calories = 2200  # Default

            if "calories:" in message:
                try:
                    cal_part = message.split("calories:")[1].split()[0]
                    calories = int(cal_part)
                except (ValueError, IndexError):
                    pass

            # Create the diet plan directly
            with st.spinner("Creating diet plan..."):
                success, result = create_diet_plan(calories)

            if success:
                diet_details = format_diet_plan(result)
                return f"✅ I've created a diet plan targeting {calories} calories per day:\n\n{diet_details}\n\nYou can say 'save diet name: My Diet' to save this plan."
            else:
                return f"❌ I couldn't create the diet plan: {result}"

        # Save workout plan
        elif message_lower.startswith("save workout"):
            if not st.session_state.get("current_workout_plan"):
                return "You don't have a workout plan to save. Let's create one first! Try saying 'Create workout plan'."

            # Extract plan name
            plan_name = f"{len(st.session_state.current_workout_plan)}-Day Workout Plan"
            if "name:" in message.lower():
                try:
                    name_part = message.lower().split("name:")[1].strip()
                    plan_name = name_part
                except (ValueError, IndexError):
                    pass

            # Save the plan
            success, message_result = save_workout_plan(plan_name)
            if success:
                return f"✅ {message_result}"
            else:
                return f"❌ {message_result}"

        # Save diet plan
        elif message_lower.startswith("save diet"):
            if not st.session_state.get("current_diet_plan"):
                return "You don't have a diet plan to save. Let's create one first! Try saying 'Create diet plan'."

            # Extract plan name
            plan_name = f"Diet Plan ({datetime.now().strftime('%Y-%m-%d')})"
            if "name:" in message.lower():
                try:
                    name_part = message.lower().split("name:")[1].strip()
                    plan_name = name_part
                except (ValueError, IndexError):
                    pass

            # Save the plan
            success, message_result = save_diet_plan(plan_name)
            if success:
                return f"✅ {message_result}"
            else:
                return f"❌ {message_result}"

        # List workout plans
        elif (
            message_lower.startswith("list workout") or message_lower == "list workouts"
        ):
            if not st.session_state.saved_workout_plans:
                return "You don't have any saved workout plans yet. Create a plan and then say 'save workout' to save it."

            response = "Here are your saved workout plans:\n\n"
            for i, plan in enumerate(st.session_state.saved_workout_plans):
                response += f"{i+1}. {plan['plan_name']} (Created: {plan['created_at'].strftime('%Y-%m-%d')})\n"

            response += "\nTo load a specific plan, say 'load workout plan: 1' (using the number from the list)."
            return response

        # List diet plans
        elif message_lower.startswith("list diet") or message_lower == "list diets":
            if not st.session_state.saved_diet_plans:
                return "You don't have any saved diet plans yet. Create a plan and then say 'save diet' to save it."

            response = "Here are your saved diet plans:\n\n"
            for i, plan in enumerate(st.session_state.saved_diet_plans):
                response += f"{i+1}. {plan['plan_name']} (Created: {plan['created_at'].strftime('%Y-%m-%d')})\n"

            response += "\nTo load a specific plan, say 'load diet plan: 1' (using the number from the list)."
            return response

        # Load workout plan
        elif message_lower.startswith("load workout"):
            if not st.session_state.saved_workout_plans:
                return "You don't have any saved workout plans yet. Create a plan and then say 'save workout' to save it."

            # Extract plan number
            try:
                if ":" in message:
                    number_part = message.split(":")[1].strip()
                else:
                    number_part = message.split("plan")[1].strip()

                plan_index = int(number_part) - 1  # Convert to 0-based index

                success, message_result = load_workout_plan(plan_index)
                if success:
                    # Get the details to show the user
                    plan_details = format_workout_plan(
                        st.session_state.current_workout_plan
                    )
                    return f"✅ {message_result}\n\n{plan_details}"
                else:
                    return f"❌ {message_result}"
            except (ValueError, IndexError):
                return "I couldn't understand which plan to load. Please say 'load workout plan: 1' (using the number from the list)."

        # Load diet plan
        elif message_lower.startswith("load diet"):
            if not st.session_state.saved_diet_plans:
                return "You don't have any saved diet plans yet. Create a plan and then say 'save diet' to save it."

            # Extract plan number
            try:
                if ":" in message:
                    number_part = message.split(":")[1].strip()
                else:
                    number_part = message.split("plan")[1].strip()

                plan_index = int(number_part) - 1  # Convert to 0-based index

                success, message_result = load_diet_plan(plan_index)
                if success:
                    # Get the details to show the user
                    plan_details = format_diet_plan(st.session_state.current_diet_plan)
                    return f"✅ {message_result}\n\n{plan_details}"
                else:
                    return f"❌ {message_result}"
            except (ValueError, IndexError):
                return "I couldn't understand which plan to load. Please say 'load diet plan: 1' (using the number from the list)."

        # View profile
        elif message_lower.startswith("view profile") or message_lower == "profile":
            if not st.session_state.user_profile:
                return "You haven't set up your profile yet. Try 'update profile age: 30, weight: 70kg, goals: lose weight'"

            response = (
                f"Here's your current profile (User: {st.session_state.username}):\n\n"
            )
            for key, value in st.session_state.user_profile.items():
                response += f"- **{key}**: {value}\n"

            return response

        # Update profile
        elif message_lower.startswith("update profile"):
            # Simple parsing of key:value pairs
            update_text = message.replace("update profile", "").strip()
            updates = {}

            # Parse key:value pairs
            for pair in update_text.split(","):
                if ":" in pair:
                    key, value = pair.split(":", 1)
                    updates[key.strip()] = value.strip()

            if not updates:
                return "Please specify what to update, for example: update profile age: 30, weight: 70kg, goals: lose weight"

            # Update profile
            success, message_result = update_profile(updates)
            if success:
                response = (
                    "I've updated your profile with the following information:\n\n"
                )
                for key, value in updates.items():
                    response += f"- **{key}**: {value}\n"
                return response
            else:
                return f"❌ {message_result}"

        # Export to calendar
        elif message_lower.startswith("export calendar") or message_lower.startswith(
            "create calendar"
        ):
            if not st.session_state.current_workout_plan:
                return "You don't have a workout plan to export. Please create or load a workout plan first!"

            # Suggest going to the Calendar tab
            return "To export your workout plan to a calendar file, please go to the Calendar tab in the navigation menu. There you can set the calendar name and start date, and download the ICS file."

        # Schedule workout
        elif message_lower.startswith("schedule workout"):
            if not st.session_state.current_workout_plan:
                return "You don't have a workout plan yet. Let's create one first! Try saying 'Create workout plan'."

            # Create a schedule visualization
            start_date = datetime.now()
            response = "Here's a schedule for your workout plan:\n\n"

            for i, workout in enumerate(st.session_state.current_workout_plan):
                workout_date = start_date + timedelta(days=i)
                response += (
                    f"📅 **{workout_date.strftime('%A, %B %d')}**: {workout.day}\n"
                )
                response += f"⏱️ Duration: {workout.duration} | 💪 Intensity: {workout.intensity}\n\n"

            response += "To add this to your calendar, say 'export calendar' and I'll guide you."
            return response

        # Help command
        elif message_lower == "help":
            return """Here are the commands you can use:

1. **'create workout plan days: 5 level: beginner'** - Create a new workout plan
2. **'create diet plan calories: 2000'** - Create a new diet plan
3. **'schedule workout'** - Schedule your current workout plan
4. **'export calendar'** - Export workout schedule to calendar file
5. **'save workout name: My Workout'** - Save the current workout plan
6. **'save diet name: My Diet'** - Save the current diet plan
7. **'list workout plans'** - Show your saved workout plans
8. **'list diet plans'** - Show your saved diet plans
9. **'load workout plan: 1'** - Load a saved workout plan
10. **'load diet plan: 1'** - Load a saved diet plan
11. **'view profile'** - See your current profile information
12. **'update profile age: 30, weight: 70kg, goals: lose weight'** - Update your profile
13. **'help'** - Show this help information

You can also just chat with me normally about fitness topics!"""

        # Fallback for other questions - try to be helpful
        return generate_llm_response(message, chat_context)

    except Exception as e:
        logger.error(f"Error processing chat message: {e}")
        return "I'm sorry, I encountered an error processing your request. Please try again or type 'help' to see available commands."


# Generate a response using the LLM for general fitness queries
def generate_llm_response(message, chat_context):
    """Handle general chat with the LLM"""
    logger.debug("Generating LLM response for message: %s", message)

    try:
        # System prompt for the chat interface
        system_prompt = """You are a helpful fitness assistant. You can help users with:
1. Creating personalized workout plans
2. Creating diet plans
3. Scheduling workouts
4. Exporting workout plans to calendar (ICS) files
5. Answering fitness-related questions
6. Giving health and wellness advice

Be conversational, friendly, and always prioritize the user's safety and health.
DO NOT format your response as JSON. Return plain text only without any JSON structure or wrapping.
"""

        # Create messages list starting with system prompt
        messages = [
            SystemMessage(content=system_prompt),
        ]

        # Add chat history for context (last 10 messages)
        if (
            "chat_messages" in st.session_state
            and len(st.session_state.chat_messages) > 0
        ):
            for msg in st.session_state.chat_messages[-10:]:
                if msg["role"] == "user":
                    messages.append(HumanMessage(content=msg["content"]))
                else:
                    messages.append(SystemMessage(content=msg["content"]))

        # Add current context information
        context_info = f"""
Current user profile:
{json.dumps(st.session_state.get('user_profile', {}), indent=2) if 'user_profile' in st.session_state and st.session_state.user_profile else 'No profile information yet'}

Current workout plan: {'Yes' if 'current_workout_plan' in st.session_state and st.session_state.current_workout_plan else 'None'}
Current diet plan: {'Yes' if 'current_diet_plan' in st.session_state and st.session_state.current_diet_plan else 'None'}
"""

        # Add current message with context
        messages.append(HumanMessage(content=message + "\n\nContext: " + context_info))

        # Use callback to track token usage
        from langchain_community.callbacks import get_openai_callback

        with get_openai_callback() as cb:
            # Configure streaming to get the complete response
            llm = st.session_state.fitness_agent.llm

            # Get complete response through streaming
            try:
                # First try with streaming if supported
                full_response = ""
                for chunk in llm.stream(messages):
                    if hasattr(chunk, "content"):
                        full_response += chunk.content
                    else:
                        # Fall back if the chunk format is unexpected
                        logger.debug("Unexpected chunk format, using standard invoke")
                        full_response = llm.invoke(messages).content
                        break

                response_content = full_response
            except (AttributeError, NotImplementedError):
                # Fall back to regular invoke if streaming not supported
                logger.debug("Streaming not supported, using standard invoke")
                response_content = llm.invoke(messages).content

            logger.info("Generated response using %s tokens", cb.total_tokens)

            # Safe logging - avoid logging the full response due to potential Unicode issues
            logger.debug("Response received from LLM")

            answer = response_content

            # Ensure we're not returning an empty string
            if not answer or answer.isspace():
                return "I'm here to help with your fitness journey! Try asking about workout plans, diet advice, or specific exercises."

            # Check if response might be in JSON format and parse it if needed
            if answer.strip().startswith("{") and answer.strip().endswith("}"):
                try:
                    parsed_json = json.loads(answer)
                    if isinstance(parsed_json, dict) and "message" in parsed_json:
                        return parsed_json["message"]
                    elif isinstance(parsed_json, dict) and "text" in parsed_json:
                        return parsed_json["text"]
                except json.JSONDecodeError:
                    # Not valid JSON, continue with original content
                    pass

            return answer

    except Exception as e:
        logger.error("Error generating LLM response: %s", str(e))
        return "I'm here to help with your fitness journey! Try asking about workout plans, diet advice, or specific exercises."


# Get recent chat context to make responses more conversational
def get_recent_chat_context():
    if (
        "chat_messages" not in st.session_state
        or len(st.session_state.chat_messages) < 2
    ):
        return []

    # Return the last 3 messages for context
    return st.session_state.chat_messages[-3:]


# Main app
def main():
    # Initialize session state
    init_session_state()

    # Page routing
    if st.session_state.page == "login":
        login_page()
        # After login submission, check if page state changed and render the appropriate page
        if st.session_state.page == "main":
            main_page()
    elif st.session_state.page == "main":
        main_page()

    # Close database connection when app is done
    if hasattr(st, "on_script_finished"):
        st.on_script_finished(lambda: st.session_state.db_manager.close())


if __name__ == "__main__":
    main()
