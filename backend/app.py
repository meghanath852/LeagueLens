from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import json
from datetime import datetime
import uvicorn
import os
import subprocess
import signal
import time
import threading
import sys
import logging
from pydantic import BaseModel
from dotenv import load_dotenv
import pandas as pd
import numpy as np

# --- Initialize Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Load Environment Variables ---
load_dotenv(override=True)
logger.info("Environment variables loaded.")

# --- Optional: Import and Initialize Chat Agent Components ---
try:
    logger.info("Importing SQL setup...")
    sys.path.append(os.path.join(os.path.dirname(__file__), 'chat'))
    import chat.sql_setup as sql_setup
    sql_engine = sql_setup.setup_database(csv_filepath='chat/deliveries.csv')
    if sql_engine is None:
        logger.error("Database setup failed during API initialization.")
    else:
        logger.info("Database setup completed successfully.")
    
    logger.info("Initializing live match data processor...")
    from chat.live_match_processor import LiveMatchRelevanceChecker
    live_match_checker = LiveMatchRelevanceChecker()
    has_live_match_data = live_match_checker.check_for_live_data()
    if has_live_match_data:
        logger.info("Live cricket match data is available for processing.")
    else:
        logger.warning("No live cricket match data found.")

    logger.info("Importing LangGraph agent components...")
    from chat.langgraph_agent_sql import compile_graph, GraphState, retriever, initialize_state
    
    # --- Compile the LangGraph Agent ---
    logger.info("Compiling LangGraph agent...")
    compiled_app = compile_graph()
    if compiled_app:
        logger.info("LangGraph agent compiled successfully.")
        chat_available = True
    else:
        logger.error("LangGraph agent compilation failed.")
        chat_available = False

    # --- Check Pathway Connection Status ---
    if retriever:
        logger.info("Pathway retriever seems available.")
    else:
        logger.warning("Pathway retriever is NOT available. Vector search will be skipped.")

except ImportError as e:
    logger.exception(f"Failed to import necessary modules for chat: {e}")
    chat_available = False
except Exception as e:
    logger.exception(f"An unexpected error occurred during chat initialization: {e}")
    chat_available = False

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["Content-Type", "Authorization"],
)


# Load the CSV
df = pd.read_csv("ipl_player_statistics_updated.csv")
df.columns = df.columns.str.strip()

# Rename important columns
df = df.rename(columns={
    "player": "Player",
    "runs_scored": "Runs",
    "wickets": "Wickets",
    "image_url": "image_url"  # if it exists
})

# Add team and id
df["id"] = df.index
# df["team"] = "Unknown"

# Fill/clean columns (where needed)
df["Player"] = df["Player"].fillna("Unnamed")
df["Runs"] = df["Runs"].fillna(0).astype(int)
df["Wickets"] = df["Wickets"].fillna(0).astype(int)
df["image_url"] = df["image_url"].fillna("")

@app.get("/players")
def get_players():
    return df.replace({np.nan: None}).to_dict(orient="records")

@app.get("/players/{player_id}")
def get_player(player_id: int):
    player = df[df["id"] == player_id]
    if player.empty:
        return {"error": "Player not found"}
    return player.replace({np.nan: None}).iloc[0].to_dict()


# Path to commentary history file
COMMENTARY_FILE = "commentary_history.json"

# Global variable to track the commentary process
commentary_process = None
commentary_status = "stopped"
commentary_lock = threading.Lock()

# --- Request and Response Models for Chat ---
class QueryRequest(BaseModel):
    question: str

class AnswerResponse(BaseModel):
    answer: str | None = None
    error: str | None = None

@app.get('/api/chat/status')
def chat_status():
    """Returns the status of the chat system"""
    return {"available": chat_available}

