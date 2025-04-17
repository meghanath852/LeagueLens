import pathway as pw
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import pandas as pd

# First, ensure the database exists
# DB_USER = "postgres"
# DB_PASSWORD = "postgres"
# DB_HOST = "localhost"
# DB_PORT = "5432"
# DB_NAME = "quicksell"

DB_USER="postgres"
DB_PASSWORD="postgres"
DB_HOST="localhost"
DB_PORT="5432"
DB_NAME="pathway_sql_test" 


def create_database_if_not_exists():
    try:
        # Connect to PostgreSQL server with default database
        conn = psycopg2.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT,
            database="postgres"  # Connect to default postgres database
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Check if database exists
        cursor.execute(f"SELECT 1 FROM pg_catalog.pg_database WHERE datname = '{DB_NAME}'")
        exists = cursor.fetchone()
        
        if not exists:
            print(f"Creating database '{DB_NAME}'...")
            cursor.execute(f"CREATE DATABASE {DB_NAME}")
            print(f"Database '{DB_NAME}' created successfully.")
        else:
            print(f"Database '{DB_NAME}' already exists.")
        
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error creating database: {e}")
        return False

# Read a sample of the CSV to determine data types
def analyze_csv_structure():
    try:
        print("Analyzing CSV structure...")
        # Read a sample of the CSV to determine data types
        df = pd.read_csv('deliveries.csv', nrows=100)
        
        # Print column names and their data types
        print("\nCSV Column Data Types:")
        for col, dtype in df.dtypes.items():
            print(f"{col}: {dtype}")
            
        return df
    except Exception as e:
        print(f"Error analyzing CSV structure: {e}")
        return None

# Create the delivery table if it doesn't exist
def create_delivery_table(df):
    try:
        # Connect to the quicksell database
        conn = psycopg2.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Drop the table if it exists (for clean restart)
        cursor.execute("DROP TABLE IF EXISTS delivery")
        print("Dropped existing delivery table if it existed.")
        
        # Create table based on the CSV structure
        print("Creating delivery table...")
        create_table_sql = '''
        CREATE TABLE delivery (
            match_id INTEGER PRIMARY KEY,
            inning INTEGER,
            batting_team VARCHAR(255),
            bowling_team VARCHAR(255),
            over INTEGER,
            ball INTEGER,
            batter VARCHAR(255),
            bowler VARCHAR(255),
            non_striker VARCHAR(255),
            batsman_runs INTEGER,
            extra_runs INTEGER,
            total_runs INTEGER,
            extras_type VARCHAR(255),
            is_wicket INTEGER,  -- Changed to INTEGER to match data
            player_dismissed VARCHAR(255),
            dismissal_kind VARCHAR(255),
            fielder VARCHAR(255),
            time BIGINT,       -- Add the time column required by Pathway
            diff INTEGER       -- Add the diff column required by Pathway
        )
        '''
        cursor.execute(create_table_sql)
        print("Delivery table created successfully.")
        
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error creating delivery table: {e}")
        return False

# Create the database and table
create_database_if_not_exists()
df = analyze_csv_structure()
create_delivery_table(df)

# Now read the data and write to PostgreSQL
data = pw.io.csv.read(
    'deliveries.csv',
    schema=pw.schema_from_csv("deliveries.csv"),
    mode='static'
)

# Write to PostgreSQL
pw.io.postgres.write_snapshot(
    data,
    {
        "host": "localhost",
        "port": "5432",
        "dbname": "quicksell",
        "user": "postgres",
        "password": "postgres"
    },
    table_name='delivery',
    primary_key=['match_id']
)

pw.run()

import os
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, MetaData, Table, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import time

# Load environment variables
load_dotenv()

# Get PostgreSQL connection details from environment variables or use defaults for local development
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "quicksell")

