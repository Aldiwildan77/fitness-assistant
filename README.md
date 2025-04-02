# Fitness Agent

A LangChain-based AI agent that helps with fitness planning, including workout routines, diet plans, and calendar scheduling. Features persistent user profiles and plan storage with PostgreSQL.

## Features

- Personalized workout plan generation
- Diet plan creation with macro tracking
- Google Calendar integration for workout scheduling
- Workout plan validation and refinement
- Context-aware fitness recommendations
- Calendar export to ICS files for any calendar application
- PostgreSQL database for persistent user profiles and saved plans
- Multi-user support with personalized settings

## Prerequisites

- Python 3.8+
- Ollama installed locally (https://ollama.ai)
- Google Calendar API credentials
- PostgreSQL database server

## Setup

1. Install Ollama:
   - Visit https://ollama.ai
   - Download and install Ollama for your platform
   - Pull the required model:
   ```bash
   ollama pull llama2
   ```

2. Install the required dependencies:
```bash
pip install -r requirements.txt
```

3. Set up Google Calendar API:
   - Go to the [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project
   - Enable the Google Calendar API
   - Create credentials (OAuth 2.0 Client ID)
   - Download the credentials and save them as `credentials.json` in the project root

4. Set up PostgreSQL:
   - Install PostgreSQL server
   - Create a database for the application
   - Update your `.env` file with the database connection details:
   ```
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=fitness_agent
   DB_USER=postgres
   DB_PASSWORD=your_password
   ```

5. Initialize the database:
   ```bash
   python init_db.py
   ```
   This script will create all necessary tables and set up a test user to verify your database connection.

6. Configure LangSmith (optional for tracing):
   - Sign up for LangSmith at https://smith.langchain.com
   - Get your API key
   - Add to your `.env` file:
   ```
   LANGCHAIN_TRACING_V2=true
   LANGCHAIN_ENDPOINT="https://api.smith.langchain.com"
   LANGCHAIN_API_KEY="your_langsmith_api_key"
   LANGCHAIN_PROJECT="fitness_agent"
   ```

## Usage

### Interactive Chat

The easiest way to use the agent is through the interactive chat interface:

```bash
python interactive_chat.py
```

This will start a chat interface where you can:
- Create workout plans with `create workout plan days: 5 level: intermediate`
- Create diet plans with `create diet plan calories: 2000`
- Schedule workouts with `schedule workout`
- Export workouts to calendar files with `export calendar name: MyWorkouts date: 2023-06-01`
- Save workout and diet plans to the database with `save workout name: My Plan` or `save diet name: My Diet`
- View and manage your user profile with `view profile` and `update profile age: 30, weight: 70kg, goals: lose weight`
- List your saved plans with `list workout plans` or `list diet plans`

### Programmatic Usage

1. Initialize the agent:
```python
from fitness_agent import FitnessAgent

# Initialize with default model (llama2)
agent = FitnessAgent()

# Or specify a different model
agent = FitnessAgent(model_name="mistral")  # or any other model you have pulled
```

2. Create a workout plan:
```python
workout_plan = agent.create_workout_plan(days=5, fitness_level="intermediate")
```

3. Create a diet plan:
```python
diet_plan = agent.create_diet_plan(daily_calories=2500)
```

4. Schedule workouts:
```python
from datetime import datetime, timedelta

start_date = datetime.now()
for i, workout in enumerate(workout_plan):
    agent.schedule_workout(workout, start_date + timedelta(days=i))
```

5. Export to calendar file:
```python
from calendar_agent import CalendarAgent

calendar_agent = CalendarAgent()
calendar_file = calendar_agent.create_workout_calendar(
    workout_plans=workout_plan,
    start_date=datetime.now(),
    calendar_name="My Workout Plan"
)
print(f"Calendar file created: {calendar_file}")
```

6. Use database storage:
```python
from db_manager import DatabaseManager

db = DatabaseManager()
user_id, is_new = db.get_or_create_user("username")

# Save profile
db.save_profile(user_id, {"age": 30, "weight": "70kg", "goals": "lose weight"})

# Save workout plan
workout_data = [plan.model_dump() for plan in workout_plan]
plan_id = db.save_workout_plan(user_id, "My Workout Plan", workout_data)

# Get saved plans
saved_plans = db.get_workout_plans(user_id)
```

## Data Models

### WorkoutPlan
- day: str
- exercises: List[Dict[str, str]]
- duration: str
- intensity: str

### DietPlan
- meal_type: str
- foods: List[str]
- calories: int
- macros: Dict[str, float]

## Database Schema

The PostgreSQL database includes the following tables:
- `users`: User accounts with usernames
- `profiles`: User profile data stored as JSONB
- `workout_plans`: Saved workout plans with timestamps
- `diet_plans`: Saved diet plans with timestamps
- `sessions`: Chat session tracking (future use)

## Available Ollama Models

The agent can work with any Ollama model that supports JSON output. Some recommended models:
- llama2 (default)
- mistral
- codellama
- neural-chat

To use a different model, make sure to pull it first:
```bash
ollama pull model_name
```

## Security Notes

- Never commit your API keys or credentials to version control
- Store sensitive information in environment variables
- Keep your Google Calendar credentials secure
- Use strong passwords for your PostgreSQL database

## Contributing

Feel free to submit issues and enhancement requests! 