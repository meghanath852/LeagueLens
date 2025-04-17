#!/usr/bin/env python3
import json
import logging
import os
from datetime import datetime
from ollama import Client
from openai import OpenAI

logger = logging.getLogger("cricket_commentary.generator")

class CommentaryGenerator:
    """Generate cricket commentary using Llama3 via Ollama or GPT-4o-mini via OpenAI"""
    
    def __init__(self, model_name="llama3", host="http://localhost:11434", commentary_file="commentary_history.json", 
                 provider="ollama", openai_api_key=None):
        """Initialize the commentary generator"""
        self.model_name = model_name
        self.provider = provider
        self.commentary_file = commentary_file
        
        if provider == "ollama":
            self.client = Client(host=host)
            # Test connection to Ollama
            try:
                models = self.client.list()
                # Check if model is available, using flexible matching for tag specification
                model_base = model_name.split(':')[0] if ':' in model_name else model_name
                if not any(model_base in model["name"] for model in models["models"]):
                    logger.warning(f"Model {model_name} not found in Ollama. Make sure to pull it with: ollama pull {model_name}")
            except Exception as e:
                logger.error(f"Failed to connect to Ollama at {host}: {e}")
                logger.info("Make sure Ollama is running and accessible")
        elif provider == "openai":
            if not openai_api_key:
                openai_api_key = os.environ.get("OPENAI_API_KEY")
                if not openai_api_key:
                    logger.error("No OpenAI API key provided. Set via parameter or OPENAI_API_KEY environment variable.")
            self.client = OpenAI(api_key=openai_api_key)
            # Default to gpt-4o-mini if not specified for OpenAI provider
            if model_name == "llama3":
                self.model_name = "gpt-4o-mini"
                logger.info(f"Using default OpenAI model: {self.model_name}")
        else:
            raise ValueError(f"Unsupported provider: {provider}. Use 'ollama' or 'openai'.")
    
    def generate_commentary(self, prompt_data, max_tokens=250, temperature=0.7):
        """Generate commentary using the LLM"""
        prompt = self._build_prompt(prompt_data)
        
        try:
            logger.info(f"Generating commentary with {self.model_name} via {self.provider}...")
            
            if self.provider == "ollama":
                # First try with options
                try:
                    response = self.client.generate(
                        model=self.model_name,
                        prompt=prompt,
                        options={
                            "num_predict": max_tokens,
                            "temperature": temperature
                        }
                    )
                except TypeError:
                    # Fallback to simplest form if options aren't supported
                    logger.warning("Falling back to basic generate method without options")
                    response = self.client.generate(
                        model=self.model_name,
                        prompt=prompt
                    )
                    
                commentary = response['response'].strip()
            
            elif self.provider == "openai":
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": "You are an expert cricket commentator providing brief, factual commentary."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=max_tokens,
                    temperature=temperature
                )
                commentary = response.choices[0].message.content.strip()
                
            logger.info(f"Generated commentary ({len(commentary.split())} words)")
            return commentary
        except Exception as e:
            logger.error(f"Error generating commentary: {e}")
            return "Commentary unavailable at this time."
    
    def _build_prompt(self, data):
        """Build a prompt for the LLM based on match data"""
        prompt = f"""
You are an expert cricket commentator. Generate a natural and engaging 1-2 sentences commentary for the current state of the match.

IMPORTANT: Base your commentary ONLY on the information provided below. DO NOT make up or hallucinate any statistics, events, player names, or match details that are not explicitly mentioned in this data.

Match: {data.get('match_description', 'Cricket Match')}
Current situation: {data.get('match_situation', '')}
Match summary: {data.get('match_summary', '')}

Batting information:
{data.get('batting_info', 'No batting information available')}

Bowling information:
{data.get('bowling_info', 'No bowling information available')}

Recent ball-by-ball commentary:
{data.get('recent_commentary', 'No recent commentary available')}

Previous commentaries:
{self._get_recent_commentaries()}

Instructions:
1. Create a brief, factual commentary using ONLY the information provided above, maintain continuity of the commentary based on the previous commentaries
2. Focus on the current match situation, recent events, and player performances shown in the data
3. Use a natural, engaging cricket commentator style
4. Do not repeat previous commentaries
5. Do not invent or hallucinate any facts, statistics, or events
6. Keep it to 1-2 sentences only
7. No need for any introduction or sign-off phrases

Just provide the commentary text itself, nothing else.
"""
        return prompt
    
    def save_commentary(self, commentary):
        """Save the generated commentary to history file"""
        try:
            # Load existing commentaries if file exists
            existing_commentaries = []
            if os.path.exists(self.commentary_file):
                with open(self.commentary_file, "r") as f:
                    existing_commentaries = json.load(f)
            
            # Add new commentary with timestamp
            existing_commentaries.append({
                "timestamp": datetime.now().isoformat(),
                "commentary": commentary
            })
            
            # Save back to file
            with open(self.commentary_file, "w") as f:
                json.dump(existing_commentaries, f, indent=2)
                
            logger.info("Commentary saved to history file")
            return True
        except Exception as e:
            logger.error(f"Error saving commentary: {e}")
            return False
    
    def _get_recent_commentaries(self, limit=5):
        """Load the recent commentary history"""
        commentary_text = ""
        try:
            if not os.path.exists(self.commentary_file):
                return commentary_text
                
            with open(self.commentary_file, "r") as f:
                commentaries = json.load(f)
                # Get the most recent commentaries up to the limit
                recent = commentaries[-limit:] if len(commentaries) >= limit else commentaries
                
                for idx, entry in enumerate(recent):
                    timestamp = datetime.fromisoformat(entry["timestamp"]).strftime("%H:%M:%S")
                    commentary_text += f"{timestamp}: {entry['commentary']}\n\n"
                    
            return commentary_text
        except Exception as e:
            logger.error(f"Error loading commentary history: {e}")
            return commentary_text 