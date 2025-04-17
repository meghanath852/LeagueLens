#!/usr/bin/env python3
import time
import logging
import os
import sys
import json
from datetime import datetime
from colorama import init, Fore, Style
import threading
from dotenv import load_dotenv

# Load environment variables from .env if not already loaded

load_dotenv(override=True)
    
from data_processor import MatchDataProcessor
from commentary_generator import CommentaryGenerator
from elevenlabs import stream, ElevenLabs

# Initialize colorama
init()

# Function to get the first match ID from data_live.json
def get_match_id():
    try:
        data_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data_live.json")
        with open(data_file, "r") as f:
            data = json.load(f)
        return list(data.keys())[0]
    except Exception as e:
        logging.error(f"Error getting match ID from data_live.json: {e}")
        return "1473470"  # Fallback to default ID if there's an error

# Get match ID from the first key in data_live.json
MATCH_ID = get_match_id()
COMMENTARY_FILE = "commentary_history.json"
DEFAULT_INTERVAL = 10  # Default seconds between commentary generation
MIN_INTERVAL = 0  # Minimum interval between commentaries

# Commentary provider and model settings - get from environment or use defaults
PROVIDER = os.environ.get("COMMENTARY_PROVIDER", "openai")  # Default to OpenAI
MODEL_NAME = os.environ.get("COMMENTARY_MODEL", "gpt-4o-mini")  # Default to GPT-4o-mini

# Eleven Labs API key - Use environment variable from .env or fallback
ELEVEN_API_KEY = os.environ.get("ELEVEN_API_KEY")
VOICE_ID = "JJQDkHrp6uKU5Vk0WKhY"  # Default voice ID
MODEL_ID = "eleven_multilingual_v2"  # Default model ID

# Setup logging
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"logs/commentary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("cricket_commentary")

# Initialize ElevenLabs client
try:
    eleven = ElevenLabs(api_key=ELEVEN_API_KEY)
    logger.info("ElevenLabs client initialized")
except Exception as e:
    logger.error(f"Error initializing ElevenLabs client: {e}")
    logger.warning("Text-to-speech functionality may not work properly")
    eleven = None

def display_commentary(commentary, timestamp):
    """Display commentary with colorful formatting"""
    print("\n" + "="*80)
    print(f"\n{Fore.YELLOW}[{timestamp}]{Style.RESET_ALL} {Fore.CYAN}COMMENTARY:{Style.RESET_ALL}")
    print(f"{Fore.WHITE}{commentary}{Style.RESET_ALL}")
    print("\n" + "="*80 + "\n")

def play_audio_in_thread(audio_stream):
    """Play audio in a separate thread"""
    try:
        stream(audio_stream)
    except Exception as e:
        logger.error(f"Error during audio streaming: {e}")

def speak_commentary(commentary):
    """Convert text to speech and start playing it in a thread"""
    if not eleven:
        logger.warning("ElevenLabs client not available, skipping TTS")
        return DEFAULT_INTERVAL
        
    try:
        logger.info("Converting commentary to speech...")
        audio_stream = eleven.text_to_speech.convert_as_stream(
            text=commentary,
            voice_id=VOICE_ID,
            model_id=MODEL_ID,
        )
        
        # Calculate audio duration (approximate)
        # Assuming average speaking rate of 150 words per minute
        words = len(commentary.split())
        estimated_duration = (words / 150) * 60  # in seconds
        
        # Start streaming the audio in a separate thread
        logger.info(f"Starting audio playback (estimated duration: {estimated_duration:.1f}s)")
        audio_thread = threading.Thread(target=play_audio_in_thread, args=(audio_stream,))
        audio_thread.daemon = True
        audio_thread.start()
        
        return estimated_duration
    except Exception as e:
        logger.error(f"Error in text-to-speech: {e}")
        return DEFAULT_INTERVAL

def main():
    """Main function to run the commentary generator"""
    logger.info(f"Starting cricket commentary generator with TTS using {PROVIDER} provider and {MODEL_NAME} model")
    
    # Initialize the data processor and commentary generator
    try:
        data_processor = MatchDataProcessor(MATCH_ID)
    except Exception as e:
        logger.error(f"Failed to initialize data processor: {e}")
        return
    
    # Get OpenAI API key from environment if using OpenAI
    openai_api_key = None
    if PROVIDER == "openai":
        openai_api_key = os.environ.get("OPENAI_API_KEY")
        if not openai_api_key or openai_api_key == "your_openai_api_key_here":
            logger.error("OpenAI API key not properly set in .env file or environment")
            logger.error("Please set a valid API key in the .env file or environment")
            return
    
    # Initialize the commentary generator with the appropriate provider and model
    try:
        generator = CommentaryGenerator(
            model_name=MODEL_NAME, 
            commentary_file=COMMENTARY_FILE,
            provider=PROVIDER,
            openai_api_key=openai_api_key
        )
        logger.info(f"Commentary generator initialized with {PROVIDER} provider")
    except Exception as e:
        logger.error(f"Failed to initialize commentary generator: {e}")
        return
    
    try:
        while True:
            # Load the latest match data
            match_data = data_processor.load_data()
            if not match_data:
                logger.error("Failed to load match data, retrying in 10 seconds")
                time.sleep(DEFAULT_INTERVAL)
                continue
            
            # Format match data for LLM prompt
            prompt_data = data_processor.format_match_data_for_prompt()
            
            # Generate new commentary
            logger.info("Generating new commentary...")
            commentary = generator.generate_commentary(prompt_data)
            
            # Display the commentary
            current_time = datetime.now().strftime('%H:%M:%S')
            display_commentary(commentary, current_time)
            
            # Save the commentary
            generator.save_commentary(commentary)
            
            # Start speaking the commentary and get estimated duration
            audio_duration = speak_commentary(commentary)
            
            # Calculate wait time (audio duration minus 1 second, with minimum threshold)
            wait_time = max(audio_duration, MIN_INTERVAL)
            
            # Wait before generating the next commentary
            # We immediately start preparing the next commentary without waiting for audio to finish
            logger.info(f"Waiting for {wait_time:.1f} seconds before next commentary")
            time.sleep(wait_time)
    
    except KeyboardInterrupt:
        logger.info("Commentary generator stopped by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        logger.exception("Full traceback:")

if __name__ == "__main__":
    main() 