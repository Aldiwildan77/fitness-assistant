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

## Setup Instructions

1. Clone this repository.
2. Create a virtual environment:
   ```
   python -m venv venv
   ```
3. Activate the virtual environment:
   - Windows: `venv\Scripts\activate`
   - macOS/Linux: `source venv/bin/activate`
4. Install the required packages:
   ```
   pip install -r requirements.txt
   ```
5. Initialize the database:
   ```
   python init_db.py
   ```
6. Configure LangSmith (optional):
   - Sign up for [LangSmith](https://smith.langchain.com)
   - Set the following environment variables:
     ```
     LANGCHAIN_API_KEY=your_api_key
     LANGCHAIN_PROJECT=your_project
     ```

## Running the Application

You can run the application in two ways:

### Command Line Interface

Run the interactive chat interface:

```
python run.py <username>
```

Replace `<username>` with your username (e.g., `python run.py john_doe`).

### Streamlit Web Interface

Run the Streamlit web application:

```
streamlit run app.py
```

Then open your browser and go to http://localhost:8501

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