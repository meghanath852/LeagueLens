# -*- coding: utf-8 -*-
"""
Cricket Q&A Vector Database Loader

This script loads cricket Q&A pairs from a CSV file and streams them to the
vector store database running on localhost:8000.
"""

import csv
import os
import time
import threading
import sys
import json
from datetime import datetime
from pathlib import Path

# For vector store client connection
from pathway.xpacks.llm.vector_store import VectorStoreClient

# Configuration
VECTOR_DB_HOST = "localhost"
VECTOR_DB_PORT = 8000

# CSV File with Q&A pairs
CSV_FILE = "cricket_qa.csv"

# Folder to store Q&A text files for vector store
DATA_PATH = "./data"
os.makedirs(DATA_PATH, exist_ok=True)

# Keep track of processed entries
PROCESSED_FILE = Path(DATA_PATH) / "processed_qa_entries.txt"

def get_processed_entries():
    """Get list of already processed entries to avoid duplicates"""
    if not PROCESSED_FILE.exists():
        return set()
    
    with open(PROCESSED_FILE, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f.readlines())

def mark_as_processed(entry_hash):
    """Mark an entry as processed"""
    with open(PROCESSED_FILE, "a", encoding="utf-8") as f:
        f.write(f"{entry_hash}\n")

def calculate_entry_hash(qa_pair):
    """Calculate a simple hash for a QA pair to identify it"""
    # Just use the first 50 chars of question as identifier
    return qa_pair.split(" : ")[0][:50].strip('"').strip()

def save_to_text_file(qa_pair, index):
    """Save a Q&A pair to a text file for vector store indexing"""
    try:
        # Extract question and answer
        parts = qa_pair.split(" : ", 1)
        if len(parts) != 2:
            print(f"Invalid format for QA pair: {qa_pair[:100]}...")
            return None
        
        question, answer = parts
        # Clean up the parts
        question = question.strip('"').strip()
        answer = answer.strip('"').strip()
        
        # Create a filename based on the question
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        safe_name = "".join(c if c.isalnum() else "_" for c in question[:30])
        filename = f"cricket_qa_{timestamp}_{safe_name}_{index}.txt"
        file_path = os.path.join(DATA_PATH, filename)
        
        # Write the content to the file
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"# Question\n{question}\n\n# Answer\n{answer}")
        
        print(f"Saved Q&A to file: {filename}")
        return file_path
    
    except Exception as e:
        print(f"Error saving Q&A to file: {e}")
        return None

def check_server_running():
    """Check if the vector store server is running"""
    print(f"Checking if vector store server is running at {VECTOR_DB_HOST}:{VECTOR_DB_PORT}...")
    
    try:
        # Try to connect to the server
        client = VectorStoreClient(VECTOR_DB_HOST, VECTOR_DB_PORT)
        
        # Try to get the list of indexed files to verify it's responding properly
        files = client.get_input_files()
        
        print(f"Server found at {VECTOR_DB_HOST}:{VECTOR_DB_PORT} with {len(files)} indexed files.")
        
        # Try a simple query to ensure it's fully functional
        test_query = "cricket"
        results = client.query(test_query)
        print(f"Server query test successful, returned {len(results)} results.")
        
        return True
        
    except Exception as e:
        print(f"No running server found at {VECTOR_DB_HOST}:{VECTOR_DB_PORT}: {e}")
        return False

def process_csv_file():
    """Process the CSV file and load new entries to the vector database"""
    if not os.path.exists(CSV_FILE):
        print(f"Error: CSV file '{CSV_FILE}' not found.")
        return
    
    # Get already processed entries
    processed_entries = get_processed_entries()
    print(f"Found {len(processed_entries)} previously processed entries.")
    
    # Read all entries from CSV
    entries_to_process = []
    try:
        with open(CSV_FILE, 'r', encoding='utf-8') as csvfile:
            csv_reader = csv.reader(csvfile)
            next(csv_reader)  # Skip header row
            
            for i, row in enumerate(csv_reader):
                if not row:
                    continue
                
                qa_pair = row[0]
                entry_hash = calculate_entry_hash(qa_pair)
                
                if entry_hash not in processed_entries:
                    entries_to_process.append((qa_pair, entry_hash, i))
    
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return
    
    print(f"Found {len(entries_to_process)} new entries to process.")
    
    # Process new entries
    for qa_pair, entry_hash, index in entries_to_process:
        # Save to text file
        file_path = save_to_text_file(qa_pair, index)
        if file_path:
            # Mark as processed
            mark_as_processed(entry_hash)
            print(f"Processed entry: {entry_hash[:30]}...")
            
            # Give the vector store server time to detect and index the new file
            time.sleep(1)
        else:
            print(f"Failed to process entry: {entry_hash[:30]}...")

def watch_for_changes():
    """Continuously watch for new entries in the CSV file"""
    print("Starting to watch for changes in the CSV file...")
    
    last_modified = os.path.getmtime(CSV_FILE) if os.path.exists(CSV_FILE) else 0
    
    while True:
        try:
            # Check if the file has been modified
            if os.path.exists(CSV_FILE):
                current_modified = os.path.getmtime(CSV_FILE)
                if current_modified > last_modified:
                    print(f"CSV file has been modified. Processing new entries...")
                    process_csv_file()
                    last_modified = current_modified
            
            # Sleep for a while before checking again
            time.sleep(10)
        
        except KeyboardInterrupt:
            print("Stopping watch for changes...")
            break
        
        except Exception as e:
            print(f"Error watching for changes: {e}")
            time.sleep(30)  # Longer sleep on error

def test_vector_store():
    """Test querying the vector store with some cricket questions"""
    try:
        client = VectorStoreClient(VECTOR_DB_HOST, VECTOR_DB_PORT)
        
        test_questions = [
            "Who won the most recent IPL match?",
            "Tell me about best bowling figures in IPL",
            "What happened in the Delhi Capitals vs Rajasthan Royals match?",
            "How did Delhi Capitals win in the Super Over?"
        ]
        
        for question in test_questions:
            print(f"\nQuerying: {question}")
            
            # Get results from the vector store
            results = client.query(question)
            
            print(f"Got {len(results)} results:")
            for i, result in enumerate(results[:3]):  # Show top 3 results
                print(f"\nResult {i+1}:")
                print(f"Score: {result.get('score', 'N/A')}")
                print(f"Content: {result.get('text', '')[:150]}...")
    
    except Exception as e:
        print(f"Error testing vector store: {e}")

def main():
    """Main function"""
    print("=" * 50)
    print("Cricket Q&A Vector Database Loader")
    print("=" * 50)
    
    # Check if vector store server is running
    if not check_server_running():
        print("Vector store server is not running. Please start it first.")
        return
    
    # Initial processing of the CSV file
    process_csv_file()
    
    # Test the vector store with some queries
    test_vector_store()
    
    # Watch for changes in the CSV file
    watch_for_changes()

if __name__ == "__main__":
    main() 