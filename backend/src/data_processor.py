#!/usr/bin/env python3
import json
import logging
import os

logger = logging.getLogger("cricket_commentary.data_processor")

class MatchDataProcessor:
    """Process and extract relevant data from the cricket match JSON"""
    
    def __init__(self, match_id=None, data_file="data_live.json"):
        self.data_file = data_file
        self.match_data = {}
        self.previous_state = {}
        
        # If match_id is not provided, use the first key from data_live.json
        if match_id is None:
            self.match_id = self._get_first_match_id()
        else:
            self.match_id = match_id
    
    def _get_first_match_id(self):
        """Get the first match ID from data file"""
        try:
            file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), self.data_file)
            with open(file_path, "r") as f:
                data = json.loads(f.read())
                if data:
                    match_id = list(data.keys())[0]
                    print(f"\033[91mExtracted match ID: {match_id}\033[0m")
                    return match_id
                else:
                    logger.error(f"Data file {self.data_file} is empty or has no match IDs")
                    match_id = "1473470"  # Default fallback ID
                    print(f"\033[91mUsed default fallback: {match_id}\033[0m")
                    return match_id
        except Exception as e:
            logger.error(f"Error getting match ID from {self.data_file}: {e}")
            return "1473470"  # Default fallback ID
    
    def load_data(self):
        """Load match data from data.json"""
        try:
            # Use a relative path to the data file
            file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), self.data_file)
            
            with open(file_path, "r") as f:
                data = json.loads(f.read())
                self.match_data = data.get(self.match_id, {})
                return self.match_data
        except Exception as e:
            logger.error(f"Error loading match data: {e}")
            return {}
    
    def check_for_updates(self):
        """Check if there have been updates to the match data"""
        current_data = self.load_data()
        
        # Simple check - compare live overs
        current_overs = self._get_current_overs(current_data)
        previous_overs = self._get_current_overs(self.previous_state)
        
        if current_overs != previous_overs:
            self.previous_state = current_data
            return True
        
        return False
    
    def _get_current_overs(self, data):
        """Extract current overs from match data"""
        try:
            if "live" in data and "innings" in data["live"]:
                return data["live"]["innings"].get("overs", "0.0")
            return "0.0"
        except:
            return "0.0"
    
    def get_match_summary(self):
        """Get a summary of the current match state"""
        if not self.match_data:
            self.load_data()
        
        if "live" in self.match_data and "status" in self.match_data["live"]:
            return self.match_data["live"]["status"]
        return "Match information not available"
    
    def get_batsmen_info(self):
        """Get information about current batsmen"""
        batsmen_info = []
        
        if "centre" in self.match_data and "batting" in self.match_data["centre"]:
            batsmen = self.match_data["centre"]["batting"]
            for batsman in batsmen:
                info = {
                    "name": batsman.get("known_as", "Unknown"),
                    "runs": batsman.get("runs", 0),
                    "balls": batsman.get("balls_faced", 0),
                    "fours": batsman.get("runs_summary", [])[1] if len(batsman.get("runs_summary", [])) > 1 else 0,
                    "sixes": batsman.get("runs_summary", [])[4] if len(batsman.get("runs_summary", [])) > 4 else 0,
                    "strike_rate": batsman.get("strike_rate", 0),
                    "status": batsman.get("live_current_name", "")
                }
                batsmen_info.append(info)
        
        return batsmen_info
    
    def get_bowlers_info(self):
        """Get information about current bowlers"""
        bowlers_info = []
        
        if "centre" in self.match_data and "bowling" in self.match_data["centre"]:
            bowlers = self.match_data["centre"]["bowling"]
            for bowler in bowlers:
                info = {
                    "name": bowler.get("known_as", "Unknown"),
                    "overs": bowler.get("overs", "0.0"),
                    "maidens": bowler.get("maidens", 0),
                    "runs": bowler.get("conceded", 0),
                    "wickets": bowler.get("wickets", 0),
                    "economy": bowler.get("economy_rate", 0),
                    "status": bowler.get("live_current_name", "")
                }
                bowlers_info.append(info)
        
        return bowlers_info
    
    def get_recent_commentary(self, num_overs=2):
        """Get recent ball-by-ball commentary"""
        commentary = []
        
        if "comms" in self.match_data:
            recent_overs = self.match_data["comms"][:num_overs]  # Get commentary for recent overs
            for over in recent_overs:
                if "ball" in over:
                    balls = over["ball"]
                    for ball in balls:
                        entry = {
                            "over": ball.get("overs_actual", ""),
                            "players": ball.get("players", ""),
                            "event": ball.get("event", ""),
                            "description": ball.get("text", "")
                        }
                        commentary.append(entry)
        
        return commentary
    
    def get_match_context(self):
        """Get overall match context and statistics"""
        context = {}
        
        if "match" in self.match_data:
            match_info = self.match_data["match"]
            context["description"] = match_info.get("description", "")
            context["venue"] = match_info.get("ground_name", "")
            context["date"] = match_info.get("date", "")
        
        if "live" in self.match_data:
            live_info = self.match_data["live"]
            
            if "innings" in live_info:
                innings = live_info["innings"]
                context["runs"] = innings.get("runs", 0)
                context["wickets"] = innings.get("wickets", 0)
                context["overs"] = innings.get("overs", "0.0")
                context["run_rate"] = innings.get("run_rate", 0)
                context["target"] = innings.get("target", 0)
                
                if context["target"] > 0:
                    context["required_runs"] = context["target"] - context["runs"]
                    context["required_run_rate"] = innings.get("required_run_rate", 0)
                    context["remaining_overs"] = innings.get("remaining_overs", "0.0")
        
        return context
    
    def format_match_data_for_prompt(self):
        """Format match data for LLM prompt"""
        context = self.get_match_context()
        batsmen = self.get_batsmen_info()
        bowlers = self.get_bowlers_info()
        recent_commentary = self.get_recent_commentary()
        
        match_description = context.get("description", "Cricket Match")
        
        # Format batting information
        batting_info = ""
        for batsman in batsmen:
            batting_info += (
                f"{batsman['name']} is {batsman['runs']} off {batsman['balls']} balls "
                f"(SR: {batsman['strike_rate']}, {batsman['fours']} fours, {batsman['sixes']} sixes). "
                f"Status: {batsman['status']}.\n"
            )
        
        # Format bowling information
        bowling_info = ""
        for bowler in bowlers:
            bowling_info += (
                f"{bowler['name']} has {bowler['wickets']}/{bowler['runs']} from {bowler['overs']} overs "
                f"(economy: {bowler['economy']}). Status: {bowler['status']}.\n"
            )
        
        # Format recent commentary
        commentary_text = ""
        for ball in recent_commentary:
            commentary_text += (
                f"{ball['over']} - {ball['players']}: {ball['event']} - {ball['description']}\n"
            )
        
        # Format match situation
        match_situation = ""
        if "runs" in context and "wickets" in context:
            match_situation = f"Score: {context.get('runs', 0)}/{context.get('wickets', 0)} in {context.get('overs', '0.0')} overs"
            
            if "target" in context and context["target"] > 0:
                match_situation += (
                    f". Target: {context.get('target', 0)}. "
                    f"Need {context.get('required_runs', 0)} from {context.get('remaining_overs', '0.0')} overs "
                    f"at RRR {context.get('required_run_rate', 0)} per over."
                )
        
        match_summary = self.get_match_summary()
        
        return {
            "match_description": match_description,
            "match_situation": match_situation,
            "match_summary": match_summary,
            "batting_info": batting_info,
            "bowling_info": bowling_info,
            "recent_commentary": commentary_text
        } 

