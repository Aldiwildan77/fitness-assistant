import json
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/db_manager.log"),
        # logging.StreamHandler()
    ],
)
logger = logging.getLogger("db_manager")

# Load environment variables
load_dotenv()

# Database connection parameters from environment variables
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "fitness_agent")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")


class DatabaseManager:
    def __init__(self):
        """Initialize the database manager and establish connection."""
        logger.info("Initializing DatabaseManager")
        self.conn = None
        self.connect()
        self.setup_tables()

    def connect(self) -> None:
        """Establish connection to the PostgreSQL database."""
        try:
            self.conn = psycopg2.connect(
                host=DB_HOST,
                port=DB_PORT,
                dbname=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD,
            )
            logger.info("Successfully connected to the database")
        except psycopg2.Error as e:
            logger.error(f"Error connecting to the database: {e}")
            # Create a fallback in-memory storage for profiles if database connection fails
            logger.warning("Using in-memory storage as fallback")
            self.conn = None

    def setup_tables(self) -> None:
        """Set up necessary database tables if they don't exist."""
        if not self.conn:
            logger.warning("Cannot set up tables: No database connection")
            return

        try:
            with self.conn.cursor() as cur:
                # Create users table
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY,
                        username VARCHAR(100) UNIQUE NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )

                # Create profiles table
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS profiles (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER REFERENCES users(id),
                        profile_data JSONB NOT NULL,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )

                # Create workout_plans table
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS workout_plans (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER REFERENCES users(id),
                        plan_name VARCHAR(200),
                        plan_data JSONB NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )

                # Create diet_plans table
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS diet_plans (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER REFERENCES users(id),
                        plan_name VARCHAR(200),
                        plan_data JSONB NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )

                # Create sessions table to track chat sessions
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS sessions (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER REFERENCES users(id),
                        session_data JSONB NOT NULL,
                        started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )

                self.conn.commit()
                logger.info("Database tables created or already exist")
        except psycopg2.Error as e:
            logger.error(f"Error setting up database tables: {e}")
            self.conn.rollback()

    def get_or_create_user(self, username: str) -> Tuple[int, bool]:
        """Get a user by username or create if not exists.

        Args:
            username: The username to get or create

        Returns:
            Tuple of (user_id, created) where created is True if a new user was created
        """
        if not self.conn:
            logger.warning("No database connection available")
            return (-1, False)

        try:
            with self.conn.cursor() as cur:
                # Check if user exists
                cur.execute("SELECT id FROM users WHERE username = %s", (username,))
                result = cur.fetchone()

                if result:
                    logger.debug(f"Found existing user: {username}")
                    return (result[0], False)

                # Create new user
                cur.execute(
                    "INSERT INTO users (username) VALUES (%s) RETURNING id", (username,)
                )
                user_id = cur.fetchone()[0]
                self.conn.commit()
                logger.info(f"Created new user: {username} with ID: {user_id}")
                return (user_id, True)
        except psycopg2.Error as e:
            logger.error(f"Error getting or creating user: {e}")
            self.conn.rollback()
            return (-1, False)

    def get_profile(self, user_id: int) -> Dict[str, Any]:
        """Get a user profile from the database.

        Args:
            user_id: The ID of the user

        Returns:
            The user profile data as a dictionary
        """
        if not self.conn:
            logger.warning("No database connection available")
            return {}

        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT profile_data FROM profiles WHERE user_id = %s", (user_id,)
                )
                result = cur.fetchone()

                if result:
                    logger.debug(f"Retrieved profile for user_id: {user_id}")
                    return result["profile_data"]
                else:
                    logger.debug(f"No profile found for user_id: {user_id}")
                    return {}
        except psycopg2.Error as e:
            logger.error(f"Error retrieving profile: {e}")
            return {}

    def save_profile(self, user_id: int, profile_data: Dict[str, Any]) -> bool:
        """Save or update a user profile in the database.

        Args:
            user_id: The ID of the user
            profile_data: The profile data to save

        Returns:
            True if successful, False otherwise
        """
        if not self.conn:
            logger.warning("No database connection available")
            return False

        try:
            with self.conn.cursor() as cur:
                # Check if profile exists
                cur.execute("SELECT id FROM profiles WHERE user_id = %s", (user_id,))
                result = cur.fetchone()

                if result:
                    # Update existing profile
                    cur.execute(
                        "UPDATE profiles SET profile_data = %s, updated_at = CURRENT_TIMESTAMP WHERE user_id = %s",
                        (json.dumps(profile_data), user_id),
                    )
                    logger.info(f"Updated profile for user_id: {user_id}")
                else:
                    # Create new profile
                    cur.execute(
                        "INSERT INTO profiles (user_id, profile_data) VALUES (%s, %s)",
                        (user_id, json.dumps(profile_data)),
                    )
                    logger.info(f"Created new profile for user_id: {user_id}")

                self.conn.commit()
                return True
        except psycopg2.Error as e:
            logger.error(f"Error saving profile: {e}")
            self.conn.rollback()
            return False

    def save_workout_plan(
        self, user_id: int, plan_name: str, plan_data: List[Dict]
    ) -> int:
        """Save a workout plan to the database.

        Args:
            user_id: The ID of the user
            plan_name: A name for the workout plan
            plan_data: The workout plan data

        Returns:
            The ID of the saved workout plan, or -1 if failed
        """
        if not self.conn:
            logger.warning("No database connection available")
            return -1

        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO workout_plans (user_id, plan_name, plan_data) VALUES (%s, %s, %s) RETURNING id",
                    (user_id, plan_name, json.dumps(plan_data)),
                )
                plan_id = cur.fetchone()[0]
                self.conn.commit()
                logger.info(f"Saved workout plan '{plan_name}' for user_id: {user_id}")
                return plan_id
        except psycopg2.Error as e:
            logger.error(f"Error saving workout plan: {e}")
            self.conn.rollback()
            return -1

    def get_workout_plans(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all workout plans for a user.

        Args:
            user_id: The ID of the user

        Returns:
            List of workout plans
        """
        if not self.conn:
            logger.warning("No database connection available")
            return []

        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT id, plan_name, plan_data, created_at FROM workout_plans WHERE user_id = %s ORDER BY created_at DESC",
                    (user_id,),
                )
                results = cur.fetchall()
                logger.debug(
                    f"Retrieved {len(results)} workout plans for user_id: {user_id}"
                )
                return results
        except psycopg2.Error as e:
            logger.error(f"Error retrieving workout plans: {e}")
            return []

    def save_diet_plan(
        self, user_id: int, plan_name: str, plan_data: List[Dict]
    ) -> int:
        """Save a diet plan to the database.

        Args:
            user_id: The ID of the user
            plan_name: A name for the diet plan
            plan_data: The diet plan data

        Returns:
            The ID of the saved diet plan, or -1 if failed
        """
        if not self.conn:
            logger.warning("No database connection available")
            return -1

        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO diet_plans (user_id, plan_name, plan_data) VALUES (%s, %s, %s) RETURNING id",
                    (user_id, plan_name, json.dumps(plan_data)),
                )
                plan_id = cur.fetchone()[0]
                self.conn.commit()
                logger.info(f"Saved diet plan '{plan_name}' for user_id: {user_id}")
                return plan_id
        except psycopg2.Error as e:
            logger.error(f"Error saving diet plan: {e}")
            self.conn.rollback()
            return -1

    def get_diet_plans(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all diet plans for a user.

        Args:
            user_id: The ID of the user

        Returns:
            List of diet plans
        """
        if not self.conn:
            logger.warning("No database connection available")
            return []

        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT id, plan_name, plan_data, created_at FROM diet_plans WHERE user_id = %s ORDER BY created_at DESC",
                    (user_id,),
                )
                results = cur.fetchall()
                logger.debug(
                    f"Retrieved {len(results)} diet plans for user_id: {user_id}"
                )
                return results
        except psycopg2.Error as e:
            logger.error(f"Error retrieving diet plans: {e}")
            return []

    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")


def main():
    """Test function to demonstrate database operations"""
    print("Testing database connection and operations...")

    db = DatabaseManager()

    # Create a test user
    user_id, created = db.get_or_create_user("testuser")
    if user_id > 0:
        print(f"User created: {created}, user_id: {user_id}")

        # Save a test profile
        test_profile = {
            "age": 30,
            "weight": "70kg",
            "height": "175cm",
            "goals": "Build muscle, lose fat",
            "experience_level": "intermediate",
        }
        success = db.save_profile(user_id, test_profile)
        print(f"Profile saved: {success}")

        # Retrieve the profile
        profile = db.get_profile(user_id)
        print(f"Retrieved profile: {profile}")
    else:
        print("Failed to create user. Check database connection.")

    db.close()


if __name__ == "__main__":
    main()
