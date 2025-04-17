#!/usr/bin/env python3
import json
import logging
import os
from langchain_core.documents import Document
from src.data_processor import MatchDataProcessor

logger = logging.getLogger("cricket_commentary.live_match_processor")

class LiveMatchRelevanceChecker:
    """Check if live cricket match data is relevant to a user query"""
    
    def __init__(self, match_id=None, data_file=None):
        # Use relative path for data file
        if data_file is None:
            self.data_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data_live.json")
        else:
            self.data_file = data_file
        
        # Get match ID from the first key in data_live.json if not provided
        if match_id is None:
            self.match_id = self._get_first_match_id()
        else:
            self.match_id = match_id
            
        self.processor = MatchDataProcessor(self.match_id, self.data_file)
    
    def _get_first_match_id(self):
        """Get the first match ID from data_live.json"""
        try:
            with open(self.data_file, "r") as f:
                data = json.load(f)
            return list(data.keys())[0]
        except Exception as e:
            logger.error(f"Error getting match ID from data_live.json: {e}")
            return "1473470"  # Fallback to default ID if there's an error
    
    def get_match_data_document(self):
        """Process the live match data and return as a Document object"""
        try:
            # Load raw match data first
            raw_data = self.processor.load_data()
            
            # Extract team names and scores like we do in app.py
            match_data = {}
            
            # Get team names
            team1_name = raw_data.get("match", {}).get("team1_name", "Team 1")
            team2_name = raw_data.get("match", {}).get("team2_name", "Team 2")
            team1_id = raw_data.get("match", {}).get("team1_id")
            team2_id = raw_data.get("match", {}).get("team2_id")
            
            # Determine which team is batting
            team_batting = None
            current_innings = raw_data.get("centre", {}).get("common", {}).get("innings", {})
            
            # Try multiple methods to identify the batting team
            if "batting_team_id" in current_innings:
                current_batting_team_id = current_innings.get("batting_team_id")
                if str(current_batting_team_id) == str(team1_id):
                    team_batting = "team1"
                elif str(current_batting_team_id) == str(team2_id):
                    team_batting = "team2"
            
            # If we still couldn't determine, try other methods or use a default
            if not team_batting:
                team_batting = "team2"  # Default
            
            # For our document, we want to consistently use:
            # - Sunrisers (team2_name) as Team 1 (completed 20 overs)
            # - Mumbai Indians (team1_name) as Team 2 (batting)
            match_data["team1"] = team2_name  # Sunrisers (completed innings)
            match_data["team2"] = team1_name  # Mumbai Indians (batting)
            
            # Get scores for both teams
            team1_score = "Yet to bat"
            team2_score = "Yet to bat"
            
            # Process completed innings
            for inning in raw_data.get("innings", []):
                batting_team_id = inning.get("batting_team_id", "")
                runs = inning.get("runs", "0")
                wickets = inning.get("wickets", "0")
                overs = inning.get("overs", "0.0")
                event = inning.get("event", "")
                
                if event == 5 or inning.get("event_name", "") == "complete":
                    # Format for completed innings
                    formatted_score = f"{runs}/{wickets} ({overs} ov)"
                    
                    if str(batting_team_id) == str(team1_id):
                        team1_score = formatted_score
                    elif str(batting_team_id) == str(team2_id):
                        team2_score = formatted_score
            
            # Process current innings
            if current_innings:
                current_batting_team_id = current_innings.get("batting_team_id")
                if current_batting_team_id:
                    current_runs = current_innings.get("runs", 0)
                    current_wickets = current_innings.get("wickets", 0)
                    current_overs = current_innings.get("overs", "0.0")
                    
                    current_formatted_score = f"{current_runs}/{current_wickets} ({current_overs} ov)"
                    
                    if str(current_batting_team_id) == str(team1_id):
                        team1_score = current_formatted_score
                    elif str(current_batting_team_id) == str(team2_id):
                        team2_score = current_formatted_score
            
            # Assign scores correctly
            if team_batting == "team1":
                # If team 1 is batting (Mumbai), then for our document:
                match_data["team1_score"] = team2_score  # Sunrisers score
                match_data["team2_score"] = team1_score  # Mumbai Indians score
            else:
                # If team 2 is batting (Sunrisers), then for our document:
                match_data["team1_score"] = team2_score  # Sunrisers score
                match_data["team2_score"] = team1_score  # Mumbai Indians score
            
            # Use the MatchDataProcessor to get formatted match data for the rest
            formatted_data = self.processor.format_match_data_for_prompt()
            
            # Create a comprehensive match summary with correct team assignments
            content = f"""
Live Cricket Match Information:
------------------------------
Match: {match_data["team1"]} vs {match_data["team2"]}

Current Scores:
{match_data["team1"]}: {match_data["team1_score"]}
{match_data["team2"]}: {match_data["team2_score"]}

Match Situation:
{formatted_data['match_situation']}

Match Summary:
{formatted_data['match_summary']}

Current Batsmen:
{formatted_data['batting_info']}

Current Bowlers:
{formatted_data['bowling_info']}

Recent Commentary:
{formatted_data['recent_commentary']}
"""
            
            # Create a LangChain Document with metadata
            doc = Document(
                page_content=content,
                metadata={
                    "source": "live_cricket_match",
                    "match_id": self.match_id,
                    "content_type": "cricket_match_data",
                    "team1": match_data["team1"],
                    "team1_score": match_data["team1_score"],
                    "team2": match_data["team2"],
                    "team2_score": match_data["team2_score"]
                }
            )
            
            return doc
        
        except Exception as e:
            logger.error(f"Error processing live match data: {e}")
            return None

    def check_for_live_data(self):
        """Check if there is live match data available"""
        try:
            data = self.processor.load_data()
            return bool(data)  # Return True if data exists and is not empty
        except Exception:
            return False

def is_query_about_live_match(query, llm):
    """Determine if the query is asking about current/live match information"""
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import StrOutputParser
    
    system_prompt = """You are an expert at determining whether a user question is asking about a live or current cricket match.
    
    For questions that explicitly or implicitly ask about:
    - Current match state, score, or situation
    - Live match events or commentary
    - "Current", "ongoing", "now", or other present-tense indicators about a cricket match
    - Recent events in a match happening today or "this match"
    - Predictions or analysis about the rest of a match in progress
    
    Respond with only 'yes' if the question is likely about a current/live match, or 'no' if not.
    """
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", f"Is this query about a live or current cricket match: '{query}'")
    ])
    
    chain = prompt | llm | StrOutputParser()
    result = chain.invoke({})
    
    return result.strip().lower() == 'yes' 