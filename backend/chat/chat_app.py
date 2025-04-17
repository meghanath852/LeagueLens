# -*- coding: utf-8 -*-
"""
Streamlit frontend for interacting with the LangGraph RAG + SQL Agent API.
"""

import streamlit as st
import requests
import os
from dotenv import load_dotenv

# --- Configuration ---
load_dotenv(override=True)
# Ensure this URL points to your running FastAPI backend
API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8001") # Default if not in .env
ASK_ENDPOINT = f"{API_BASE_URL}/ask"
REQUEST_TIMEOUT = 180 # Timeout for API request in seconds (RAG can be slow)

# --- Streamlit Page Setup ---
st.set_page_config(
    page_title="RAG + SQL Agent Q&A",
    layout="centered",
    initial_sidebar_state="auto",
)

# --- Sidebar ---
st.sidebar.title("About")
st.sidebar.info(
    """
    This app demonstrates a Retrieval-Augmented Generation (RAG) agent
    that uses both a vector store (via Pathway) for general knowledge
    and a SQL database (PostgreSQL) for structured data (e.g., cricket stats).

    Enter a question, and the agent will try to answer it by:
    1. Checking if the SQL database is relevant.
    2. Querying the SQL database if needed.
    3. Searching the vector store.
    4. Synthesizing an answer using an LLM based on the gathered information.
    """
)
st.sidebar.markdown("---")
st.sidebar.markdown(
    """
    **Powered by:**
    - LangGraph
    - Pathway
    - FastAPI
    - Streamlit
    - OpenAI
    - PostgreSQL
    """
)

# --- Main Interface ---
st.title("Ask the RAG + SQL Agent 🧠📄🏏")
st.write("Enter your question below. The agent will use its knowledge sources to find the best answer.")

# --- User Input ---
user_question = st.text_input(
    "Your Question:",
    placeholder="e.g., How does self-RAG work? OR How many runs did MS Dhoni score?",
    key="user_question_input"
)

# --- Submit Button and API Call Logic ---
if st.button("Get Answer", key="submit_button"):
    if user_question and user_question.strip():
        st.markdown("---")
        # Show spinner while processing
        with st.spinner("Thinking... The agent is processing your question..."):
            try:
                # Prepare the request payload
                payload = {"question": user_question}

                # Make the POST request to the FastAPI backend
                response = requests.post(
                    ASK_ENDPOINT,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=REQUEST_TIMEOUT
                )

                # Process the response
                if response.status_code == 200:
                    data = response.json()
                    answer = data.get("answer")
                    error = data.get("error")

                    if answer:
                        st.success("Answer:")
                        st.markdown(answer) # Use markdown for better formatting
                    elif error:
                        st.warning(f"Agent encountered an issue: {error}")
                    else:
                        st.warning("Received a response, but no answer or error was found.")

                else:
                    # Handle non-200 responses
                    error_detail = "Unknown error"
                    try:
                        # Try to get more specific error from response body
                        error_detail = response.json().get("detail", response.text)
                    except requests.exceptions.JSONDecodeError:
                        error_detail = response.text # Use raw text if not JSON
                    st.error(f"API Request Failed (Status Code: {response.status_code}): {error_detail}")

            except requests.exceptions.ConnectionError:
                st.error(f"Connection Error: Could not connect to the API at {API_BASE_URL}. Is the backend running?")
            except requests.exceptions.Timeout:
                st.error(f"Request Timed Out: The API took too long to respond (>{REQUEST_TIMEOUT}s). The question might be complex.")
            except requests.exceptions.RequestException as e:
                st.error(f"An unexpected error occurred during the API request: {e}")
            except Exception as e:
                 st.error(f"An unexpected error occurred in the Streamlit app: {e}")
                 st.exception(e) # Show traceback for debugging

    else:
        st.warning("Please enter a question.")

# --- Optional: Add a clear button ---
if st.button("Clear", key="clear_button"):
    # Rerun the script to clear state (simplest way in Streamlit)
    st.rerun()