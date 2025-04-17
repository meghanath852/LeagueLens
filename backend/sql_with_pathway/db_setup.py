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
DB_NAME = os.getenv("DB_NAME", "pathway_sql_test")

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
                    df = pd.read_csv('deliveries.csv')  # Load only first 1000 rows as sample
                    
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