@app.post('/api/chat/ask', response_model=AnswerResponse)
async def ask_agent(request: QueryRequest):
    """
    Receives a question, runs it through the LangGraph agent,
    and returns the generated answer or an error.
    """
    if not chat_available:
        return AnswerResponse(
            answer=None, 
            error="Chat service is not available. Check server logs for details."
        )
        
    question = request.question
    logger.info(f"Received question: {question}")

    if not compiled_app:
        logger.error("Agent not compiled or available.")
        return AnswerResponse(
            answer=None,
            error="Agent service is unavailable."
        )

    if not question or not question.strip():
        return AnswerResponse(
            answer=None,
            error="Question cannot be empty."
        )

    try:
        # Prepare initial state for the agent
        inputs = initialize_state()
        inputs["question"] = question
        final_state_snapshot = {}

        logger.info("Invoking LangGraph agent...")
        final_state_snapshot = compiled_app.invoke(inputs, {"recursion_limit": 15})
        logger.info("Agent invocation complete.")

        # Extract the final answer
        final_answer = None
        if isinstance(final_state_snapshot, dict):
            final_answer = final_state_snapshot.get('generation')

            if final_answer is not None:
                 logger.info("Successfully extracted 'generation' key.")
            else:
                 logger.warning("Could not find 'generation' key OR its value was None in the final state dictionary.")

        if final_answer:
            logger.info(f"Agent generated answer (length: {len(final_answer)}).")
            return AnswerResponse(answer=final_answer)
        else:
            logger.warning("Agent finished but no final answer could be extracted.")
            error_msg = "Agent finished processing, but could not determine a final answer."
            return AnswerResponse(answer=None, error=error_msg)

    except Exception as e:
        logger.exception(f"Error during agent execution for question '{question}': {e}")
        return AnswerResponse(
            answer=None,
            error=f"An error occurred while processing the question: {str(e)}"
        )

