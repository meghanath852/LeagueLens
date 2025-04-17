# -*- coding: utf-8 -*-
"""
FastAPI backend to serve the LangGraph RAG + SQL Agent.
"""

import os
import sys
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
from dotenv import load_dotenv

# --- Initialize Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Load Environment Variables ---
load_dotenv(override=True)
logger.info("Environment variables loaded.")

# --- Import and Initialize Agent Components ---
# IMPORTANT: These imports trigger the setup logic within the imported files.
try:
    logger.info("Importing SQL setup...")
    import sql_setup
    sql_engine = sql_setup.setup_database(csv_filepath='deliveries.csv')
    if sql_engine is None:
        logger.error("Database setup failed during API initialization.")
        # Decide if API should still start or exit
        # sys.exit("API startup failed: Database connection error.")
    else:
        logger.info("Database setup completed successfully.")
    
    logger.info("Initializing live match data processor...")
    from live_match_processor import LiveMatchRelevanceChecker
    live_match_checker = LiveMatchRelevanceChecker()
    has_live_match_data = live_match_checker.check_for_live_data()
    if has_live_match_data:
        logger.info("Live cricket match data is available for processing.")
    else:
        logger.warning("No live cricket match data found.")

    logger.info("Importing LangGraph agent components...")
    # This import will define components and might try Pathway connection
    from langgraph_agent_sql import compile_graph, GraphState, retriever, initialize_state # Import necessary parts

    # --- Compile the LangGraph Agent ---
    logger.info("Compiling LangGraph agent...")
    compiled_app = compile_graph()
    if compiled_app:
        logger.info("LangGraph agent compiled successfully.")
    else:
        logger.error("LangGraph agent compilation failed.")
        # Decide if API should still start or exit
        # sys.exit("API startup failed: LangGraph compilation error.")

    # --- Optional: Check Pathway Connection Status ---
    if retriever:
        logger.info("Pathway retriever seems available.")
    else:
        logger.warning("Pathway retriever is NOT available. Vector search will be skipped.")

except ImportError as e:
    logger.exception(f"Failed to import necessary modules: {e}")
    sys.exit(f"API startup failed: Missing module - {e}")
except Exception as e:
    logger.exception(f"An unexpected error occurred during API initialization: {e}")
    sys.exit(f"API startup failed: Initialization error - {e}")


# --- FastAPI App Initialization ---
api = FastAPI(
    title="LangGraph RAG + SQL Agent API",
    description="API endpoint to interact with the LangGraph agent that uses both vector search and SQL database.",
    version="1.0.0",
)

# --- Request and Response Models ---
class QueryRequest(BaseModel):
    question: str

class AnswerResponse(BaseModel):
    answer: str | None = None
    error: str | None = None

# --- API Endpoints ---

@api.get("/", summary="API Root/Health Check")
async def read_root():
    """Basic health check endpoint."""
    return {"status": "LangGraph Agent API is running"}

# Inside main_api.py

@api.post("/ask", response_model=AnswerResponse, summary="Ask the RAG Agent")
async def ask_agent(request: QueryRequest):
    """
    Receives a question, runs it through the LangGraph agent,
    and returns the generated answer or an error.
    """
    question = request.question
    logger.info(f"Received question: {question}")

    if not compiled_app:
        logger.error("Agent not compiled or available.")
        raise HTTPException(status_code=503, detail="Agent service is unavailable.")

    if not question or not question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    try:
        # Prepare initial state for the agent
        inputs = initialize_state()
        inputs["question"] = question
        final_state_snapshot = {} # To capture the final state pieces

        logger.info("Invoking LangGraph agent...")
        final_state_snapshot = compiled_app.invoke(inputs, {"recursion_limit": 15})
        logger.info("Agent invocation complete.")

        # --- Start Debugging Block ---
        # Log the type and content of the returned state
        logger.info(f"[DEBUG] Type of final_state_snapshot: {type(final_state_snapshot)}")
        if isinstance(final_state_snapshot, dict):
            logger.info(f"[DEBUG] Keys in final_state_snapshot: {list(final_state_snapshot.keys())}")
            # Attempt to log the full dictionary structure carefully
            import json
            try:
                # Convert Documents to string representations for logging if present
                loggable_state = {}
                for key, value in final_state_snapshot.items():
                    if key == 'documents' and isinstance(value, list):
                        loggable_state[key] = [f"Document(page_content='{str(doc.page_content)[:100]}...', metadata={doc.metadata})" for doc in value]
                    else:
                        loggable_state[key] = value

                logger.info(f"[DEBUG] Full final_state_snapshot (loggable):\n{json.dumps(loggable_state, indent=2, default=str)}")
            except Exception as log_err:
                logger.error(f"[DEBUG] Error creating loggable state: {log_err}")
                logger.info(f"[DEBUG] Raw final_state_snapshot: {final_state_snapshot}") # Log raw as fallback
        else:
            logger.info(f"[DEBUG] final_state_snapshot is not a dict: {final_state_snapshot}")
        # --- End Debugging Block ---


        # Extract the final answer
        final_answer = None
        if isinstance(final_state_snapshot, dict):
            # Directly access the 'generation' state attribute from the final state dict
            final_answer = final_state_snapshot.get('generation')

            if final_answer is not None: # Check for None explicitly
                 logger.info("Successfully extracted 'generation' key.")
            else:
                 logger.warning("Could not find 'generation' key OR its value was None in the final state dictionary.")

        if final_answer:
            logger.info(f"Agent generated answer (length: {len(final_answer)}).")
            return AnswerResponse(answer=final_answer)
        else:
            # This warning should now only trigger if 'generation' is genuinely missing or None
            logger.warning("Agent finished but no final answer could be extracted (final_answer is None or empty).")
            error_msg = "Agent finished processing, but could not determine a final answer."
            return AnswerResponse(answer=None, error=error_msg)

    except Exception as e:
        logger.exception(f"Error during agent execution for question '{question}': {e}")
        raise HTTPException(status_code=500, detail=f"An error occurred while processing the question: {str(e)}")

# --- Run the API using Uvicorn ---
if __name__ == "__main__":
    # Use port 8001 to avoid conflict with Pathway (default 8000)
    port = int(os.environ.get("PORT", 8001))
    host = os.environ.get("HOST", "0.0.0.0")
    logger.info(f"Starting FastAPI server on {host}:{port}...")
    uvicorn.run(api, host=host, port=port)