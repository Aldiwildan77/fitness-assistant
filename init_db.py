#!/usr/bin/env python3
"""
Database Initialization Script for Fitness Agent

This script initializes the PostgreSQL database tables required for the Fitness Agent application.
It creates the necessary tables if they don't already exist.

Usage:
    python init_db.py
"""

import logging
import sys

from dotenv import load_dotenv

from db_manager import DatabaseManager

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/init_db.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("init_db")


def initialize_database():
    """Initialize the database by creating all necessary tables."""
    logger.info("Starting database initialization...")

    # Load environment variables to get database connection parameters
    load_dotenv()

    try:
        # Create a database manager instance
        db_manager = DatabaseManager()

        # Set up tables
        db_manager.setup_tables()

        # Test connection with a sample user
        test_user_id, is_new = db_manager.get_or_create_user("test_user")
        if is_new:
            logger.info(f"Created test user with ID: {test_user_id}")
            # Save a sample profile
            db_manager.save_profile(
                test_user_id,
                {
                    "name": "Test User",
                    "age": 30,
                    "fitness_level": "intermediate",
                    "goals": "general fitness",
                },
            )
            logger.info("Added sample profile for test user")
        else:
            logger.info(f"Test user already exists with ID: {test_user_id}")

        # Close the database connection
        db_manager.close()

        logger.info("Database initialization completed successfully!")
        print("✅ Database initialized successfully!")
        print("You can now run the fitness agent application.")

    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        print(f"❌ Error initializing database: {str(e)}")
        print("Please check your database connection parameters in the .env file.")
        sys.exit(1)


if __name__ == "__main__":
    initialize_database()