def create_database_if_not_exists():
    """
    Create the PostgreSQL database if it doesn't exist
    """
    # Maximum number of connection attempts
    max_attempts = 3
    attempt = 0
    
    while attempt < max_attempts:
        attempt += 1
        try:
            print(f"Attempting to connect to PostgreSQL server (attempt {attempt}/{max_attempts})...")
            # Connect to PostgreSQL server with default database
            conn = psycopg2.connect(
                user=DB_USER,
                password=DB_PASSWORD,
                host=DB_HOST,
                port=DB_PORT,
                database="postgres"  # Connect to default postgres database
            )
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()
            
            # Check if database exists
            cursor.execute(f"SELECT 1 FROM pg_catalog.pg_database WHERE datname = '{DB_NAME}'")
            exists = cursor.fetchone()
            
            if not exists:
                print(f"Creating database '{DB_NAME}'...")
                cursor.execute(f"CREATE DATABASE {DB_NAME}")
                print(f"Database '{DB_NAME}' created successfully.")
            else:
                print(f"Database '{DB_NAME}' already exists.")
            
            cursor.close()
            conn.close()
            return True
            
        except psycopg2.OperationalError as e:
            print(f"Connection attempt {attempt} failed: {e}")
            if attempt < max_attempts:
                wait_time = 2 * attempt  # Exponential backoff
                print(f"Waiting {wait_time} seconds before retrying...")
                time.sleep(wait_time)
            else:
                print("Maximum connection attempts reached. Could not connect to PostgreSQL server.")
                print(f"Please check that PostgreSQL is running and accessible with the following settings:")
                print(f"  Host: {DB_HOST}")
                print(f"  Port: {DB_PORT}")
                print(f"  User: {DB_USER}")
                print(f"  Database: postgres (default)")
                return False
        except Exception as e:
            print(f"Error creating database: {e}")
            return False

# Create a connection string for the target database
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Create engine
engine = None
# Create deliveries table as a global variable
deliveries = None

def setup_database():
    """
    Create the deliveries table if it doesn't exist
    """
    global engine, deliveries
    
    try:
        # First, create the database if it doesn't exist
        if not create_database_if_not_exists():
            return False
        
        # Initialize the engine now that we know the database exists
        engine = create_engine(DATABASE_URL)
        
        # Create Base and metadata objects
        Base = declarative_base()
        metadata = MetaData()
        
        # Define Deliveries table structure based on CSV columns
        deliveries = Table(
            'deliveries', 
            metadata,
            Column('id', Integer, primary_key=True),
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
            Column('extras_type', String),
            Column('is_wicket', Boolean),
            Column('player_dismissed', String),
            Column('dismissal_kind', String),
            Column('fielder', String)
        )
            
        # Create the table
        metadata.create_all(engine)
        print("Deliveries table created successfully.")
        
        # Check if data should be loaded (optional)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Check if the table is empty
        try:
            row_count = session.query(deliveries).count()
            if row_count == 0:
                # Load a sample of data from the CSV (to avoid loading the full 26MB file)
                print("Loading sample data from CSV...")
                if os.path.exists('deliveries.csv'):
                    df = pd.read_csv('deliveries.csv', nrows=1000)  # Load only first 1000 rows as sample
                    
                    # Convert data types to match the table schema
                    df['is_wicket'] = df['is_wicket'].astype(bool)
                    
                    # Replace NaN values with None for proper SQL NULL values
                    df = df.where(pd.notnull(df), None)
                    
                    # Insert data into the table
                    df.to_sql('deliveries', engine, if_exists='append', index=False)
                    print("Sample data loaded successfully.")
                else:
                    print("Warning: deliveries.csv file not found. No sample data loaded.")
        except Exception as e:
            print(f"Error checking or loading data: {e}")
        finally:
            session.close()
        
        # Return success
        return True
    except Exception as e:
        print(f"Error setting up database: {e}")
        return False 
    

from sqlalchemy import create_engine, select, func, Integer, text, Table
from sqlalchemy.orm import sessionmaker
import time

# Import setup_database first
from db_setup import setup_database

# Initialize database
setup_database()

# Now import engine and deliveries after they've been initialized
from db_setup import engine, deliveries

# Create session
Session = sessionmaker(bind=engine)

def get_total_deliveries():
    """
    Get the total number of deliveries in the database
    """
    session = Session()
    try:
        result = session.query(func.count()).select_from(deliveries).scalar()
        return result
    except Exception as e:
        print(f"Error getting total deliveries: {e}")
        return 0
    finally:
        session.close()

