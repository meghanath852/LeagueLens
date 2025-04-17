#!/usr/bin/env python3
"""
Cricket Commentary Generator
============================

This script launches a continuous commentary generator for cricket match data 
using GPT-4o-mini from OpenAI or Llama3 model hosted in Ollama and ElevenLabs for text-to-speech.

Requirements:
- OpenAI API key (can be set in .env file or OPENAI_API_KEY environment variable) OR
- Ollama service should be running with the Llama3 model pulled
- ElevenLabs API key (can be set in .env file or ELEVEN_API_KEY environment variable)
- Python dependencies from requirements.txt must be installed

Usage:
    python run_commentary.py
"""

import sys
import os
import subprocess
import time
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(override=True)

def check_openai_api_key():
    """Check if OpenAI API key is available"""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key or api_key == "your_openai_api_key_here":
        print("\nWARNING: OPENAI_API_KEY not properly set in .env file or environment.")
        print("Will try using Ollama instead.")
        return False
    return True

def check_ollama():
    """Check if Ollama is running"""
    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags")
        if response.status_code == 200:
            return True
        return False
    except:
        return False

def check_model():
    """Check if llama3 model is available in Ollama"""
    try:
        import ollama
        client = ollama.Client()
        models = client.list()
        # Check for the model name with flexible matching
        model_name = "llama3"
        model_base = model_name.split(':')[0] if ':' in model_name else model_name
        return any(model_base in model["name"] for model in models["models"])
    except:
        return False

def check_elevenlabs_api_key():
    """Check if ElevenLabs API key is available"""
    api_key = os.environ.get("ELEVEN_API_KEY")
    if not api_key or api_key == "your_elevenlabs_api_key_here":
        print("\nWARNING: ELEVEN_API_KEY not properly set in .env file or environment.")
        print("Text-to-speech will use the default API key from the code.")
        print("For production use, set your own API key in the .env file or with:")
        print("    export ELEVEN_API_KEY=your_api_key_here")
        return False
    return True

def main():
    """Main function to start the commentary generator"""
    print("\n" + "="*80)
    print("CRICKET COMMENTARY GENERATOR WITH TEXT-TO-SPEECH")
    print("="*80 + "\n")
    
    # Check if Python dependencies are installed
    try:
        import openai
        import colorama
        import elevenlabs
    except ImportError:
        print("Required dependencies not found. Installing from requirements.txt...")
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("Dependencies installed.")
    
    # Get provider and model from .env or use defaults
    provider = os.environ.get("COMMENTARY_PROVIDER", "openai")
    model_name = os.environ.get("COMMENTARY_MODEL", "gpt-4o-mini")
    
    print(f"Configuration from .env: Provider={provider}, Model={model_name}")
    
    # Check for OpenAI API key if OpenAI is the provider
    if provider == "openai":
        print("Checking for OpenAI API key...")
        use_openai = check_openai_api_key()
        
        if not use_openai:
            print("OpenAI API key not found. Checking Ollama service...")
            # Check if Ollama is running
            if not check_ollama():
                print("\nERROR: OpenAI API key not set and Ollama service is not running!")
                print("Please either:")
                print("1. Set your OpenAI API key in .env file or: export OPENAI_API_KEY=your_key_here")
                print("2. Start Ollama with: ollama serve")
                print("\nThen run this script again.")
                return
            
            # Check if Llama3 model is available
            print("Checking for llama3 model...")
            if not check_model():
                print("\nllama3 model not found in Ollama. Pulling the model...")
                print("This might take a while for the first time...")
                subprocess.run(["ollama", "pull", "llama3"])
            
            # Use Ollama as fallback
            provider = "ollama"
            model_name = "llama3"
            print("\nUsing Ollama with Llama3 model.")
        else:
            print("\nUsing OpenAI with GPT-4o-mini model.")
    # If provider is explicitly set to ollama, check ollama setup
    elif provider == "ollama":
        print("Checking Ollama service...")
        if not check_ollama():
            print("\nERROR: Ollama service is not running!")
            print("Please start Ollama with: ollama serve")
            print("\nThen run this script again.")
            return
        
        # Check if Llama3 model is available
        print("Checking for llama3 model...")
        if not check_model():
            print("\nllama3 model not found in Ollama. Pulling the model...")
            print("This might take a while for the first time...")
            subprocess.run(["ollama", "pull", "llama3"])
    
    # Check for ElevenLabs API key
    print("Checking for ElevenLabs API key...")
    check_elevenlabs_api_key()
    
    # Add src directory to path
    sys.path.append(os.path.join(os.path.dirname(__file__), "src"))
    
    # Set provider and model environment variables
    os.environ["COMMENTARY_PROVIDER"] = provider
    os.environ["COMMENTARY_MODEL"] = model_name
    
    # Start the commentary generator
    print("\nStarting cricket commentary generator with text-to-speech...")
    print("Press Ctrl+C to stop.\n")
    time.sleep(1)
    
    try:
        from src.main import main
        main()
    except KeyboardInterrupt:
        print("\nCommentary generator stopped by user.")
    except Exception as e:
        print(f"\nError: {e}")
        print("Please check the logs in the logs directory for more details.")

if __name__ == "__main__":
    main() 