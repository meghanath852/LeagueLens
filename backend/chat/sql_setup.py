# -*- coding: utf-8 -*-
"""
Sets up the PostgreSQL database, creates the 'deliveries' table,
and loads initial data from deliveries.csv.
"""

import os
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, MetaData, Table, text
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import time
import warnings

# Suppress specific SQLAlchemy warnings if desired
warnings.filterwarnings("ignore", category=DeprecationWarning, module='sqlalchemy.engine.reflection')

# Load environment variables from .env file
load_dotenv(override=True)

# Get PostgreSQL connection details from environment variables or use defaults
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "quicksell_rag") # Use a distinct name if needed

# Global engine variable
engine = None
metadata = MetaData()

# Define Deliveries table structure (globally accessible)
deliveries_table = Table(
    'deliveries',
    metadata,
    Column('id', Integer, primary_key=True, autoincrement=True), # Added autoincrement pk
    Column('match_id', Integer),
    Column('inning', Integer),
    Column('batting_team', String),
    Column('bowling_team', String),
    Column('over', Integer),
    Column('ball', Integer),
    Column('batter', String),
    Column('bowler', String),
    Column('non_striker', String),
    Column('batsman_runs', Integer),
    Column('extra_runs', Integer),
    Column('total_runs', Integer),
    Column('extras_type', String, nullable=True), # Allow NULLs
    Column('is_wicket', Boolean),
    Column('player_dismissed', String, nullable=True), # Allow NULLs
    Column('dismissal_kind', String, nullable=True),  # Allow NULLs
    Column('fielder', String, nullable=True) # Allow NULLs
)

def create_database_if_not_exists():
    """Creates the PostgreSQL database if it doesn't exist."""
    max_attempts = 5
    attempt = 0
    conn = None
    cursor = None

    while attempt < max_attempts:
        attempt += 1
        try:
            print(f"Attempting to connect to PostgreSQL server (attempt {attempt}/{max_attempts})...")
            conn = psycopg2.connect(
                user=DB_USER,
                password=DB_PASSWORD,
                host=DB_HOST,
                port=DB_PORT,
                database="postgres" # Connect to default database first
            )
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()

            cursor.execute(f"SELECT 1 FROM pg_catalog.pg_database WHERE datname = %s", (DB_NAME,))
            exists = cursor.fetchone()

            if not exists:
                print(f"Database '{DB_NAME}' does not exist. Creating...")
                cursor.execute(f"CREATE DATABASE {DB_NAME}")
                print(f"Database '{DB_NAME}' created successfully.")
            else:
                print(f"Database '{DB_NAME}' already exists.")

            return True # Success

        except psycopg2.OperationalError as e:
            print(f"Connection attempt {attempt} failed: {e}")
            if attempt < max_attempts:
                wait_time = 2 * attempt
                print(f"Waiting {wait_time} seconds before retrying...")
                time.sleep(wait_time)
            else:
                print("Maximum connection attempts reached. Could not connect to PostgreSQL server.")
                print(f"Please check connection details: Host={DB_HOST}, Port={DB_PORT}, User={DB_USER}")
                return False
        except Exception as e:
            print(f"An unexpected error occurred during database check/creation: {e}")
            return False
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    return False # Failed after retries


def setup_database(csv_filepath='deliveries.csv'):
    """
    Sets up the database connection, creates the table, and loads data.

    Args:
        csv_filepath (str): Path to the CSV file containing delivery data.

    Returns:
        sqlalchemy.engine.Engine or None: The database engine if setup is successful, None otherwise.
    """
    global engine, metadata, deliveries_table

    if not create_database_if_not_exists():
        print("Database setup failed: Could not ensure database existence.")
        return None

    DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

    try:
        print(f"Connecting to database: {DB_NAME}...")
        engine = create_engine(DATABASE_URL)

        # Test connection
        with engine.connect() as connection:
            print("Database connection successful.")

        # Create the table
        print(f"Creating table '{deliveries_table.name}' if it doesn't exist...")
        metadata.create_all(engine)
        print(f"Table '{deliveries_table.name}' ensured.")

        # Check if data needs loading
        Session = sessionmaker(bind=engine)
        session = Session()
        try:
            row_count = session.query(deliveries_table).count()
            if row_count == 0:
                print(f"Table '{deliveries_table.name}' is empty. Attempting to load data from '{csv_filepath}'...")
                if os.path.exists(csv_filepath):
                    try:
                        df = pd.read_csv(csv_filepath)
                        print(f"Loaded {len(df)} rows from CSV.")

                        # Basic Data Cleaning / Type Conversion
                        df['is_wicket'] = df['is_wicket'].astype(bool)
                        # Ensure numeric columns are numeric, fill NA with 0 or handle appropriately
                        numeric_cols = ['match_id', 'inning', 'over', 'ball', 'batsman_runs', 'extra_runs', 'total_runs']
                        for col in numeric_cols:
                             if col in df.columns:
                                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

                        # Replace potential pd.NA or np.nan with None for string columns before insert
                        string_cols = ['batting_team', 'bowling_team', 'batter', 'bowler', 'non_striker', 'extras_type', 'player_dismissed', 'dismissal_kind', 'fielder']
                        for col in string_cols:
                             if col in df.columns:
                                # Convert to string first to handle mixed types, then replace NaN/None
                                df[col] = df[col].astype(str).replace({'nan': None, 'None': None, 'NA': None, '': None})


                        # Select only columns that exist in the table definition
                        table_columns = [c.name for c in deliveries_table.columns if c.name != 'id'] # Exclude 'id' if autoincrement
                        df_to_insert = df[table_columns]


                        # Insert data into the table
                        print("Inserting data into database...")
                        df_to_insert.to_sql(deliveries_table.name, engine, if_exists='append', index=False, chunksize=1000) # Use chunksize
                        print(f"Successfully loaded {len(df)} rows into '{deliveries_table.name}'.")

                    except FileNotFoundError:
                         print(f"Warning: CSV file '{csv_filepath}' not found. No data loaded.")
                    except Exception as load_err:
                         print(f"Error loading data from CSV '{csv_filepath}': {load_err}")

                else:
                    print(f"Warning: CSV file '{csv_filepath}' not found. No data loaded.")
            else:
                print(f"Table '{deliveries_table.name}' already contains {row_count} rows. Skipping data load.")

        except Exception as data_check_err:
            print(f"Error checking or loading data into table: {data_check_err}")
        finally:
            session.close()

        print("Database setup completed.")
        return engine

    except Exception as e:
        print(f"FATAL: Error setting up database engine or table: {e}")
        engine = None # Ensure engine is None on failure
        return None

# Example of how to run setup (optional, usually called from agent script)
if __name__ == "__main__":
    print("Running SQL Database Setup...")
    initialized_engine = setup_database()
    if initialized_engine:
        print("Database setup script finished successfully.")
    else:
        print("Database setup script failed.")