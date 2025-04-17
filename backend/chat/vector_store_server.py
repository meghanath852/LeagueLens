# -*- coding: utf-8 -*-
"""
Pathway Vector Store Server Setup and Runner.

This script sets up and runs the Pathway VectorStoreServer,
indexing documents from the specified data path.
It should be run first and kept running in the background
for the LangGraph agent to connect to.
"""

import os
import re
import time
import threading
from urllib.parse import urlparse

# LangChain Community loader (only for ingestion helper)
from langchain_community.document_loaders import WebBaseLoader

# Pathway imports
import pathway as pw
from pathway.xpacks.llm.vector_store import VectorStoreServer, VectorStoreClient
from pathway.xpacks.llm import (
    embedders,
    llms,
    parsers,
    splitters,
)
from pathway.udfs import DiskCache

# Pretty printing
from pprint import pprint

# === Configuration ===

# Replace with your actual OpenAI API key or use environment variables
# WARNING: Avoid hardcoding API keys in production code. Use environment variables.
OPENAI_API_KEY = "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" # Replace with your key
if OPENAI_API_KEY == "YOUR_OPENAI_API_KEY":
    print("Warning: Replace 'YOUR_OPENAI_API_KEY' with your actual OpenAI API key.")
    # Attempt to get from environment if not replaced
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
    if not OPENAI_API_KEY:
        raise ValueError("OpenAI API Key not set. Please set the OPENAI_API_KEY environment variable or replace the placeholder in the script.")

os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY


# Folder to store downloaded documents
DATA_PATH = "./data"
os.makedirs(DATA_PATH, exist_ok=True)

# Host and port for the Pathway RAG app
PATHWAY_HOST: str = "0.0.0.0"
PATHWAY_PORT: int = 8000

# === Helper Functions for Web Scraping ===

def load_page_content(url: str) -> str:
    """Load web page content with Langchain utilities."""
    loader = WebBaseLoader(url)
    # Handle potential loading errors
    try:
        docs = loader.load()
        if docs:
            return docs[0].page_content
    except Exception as e:
        print(f"Error loading content from {url}: {e}")
    return ""


def ingest_webpage(url: str, data_path: str) -> None:
    """Save a webpage to local data_path folder."""
    print(f"Ingesting webpage: {url}")
    text_content = load_page_content(url)
    if not text_content:
        print(f"Warning: Could not load content from {url}")
        return

    parsed_url = urlparse(url)
    # Sanitize filename
    hostname = re.sub(r'[^\w\-.]', '_', parsed_url.hostname or "")
    path = re.sub(r'[^\w\-./]', '_', parsed_url.path or "")
    # Ensure path doesn't start or end with problematic characters
    path = path.strip('_').strip('.')
    if not path: # Handle cases like domain root
        file_name = hostname + "_index.txt"
    else:
        file_name = hostname + "_" + path.replace("/", "_").replace("\\", "_") + ".txt"

    file_path = os.path.join(data_path, file_name)

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(text_content)
        print(f"Saved webpage content to: {file_path}")
    except Exception as e:
        print(f"Error writing file {file_path}: {e}")


def check_server_running(host: str, port: int) -> bool:
    """
    Checks if a Pathway vector store server is already running at the specified host and port.
    
    Args:
        host: The host address where the server should be running
        port: The port number where the server should be running
        
    Returns:
        bool: True if a server is running and responding, False otherwise
    """
    print(f"Checking if a vector store server is already running at {host}:{port}...")
    
    try:
        # Try to connect to the server
        client = VectorStoreClient(host, port)
        
        # Try to get the list of indexed files to verify it's responding properly
        files = client.get_input_files()
        
        print(f"Server found at {host}:{port} with {len(files)} indexed files:")
        pprint(files)
        
        # Try a simple query to ensure it's fully functional
        test_query = "test query"
        results = client.query(test_query)
        print(f"Server query test successful, returned {len(results)} results.")
        
        return True
        
    except Exception as e:
        print(f"No running server found at {host}:{port}: {e}")
        return False


# === Main Execution Block ===

def run_server():
    """Sets up and runs the Pathway VectorStoreServer."""
    
    # First check if a server is already running
    if check_server_running(PATHWAY_HOST, PATHWAY_PORT):
        print(f"A Pathway Vector Store server is already running at {PATHWAY_HOST}:{PATHWAY_PORT}.")
        print("Using the existing server instance. No need to start a new one.")
        return threading.Thread()  # Return a dummy thread that's already "running"

    # === Download Source Document ===
    print("Downloading Self-RAG paper content...")
    ingest_webpage("https://arxiv.org/html/2310.11511", DATA_PATH)
    print("-" * 30)


    # === Build the Pathway Indexing Pipeline ===

    print("Setting up Pathway indexing pipeline...")
    # Read the text files under the data folder
    # Pathway can also read from Google Drive, Sharepoint, etc.
    # See connectors documentation: https://pathway.com/developers/user-guide/connect/pathway-connectors
    try:
        folder_reader = pw.io.fs.read(
            path=f"{DATA_PATH}/*.txt",
            format="binary",
            with_metadata=True,
            mode="streaming", # Use streaming for potential updates
            refresh_interval=5, # Check for new files every 5 seconds
        )
    except Exception as e:
        print(f"Error setting up file reader for path '{DATA_PATH}/*.txt': {e}")
        print("Please ensure the data directory exists and contains .txt files.")
        return None # Indicate failure

    # List of data sources to be indexed
    sources = [folder_reader]

    # Define the document processing steps
    unstructured_parser = parsers.UnstructuredParser()
    token_splitter = splitters.TokenCountSplitter(min_tokens=150, max_tokens=450)
    openai_embedder = embedders.OpenAIEmbedder(cache_strategy=DiskCache()) # Add caching

    # Setup the VectorStoreServer
    vector_server = VectorStoreServer(
        *sources,
        embedder=openai_embedder,
        splitter=token_splitter,
        parser=unstructured_parser,
    )

    # Deploy the vector store locally in a separate thread
    print(f"Starting Pathway VectorStoreServer on {PATHWAY_HOST}:{PATHWAY_PORT}...")
    server_thread = vector_server.run_server(
        PATHWAY_HOST,
        PATHWAY_PORT,
        threaded=True,
        with_cache=True # Enable caching for potentially faster restarts/updates
    )
    print("Pathway VectorStoreServer thread started.")

    # Allow some time for the server to start and index initial documents
    print("Waiting for server to initialize and index documents (approx 10s)...")
    time.sleep(10) # Adjust sleep time if needed based on document size/count
    print("Server should be ready.")

    return server_thread # Return the thread object

if __name__ == "__main__":
    server_thread = run_server()

    if server_thread and server_thread.is_alive():
        print("\nPathway server is running. Press Ctrl+C to stop.")
        try:
            # Keep the main thread alive to allow the server thread to run
            server_thread.join()
        except KeyboardInterrupt:
            print("\nStopping Pathway server...")
            # Note: Graceful shutdown of the Pathway server thread might require
            # more specific logic depending on the Pathway version/implementation.
            # This KeyboardInterrupt primarily stops the main thread waiting.
            # The server thread might need to be managed or might exit on its own.
            print("Server shutdown initiated.")
    else:
        print("\nNo new server was started. Either using an existing server or failed to start.")