@app.post('/api/commentary/start')
def start_commentary():
    """Start the commentary service"""
    global commentary_process, commentary_status
    
    with commentary_lock:
        if commentary_status == "running":
            return {"status": "already_running", "message": "Commentary service is already running"}
        
        try:
            # Get the absolute path to run_commentary.py
            script_dir = os.path.dirname(os.path.abspath(__file__))
            commentary_script = os.path.join(script_dir, "run_commentary.py")
            
            # Start the commentary process
            commentary_process = subprocess.Popen(
                [sys.executable, commentary_script],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Wait a moment to ensure the process starts correctly
            time.sleep(2)
            
            if commentary_process.poll() is None:
                # Process is running
                commentary_status = "running"
                return {"status": "started", "message": "Commentary service started successfully"}
            else:
                # Process failed to start
                return {"status": "error", "message": "Failed to start commentary service"}
                
        except Exception as e:
            return {"status": "error", "message": f"Error starting commentary service: {str(e)}"}

@app.post('/api/commentary/stop')
def stop_commentary():
    """Stop the commentary service"""
    global commentary_process, commentary_status
    
    with commentary_lock:
        if commentary_status != "running" or commentary_process is None:
            return {"status": "not_running", "message": "Commentary service is not running"}
        
        try:
            # Get the process group to terminate all child processes too
            pid = commentary_process.pid
            
            # Terminate the process
            commentary_process.terminate()
            
            # Give it some time to terminate gracefully
            time.sleep(2)
            
            # If it's still running, kill it
            if commentary_process.poll() is None:
                commentary_process.kill()
                
                # On Unix/Linux/Mac, try to kill the process group
                try:
                    import os
                    import signal
                    os.killpg(os.getpgid(pid), signal.SIGTERM)
                except (ImportError, AttributeError, ProcessLookupError):
                    # This might not work on all platforms or if the process is already gone
                    pass
            
            commentary_status = "stopped"
            commentary_process = None
            
            # Also check for any remaining python processes with "run_commentary.py" 
            # and terminate them (for extra safety)
            try:
                import subprocess
                result = subprocess.run(
                    ["ps", "aux"], 
                    capture_output=True, 
                    text=True
                )
                for line in result.stdout.splitlines():
                    if "python" in line and "run_commentary.py" in line:
                        # Extract PID (second column in ps output)
                        parts = line.split()
                        if len(parts) > 1:
                            try:
                                leftover_pid = int(parts[1])
                                os.kill(leftover_pid, signal.SIGTERM)
                                logger.info(f"Terminated leftover commentary process with PID {leftover_pid}")
                            except (ValueError, ProcessLookupError) as e:
                                logger.warning(f"Failed to terminate process: {e}")
            except Exception as e:
                logger.warning(f"Error cleaning up additional processes: {e}")
            
            return {"status": "stopped", "message": "Commentary service stopped successfully"}
            
        except Exception as e:
            logger.error(f"Error stopping commentary service: {e}")
            return {"status": "error", "message": f"Error stopping commentary service: {str(e)}"}

@app.get('/api/commentary/status')
def get_commentary_status():
    """Get the current status of the commentary service"""
    return {"status": commentary_status}

@app.get('/api/live-commentary')
def live_commentary():
    """Endpoint to get the most recent commentary"""
    try:
        # Check if commentary file exists
        if not os.path.exists(COMMENTARY_FILE):
            return {"commentary": "Commentary not available yet.", "timestamp": ""}
        
        # Load commentary history
        with open(COMMENTARY_FILE, 'r') as f:
            commentaries = json.load(f)
        
        # Get the most recent commentary
        if commentaries:
            latest = commentaries[-1]
            return {
                "commentary": latest["commentary"],
                "timestamp": latest["timestamp"]
            }
        else:
            return {"commentary": "Commentary not available yet.", "timestamp": ""}
    
    except Exception as e:
        print(f"Error fetching commentary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get('/api/live-scores')
def live_scores():
    try:
        # Use a relative path instead of hardcoded absolute path
        import os
        file_path = os.path.join(os.path.dirname(__file__), 'data_live.json')
        
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        # Check if data is empty
        if not data:
            logger.error("data_live.json is empty or contains no match data")
            return JSONResponse(
                status_code=404,
                content={"error": "No live match data available"}
            )
            
        # Get the match ID and initial data    
        match_id = list(data.keys())[0]
        logger.info(f"Processing match ID: {match_id}")
        match_data = data[match_id]
        
        # Safely extract nested data with default values
        try:
            common_data = match_data.get("centre", {}).get("common", {})
        except Exception as e:
            logger.error(f"Error accessing centre.common data: {e}")
            common_data = {}
            
        try:
            current_innings = common_data.get("innings", {})
        except Exception as e:
            logger.error(f"Error accessing innings data: {e}")
            current_innings = {}
            
        try:
            innings_list = common_data.get("innings_list", [])
        except Exception as e:
            logger.error(f"Error accessing innings_list data: {e}")
            innings_list = []

        # Extract team names with safe fallbacks
        current_innings_meta = next((inn for inn in innings_list if inn.get("current") == 1), {})
        
        # Direct extraction of team names from match_info
        team1_name = match_data.get("match", {}).get("team1_name", "Team 1")
        team2_name = match_data.get("match", {}).get("team2_name", "Team 2")
        
        # Get batting team ID from current innings
        batting_team_id = current_innings.get("batting_team_id")
        team1_id = match_data.get("match", {}).get("team1_id")
        team2_id = match_data.get("match", {}).get("team2_id")
        
        # Additional ways to determine which team is batting
        innings_number = match_data.get("innings", [])[0].get("innings_number", "1") if match_data.get("innings", []) else "1"
        batting_first_team_id = match_data.get("match", {}).get("batting_first_team_id")
        
        logger.info(f"Innings number: {innings_number}, Batting first team ID: {batting_first_team_id}")
        logger.info(f"Batting team ID: {batting_team_id}, Team1 ID: {team1_id}, Team2 ID: {team2_id}")
        
        # Determine which team is batting
        # If batting_team_id is explicitly provided, use that
        # Otherwise, use batting_first_team_id to determine who's batting in first innings
        team_batting = None
        
        # Try to get the current batting team ID directly from the data
        current_batting_team_id = None
        
        # Method 1: Check the current_innings directly
        if current_innings and 'batting_team_id' in current_innings:
            current_batting_team_id = current_innings.get('batting_team_id')
            logger.info(f"Got batting team ID from current_innings: {current_batting_team_id}")
        
        # Method 2: Check the innings_list for the current innings
        if not current_batting_team_id and innings_list:
            current_innings_item = next((inn for inn in innings_list if inn.get('current') == 1), None)
            if current_innings_item:
                current_batting_team_id = current_innings_item.get('team_id')
                logger.info(f"Got batting team ID from innings_list: {current_batting_team_id}")
        
        # Method 3: Check the live data structure
        if not current_batting_team_id:
            live_innings = match_data.get('live', {}).get('innings', {})
            if live_innings and 'batting_team_id' in live_innings:
                current_batting_team_id = live_innings.get('batting_team_id')
                logger.info(f"Got batting team ID from live.innings: {current_batting_team_id}")
        
        # Use the discovered batting team ID if we found one
        if current_batting_team_id:
            if str(current_batting_team_id) == str(team1_id):
                team_batting = "team1"
            elif str(current_batting_team_id) == str(team2_id):
                team_batting = "team2"
            logger.info(f"Determined batting team from discovered ID: {team_batting}")
        
        # Fallback to other methods if we couldn't determine the batting team
        if not team_batting:
            # Get innings number to determine if we're in first or second innings
            innings_number = current_innings.get('innings_number', '1')
            logger.info(f"Current innings number: {innings_number}")
            
            # If we have batting_first_team_id, we can determine who's batting based on innings
            if batting_first_team_id:
                is_first_innings = innings_number == "1"
                if str(batting_first_team_id) == str(team1_id):
                    team_batting = "team1" if is_first_innings else "team2"
                elif str(batting_first_team_id) == str(team2_id):
                    team_batting = "team2" if is_first_innings else "team1"
                logger.info(f"Determined batting team from innings number: {team_batting}")
                
        # If we still can't determine, default to team2 (SRH) being the batting team
        if not team_batting:
            team_batting = "team2"
            logger.info(f"Using default batting team: {team_batting}")
        
        logger.info(f"Final determination - Team batting: {team_batting}")
        
        # Initialize scores with default values
        team1_score = "Yet to bat"
        team2_score = "Yet to bat"
        
        # Based on who's batting, set up our response data
        if team_batting == "team1":
            # Team 1 is batting (Mumbai Indians)
            batting_team_name = team1_name
            waiting_team_name = team2_name
            
            # In our API response:
            # Team 1 should be Sunrisers (completed 20 overs)
            # Team 2 should be Mumbai Indians (currently batting)
            response_team1_name = team2_name  # Sunrisers (completed innings)
            response_team2_name = team1_name  # Mumbai Indians (batting)
            
            response_team1_obj_id = match_data.get("match", {}).get("team2_object_id", "0")
            response_team2_obj_id = match_data.get("match", {}).get("team1_object_id", "0")
        else:
            # Team 2 is batting (Sunrisers)
            batting_team_name = team2_name
            waiting_team_name = team1_name
            
            # In our API response:
            # Team 1 should be Sunrisers (completed 20 overs)
            # Team 2 should be Mumbai Indians (currently batting)
            response_team1_name = team2_name  # Sunrisers (completed innings)
            response_team2_name = team1_name  # Mumbai Indians (currently batting)
            
            response_team1_obj_id = match_data.get("match", {}).get("team2_object_id", "0")
            response_team2_obj_id = match_data.get("match", {}).get("team1_object_id", "0")
        
        logger.info(f"Response - Team1: {response_team1_name}, Team2: {response_team2_name}")
        
        # Get scores for the respective teams
        # For first innings, the team batting first will have a score and second team "Yet to bat"
        # For second innings, both teams will have scores
        
        # Get details of all innings
        all_innings = match_data.get("innings", [])
        
        # Process completed innings first
        for inning in all_innings:
            inning_num = inning.get("innings_number", "")
            batting_team_id = inning.get("batting_team_id", "")
            runs = inning.get("runs", "0")
            wickets = inning.get("wickets", "0")
            overs = inning.get("overs", "0.0")
            event = inning.get("event", "")
            event_name = inning.get("event_name", "")
            
            # Only consider completed innings here (event=5 is "complete" in cricket data)
            if event == 5 or event_name == "complete":
                # Format the score for this innings
                formatted_score = f"{runs}/{wickets} ({overs} ov)"
                
                # Assign to the correct team based on batting_team_id
                if str(batting_team_id) == str(team1_id):
                    team1_score = formatted_score
                    logger.info(f"Set team1 (ID: {team1_id}) completed innings score: {formatted_score}")
                elif str(batting_team_id) == str(team2_id):
                    team2_score = formatted_score
                    logger.info(f"Set team2 (ID: {team2_id}) completed innings score: {formatted_score}")
        
        # Handle current innings specifically to get the most up-to-date score
        if current_innings:
            # Get the current batting team
            current_batting_team_id = None
            
            # Try different ways to determine the current batting team
            if 'batting_team_id' in current_innings:
                current_batting_team_id = current_innings.get('batting_team_id')
            elif team_batting == "team1":
                current_batting_team_id = team1_id
            elif team_batting == "team2":
                current_batting_team_id = team2_id
                
            if current_batting_team_id:
                # Get current innings details
                current_runs = current_innings.get('runs', 0)
                current_wickets = current_innings.get('wickets', 0)
                current_overs = current_innings.get('overs', '0.0')
                
                # Format the current innings score
                current_formatted_score = f"{current_runs}/{current_wickets} ({current_overs} ov)"
                
                # Update the score for the currently batting team
                if str(current_batting_team_id) == str(team1_id):
                    team1_score = current_formatted_score
                    logger.info(f"Set team1 (ID: {team1_id}) active innings score: {current_formatted_score}")
                elif str(current_batting_team_id) == str(team2_id):
                    team2_score = current_formatted_score
                    logger.info(f"Set team2 (ID: {team2_id}) active innings score: {current_formatted_score}")
        
        # Assign scores to the API response
        if team_batting == "team1":
            # If team 1 is batting (Mumbai), then:
            # - team1_score contains Mumbai's score
            # - team2_score contains Sunrisers's score
            # But in our response:
            # - response_team1 is Sunrisers
            # - response_team2 is Mumbai
            response_team1_score = team2_score  # Sunrisers score
            response_team2_score = team1_score  # Mumbai Indians score
        else:
            # If team 2 is batting (Sunrisers), then:
            # - team1_score contains Mumbai's score
            # - team2_score contains Sunrisers's score
            # But in our response:
            # - response_team1 is Sunrisers
            # - response_team2 is Mumbai
            response_team1_score = team2_score  # Sunrisers score
            response_team2_score = team1_score  # Mumbai Indians score
        
        # Log the final scores
        logger.info(f"Team1 ({response_team1_name}) score: {response_team1_score}")
        logger.info(f"Team2 ({response_team2_name}) score: {response_team2_score}")
        
        # Get additional match status information
        match_status = ""
        required_info = ""
        
        # Extract direct status from match_data.live if available
        direct_status = match_data.get("live", {}).get("status", "")
        
        # Check if we're in a second innings scenario (chasing)
        innings_number = current_innings.get('innings_number') if current_innings else None
        target = current_innings.get('target') if current_innings else None
        
        if innings_number == "2" and target:
            # This is a chase - add details about the target
            current_runs = int(current_innings.get('runs', 0))
            remaining_runs = int(target) - current_runs
            remaining_balls = current_innings.get('remaining_balls')
            remaining_overs = current_innings.get('remaining_overs')
            
            if remaining_runs > 0 and remaining_balls:
                # Still chasing
                required_run_rate = current_innings.get('required_run_rate', 0)
                match_status = f"{response_team2_name} require {remaining_runs} runs from {remaining_overs} overs"
                required_info = f"RRR: {required_run_rate}"
            elif remaining_runs <= 0:
                # Chase completed
                match_status = f"{response_team2_name} won by {10 - int(current_innings.get('wickets', 0))} wickets"
        
        # Extract match result if available
        result = common_data.get("match", {}).get("result_string", "")
        if result:
            match_status = result
        
        # Safely extract additional match data
        match_info = match_data.get("match", {})
        stadium = match_info.get("ground_name", "Unknown Stadium")

        # Add status information to the response
        status_info = {
            "match_status": match_status,
            "required_info": required_info
        }

        # If direct status is available, use it as match_status
        if direct_status:
            status_info["match_status"] = direct_status

        # Build player_id → image_id mapping
        player_id_to_image = {}
        for team in match_data.get("team", []):
            for player in team.get("player", []):
                pid = str(player.get("player_id", ""))
                imgid = player.get("image_id", "")
                if pid and imgid:
                    player_id_to_image[pid] = str(imgid)

        # Get batsmen with image URLs - with safer extraction
        batsmen = []
        for player in match_data.get("centre", {}).get("batting", []):
            if player.get("live_current_name") in ["striker", "non-striker"]:
                pid = str(player.get("player_id", ""))
                image_id = player_id_to_image.get(pid, "")
                image_id_prefix = image_id[:4] + "00" if len(image_id) >= 4 else ""
                batsmen.append({
                    "name": player.get("known_as", ""),
                    "runs": int(player.get("runs", 0)),
                    "balls": int(player.get("balls_faced", 0)),
                    "image_url": f"https://img1.hscicdn.com/image/upload/f_auto,t_ds_square_w_320,q_50/lsci/db/PICTURES/CMS/{image_id_prefix}/{image_id}.png" if image_id else ""
                })

        # Get bowler with image - with safer extraction
        bowler = {}
        for player in match_data.get("centre", {}).get("bowling", []):
            if player.get("live_current_name") == "current bowler":
                pid = str(player.get("player_id", ""))
                image_id = player_id_to_image.get(pid, "")
                image_id_prefix = image_id[:4] + "00" if len(image_id) >= 4 else ""
                bowler = {
                    "name": player.get("known_as", ""),
                    "overs": player.get("overs", "0.0"),
                    "wickets": int(player.get("wickets", 0)),
                    "image_url": f"https://img1.hscicdn.com/image/upload/f_auto,t_ds_square_w_320,q_50/lsci/db/PICTURES/CMS/{image_id_prefix}/{image_id}.png" if image_id else ""
                }
                break

        # Format present_datetime_local to 12-hr IST - with safer extraction
        last_updated = ""
        try:
            raw_time = match_data.get("match", {}).get("present_datetime_local")
            if raw_time:
                dt = datetime.strptime(raw_time, "%Y-%m-%d %H:%M:%S")
                last_updated = dt.strftime("%I:%M:%S %p")  # 12-hour format with seconds
        except Exception as e:
            logger.error(f"Error formatting datetime: {e}")
            last_updated = ""

        scores = [{
            "id": match_id,
            "team1": response_team1_name,
            "team1Score": response_team1_score,
            "team1ObjectId": response_team1_obj_id,
            "team2": response_team2_name,
            "team2Score": response_team2_score,
            "team2ObjectId": response_team2_obj_id,
            "result": result,
            "batsmen": batsmen,
            "bowler": bowler,
            "stadium": stadium,
            "last_updated": last_updated,
            "status_info": status_info
        }]

        return scores

    except FileNotFoundError:
        logger.error("data_live.json file not found")
        return JSONResponse(
            status_code=404,
            content={"error": "Live match data file not found"}
        )
    except json.JSONDecodeError:
        logger.error("Invalid JSON format in data_live.json")
        return JSONResponse(
            status_code=500,
            content={"error": "Invalid data format in live match data file"}
        )
    except KeyError as e:
        logger.error(f"Missing key in data structure: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Data structure error: missing {str(e)}"}
        )
    except Exception as e:
        logger.error(f"Error processing data: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Error processing data: {str(e)}"}
        )

if __name__ == '__main__':
    uvicorn.run("app:app", host="0.0.0.0", port=8051, reload=True)