def main():
    """Test function to demonstrate the MatchDataProcessor functionality"""
    # Configure logging
    logging.basicConfig(level=logging.INFO, 
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Create an instance of MatchDataProcessor
    processor = MatchDataProcessor()
    
    # Load match data
    match_data = processor.load_data()
    if not match_data:
        logger.warning("No match data found. Check if data_live.json exists and contains valid data.")
        return
    
    logger.info(f"Successfully loaded match data for match ID: {processor.match_id}")
    
    # Get and display match summary
    match_summary = processor.get_match_summary()
    print("\n=== Match Summary ===")
    print(match_summary)
    
    # Get and display match context
    context = processor.get_match_context()
    print("\n=== Match Context ===")
    for key, value in context.items():
        print(f"{key}: {value}")
    
    # Get and display batsmen information
    batsmen = processor.get_batsmen_info()
    print("\n=== Current Batsmen ===")
    for batsman in batsmen:
        print(f"{batsman['name']}: {batsman['runs']} runs from {batsman['balls']} balls (SR: {batsman['strike_rate']})")
    
    # Get and display bowlers information
    bowlers = processor.get_bowlers_info()
    print("\n=== Current Bowlers ===")
    for bowler in bowlers:
        print(f"{bowler['name']}: {bowler['wickets']}/{bowler['runs']} from {bowler['overs']} overs (Economy: {bowler['economy']})")
    
    # Get and display recent commentary
    commentary = processor.get_recent_commentary()
    print("\n=== Recent Commentary ===")
    for ball in commentary:
        print(f"{ball['over']} - {ball['event']} - {ball['description']}")
    
    # Get formatted data for prompt
    formatted_data = processor.format_match_data_for_prompt()
    print("\n=== Formatted Data for Prompt ===")
    print(f"Match Description: {formatted_data['match_description']}")
    print(f"Match Situation: {formatted_data['match_situation']}")
    print(f"Match Summary: {formatted_data['match_summary']}")
    
    # Check for updates
    has_updates = processor.check_for_updates()
    print(f"\nHas updates since last check: {has_updates}")

if __name__ == "__main__":
    main()