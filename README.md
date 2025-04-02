# Fitness Agent

A LangChain-based AI agent that helps with fitness planning, including workout routines, diet plans, and calendar scheduling.

## Features

- Personalized workout plan generation
- Diet plan creation with macro tracking
- Google Calendar integration for workout scheduling
- Workout plan validation and refinement
- Context-aware fitness recommendations

## Prerequisites

- Python 3.8+
- Ollama installed locally (https://ollama.ai)
- Google Calendar API credentials

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

## Usage

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

5. Get scheduled workouts:
```python
schedule = agent.get_workout_schedule(start_date, days=5)
```

6. Refine workout plan based on feedback:
```python
refined_plan = agent.refine_workout_context(
    "The leg exercises are too intense",
    current_plan=workout_plan
)
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

## Contributing

Feel free to submit issues and enhancement requests! 