def get_team_stats(team_name):
    """
    Get stats for a specific team
    """
    session = Session()
    try:
        # Get batting stats
        batting_query = select(
            func.sum(deliveries.c.batsman_runs).label('total_runs'),
            func.count().label('total_balls_faced')
        ).where(deliveries.c.batting_team == team_name)
        
        batting_result = session.execute(batting_query).fetchone()
        
        # Get bowling stats
        bowling_query = select(
            func.sum(deliveries.c.total_runs).label('total_runs_conceded'),
            func.count().label('total_balls_bowled'),
            func.sum(deliveries.c.is_wicket.cast(Integer)).label('total_wickets')
        ).where(deliveries.c.bowling_team == team_name)
        
        bowling_result = session.execute(bowling_query).fetchone()
        
        return {
            'batting': {
                'total_runs': batting_result.total_runs if batting_result.total_runs else 0,
                'total_balls_faced': batting_result.total_balls_faced
            },
            'bowling': {
                'total_runs_conceded': bowling_result.total_runs_conceded if bowling_result.total_runs_conceded else 0,
                'total_balls_bowled': bowling_result.total_balls_bowled,
                'total_wickets': bowling_result.total_wickets if bowling_result.total_wickets else 0
            }
        }
    except Exception as e:
        print(f"Error getting team stats: {e}")
        return {
            'batting': {'total_runs': 0, 'total_balls_faced': 0},
            'bowling': {'total_runs_conceded': 0, 'total_balls_bowled': 0, 'total_wickets': 0}
        }
    finally:
        session.close()

def get_player_stats(player_name):
    """
    Get stats for a specific player
    """
    session = Session()
    try:
        # Get batting stats
        batting_query = select(
            func.sum(deliveries.c.batsman_runs).label('total_runs'),
            func.count().label('total_balls_faced')
        ).where(deliveries.c.batter == player_name)
        
        batting_result = session.execute(batting_query).fetchone()
        
        # Get bowling stats
        bowling_query = select(
            func.sum(deliveries.c.total_runs).label('total_runs_conceded'),
            func.count().label('total_balls_bowled'),
            func.sum(deliveries.c.is_wicket.cast(Integer)).label('total_wickets')
        ).where(deliveries.c.bowler == player_name)
        
        bowling_result = session.execute(bowling_query).fetchone()
        
        return {
            'batting': {
                'total_runs': batting_result.total_runs if batting_result.total_runs else 0,
                'total_balls_faced': batting_result.total_balls_faced
            },
            'bowling': {
                'total_runs_conceded': bowling_result.total_runs_conceded if bowling_result.total_runs_conceded else 0,
                'total_balls_bowled': bowling_result.total_balls_bowled,
                'total_wickets': bowling_result.total_wickets if bowling_result.total_wickets else 0
            }
        }
    except Exception as e:
        print(f"Error getting player stats: {e}")
        return {
            'batting': {'total_runs': 0, 'total_balls_faced': 0},
            'bowling': {'total_runs_conceded': 0, 'total_balls_bowled': 0, 'total_wickets': 0}
        }
    finally:
        session.close() 

import os
import sys
import argparse
import pandas as pd
from db_setup import setup_database
from sqlalchemy import text
import db_setup
# from prompts import sql_query_generator

def test_database_connection():
    """
    Test the PostgreSQL database connection and functions
    """
    print("Testing PostgreSQL database connection...")
    
    # Set up the database first
    try:
        setup_result = setup_database()
        if setup_result:
            print("Database setup successful!")
        else:
            print("Database setup failed.")
            return
    except Exception as e:
        print(f"Error setting up database: {e}")
        return
    
    # Now that the database is set up, import the query functions
    from deliveries_db import get_total_deliveries, get_team_stats, get_player_stats
    
    # Test database queries
    try:
        # Get total deliveries
        total_deliveries = get_total_deliveries()
        print(f"Total deliveries in database: {total_deliveries}")
        
        # Get team stats for a sample team
        team_name = "Kolkata Knight Riders"
        team_stats = get_team_stats(team_name)
        print(f"\nStats for {team_name}:")
        print(f"Batting runs: {team_stats['batting']['total_runs']}")
        print(f"Balls faced: {team_stats['batting']['total_balls_faced']}")
        print(f"Bowling runs conceded: {team_stats['bowling']['total_runs_conceded']}")
        print(f"Balls bowled: {team_stats['bowling']['total_balls_bowled']}")
        print(f"Wickets taken: {team_stats['bowling']['total_wickets']}")
        
        # Get player stats for a sample player
        player_name = "SC Ganguly"
        player_stats = get_player_stats(player_name)
        print(f"\nStats for {player_name}:")
        print(f"Batting runs: {player_stats['batting']['total_runs']}")
        print(f"Balls faced: {player_stats['batting']['total_balls_faced']}")
        print(f"Bowling runs conceded: {player_stats['bowling']['total_runs_conceded']}")
        print(f"Balls bowled: {player_stats['bowling']['total_balls_bowled']}")
        print(f"Wickets taken: {player_stats['bowling']['total_wickets']}")
        
        print("\nDatabase tests completed successfully!")
    except Exception as e:
        print(f"Error testing database: {e}")

