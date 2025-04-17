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