def execute_raw_sql(sql_query):
    """
    Execute a raw SQL query and display the results
    
    Args:
        sql_query (str): The SQL query to execute
    """
    print(f"\n--- Executing SQL Query ---")
    print(f"Query: {sql_query}")
    
    try:
        # Initialize database if needed
        if db_setup.engine is None:
            setup_database()
        
        # Execute query
        with db_setup.engine.connect() as connection:
            result = connection.execute(text(sql_query))
            rows = result.fetchall()
            
            # Convert to DataFrame for nicer display
            df = pd.DataFrame(rows, columns=result.keys())
            
            if not df.empty:
                print("\nResults:")
                print(df.to_string(index=False))
                return df
            else:
                print("\nQuery returned no results.")
                return None
    except Exception as e:
        print(f"\nError executing SQL query: {e}")
        return None

def generate_and_execute_sql(question):
    """
    Generate an SQL query from a natural language question and execute it
    
    Args:
        question (str): Natural language question to generate SQL from
    """
    print(f"\n--- Generating SQL for Question ---")
    print(f"Question: {question}")
    
    # Database description for the SQL generator
    db_description = """
    The database contains cricket match delivery information from IPL matches, stored in a table called 'deliveries'.
    
    The table schema is:
    - match_id: The ID of the match
    - inning: The inning number
    - batting_team: Name of the team that is batting
    - bowling_team: Name of the team that is bowling
    - over: The over number
    - ball: The ball number in the current over
    - batter: Name of the batsman facing the ball
    - bowler: Name of the bowler bowling the ball
    - non_striker: Name of the batsman at the non-striker's end
    - batsman_runs: Runs scored by the batsman on this ball
    - extra_runs: Extra runs on this ball (wides, no balls, etc.)
    - total_runs: Total runs scored on this ball
    - extras_type: Type of extras (wide, no ball, etc.)
    - is_wicket: Boolean indicating if a wicket fell on this ball
    - player_dismissed: Name of the player who got out (if a wicket fell)
    - dismissal_kind: How the player got out (caught, bowled, etc.)
    - fielder: Name of the fielder involved in the dismissal (if applicable)
    """
    
    try:
        # Generate SQL query using LLM
        # sql_query = sql_query_generator.invoke({
        #     "question": question,
        #     "database_description": db_description
        # })
        
        # print(f"\nGenerated SQL: {sql_query}")
        
        # # Execute the generated query
        # return execute_raw_sql(sql_query)
        return None
    except Exception as e:
        print(f"\nError generating or executing SQL: {e}")
        return None

def display_help():
    """Display help information about the script"""
    print("\n=== Cricket Database Test Tool ===")
    print("This tool helps test the PostgreSQL database connection and run SQL queries.")
    print("\nUsage modes:")
    print("  1. python test_db.py                     Run the standard database connection test")
    print("  2. python test_db.py --sql 'SQL QUERY'   Execute a specific SQL query")
    print("  3. python test_db.py --ask 'QUESTION'    Generate and execute SQL from a natural language question")
    print("  4. python test_db.py --help              Display this help message")
    print("\nExamples:")
    print("  python test_db.py --sql 'SELECT * FROM deliveries LIMIT 5'")
    print("  python test_db.py --ask 'How many runs did MS Dhoni score?'")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test database connection and execute SQL queries", add_help=False)
    parser.add_argument('--sql', type=str, help='Execute a specific SQL query')
    parser.add_argument('--ask', type=str, help='Generate and execute SQL from a natural language question')
    parser.add_argument('--help', action='store_true', help='Display help information')
    
    # Parse the arguments
    args = parser.parse_args()
    
    if args.help:
        display_help()
    elif args.sql:
        # Initialize database and execute the provided SQL query
        setup_database()
        execute_raw_sql(args.sql)
    elif args.ask:
        # Initialize database, generate SQL from question, and execute it
        setup_database()
        generate_and_execute_sql(args.ask)
    else:
        # Run the standard database connection test
        test_database_connection() 