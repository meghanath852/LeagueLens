# # -*- coding: utf-8 -*-
# """
# LangGraph Agent powered by a Pathway Vector Store and integrated SQL Database.

# This script defines and runs a LangGraph agent that uses:
# 1. A Pathway VectorStoreRetriever for unstructured data.
# 2. A PostgreSQL database for structured cricket data.

# It checks question relevance for the SQL DB, generates/executes queries if relevant,
# and combines results with vector retrieval for the LLM generation.
# """

# import os
# import time
# import sys
# from typing import List, Dict, Any
# # Use Pydantic V1 specifically if needed, or just BaseModel if V2 is okay
# from pydantic.v1 import BaseModel as PydanticBaseModelV1, Field
# from dotenv import load_dotenv
# import pandas as pd
# from sqlalchemy import text

# # LangChain and LangGraph imports
# from langchain_community.vectorstores import PathwayVectorClient # For LCEL integration
# from langchain_core.prompts import ChatPromptTemplate
# # Use the aliased Pydantic V1 BaseModel for Langchain compatibility
# from langchain_core.pydantic_v1 import BaseModel as LangchainBaseModelV1
# from langchain_core.output_parsers import StrOutputParser
# from langchain_core.documents import Document # Ensure Document is imported
# from langchain_openai import ChatOpenAI
# from langchain import hub
# from langgraph.graph import END, StateGraph, START
# from typing_extensions import TypedDict

# # Pathway client import
# from pathway.xpacks.llm.vector_store import VectorStoreClient # For direct client interaction (optional checks)

# # SQL Database Setup Import
# import sql_setup # Import the setup script

# # Live Cricket Match Data Import
# from live_match_processor import LiveMatchRelevanceChecker, is_query_about_live_match

# # Pretty printing
# from pprint import pprint

# # === Configuration ===

# # Load environment variables from .env file
# load_dotenv()

# # OpenAI API Key
# OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
# if not OPENAI_API_KEY:
#     raise ValueError("OpenAI API Key not found. Please set the OPENAI_API_KEY environment variable.")
# os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY

# # Pathway Vector Store Server Configuration
# PATHWAY_HOST: str = os.environ.get("PATHWAY_HOST", "0.0.0.0")
# PATHWAY_PORT: int = int(os.environ.get("PATHWAY_PORT", 8000))

# # Database Configuration (ensure these match .env and sql_setup.py)
# DB_HOST = os.getenv("DB_HOST", "localhost")
# DB_PORT = os.getenv("DB_PORT", "5432")
# DB_USER = os.getenv("DB_USER", "postgres")
# DB_NAME = os.getenv("DB_NAME", "quicksell_rag")

# # === Initialize Database ===
# print("Initializing PostgreSQL database connection...")
# # The setup_database function returns the engine
# sql_engine = sql_setup.setup_database(csv_filepath='deliveries.csv')
# if sql_engine is None:
#     print("FATAL: Database setup failed. Exiting.")
#     sys.exit(1)
# else:
#     print(f"Successfully connected to database '{DB_NAME}' on {DB_HOST}:{DB_PORT}")
# print("-" * 30)


# # === Pathway Client and Retriever Setup ===

# print("Setting up Pathway client and LangChain retriever...")
# print(f"Attempting to connect to Pathway server at {PATHWAY_HOST}:{PATHWAY_PORT}...")

# # Allow a moment for the server to potentially be ready if just started
# time.sleep(5)

# retriever = None # Initialize retriever
# try:
#     # Create LangChain retriever via PathwayVectorClient
#     vectorstore_client_lc = PathwayVectorClient(PATHWAY_HOST, PATHWAY_PORT)
#     retriever = vectorstore_client_lc.as_retriever()
#     print("LangChain Pathway retriever created.")

#     # Test the retriever (optional check)
#     test_question = "self-RAG"
#     print(f"\nTesting Pathway retriever with question: '{test_question}'")
#     relevant_docs_vector = retriever.invoke(test_question) # Use invoke for LCEL compatibility
#     print(f"Retrieved {len(relevant_docs_vector)} documents from Pathway for test question.")

# except Exception as e:
#     print(f"\n--- WARNING ---")
#     print(f"Error connecting to or interacting with Pathway server at {PATHWAY_HOST}:{PATHWAY_PORT}: {e}")
#     print("Pathway Vector Store retrieval will be unavailable.")
#     # Allow continuation without vector store if needed, or exit:
#     # sys.exit(1)

# print("-" * 30)


# # === Initialize Live Match Data Processor ===
# print("Initializing Live Cricket Match Data Processor...")
# live_match_checker = LiveMatchRelevanceChecker()
# has_live_match_data = live_match_checker.check_for_live_data()
# if has_live_match_data:
#     print("Live cricket match data is available for processing.")
# else:
#     print("No live cricket match data found.")
# print("-" * 30)


# # === Define LangGraph Workflow Components ===

# print("Defining LangGraph components (Graders, Generators, Rewriter, SQL Helpers)...")

# # --- LLM Instances ---
# # Use consistent models where appropriate
# llm_grader = ChatOpenAI(model="gpt-4o-mini", temperature=0)
# llm_sql_helper = ChatOpenAI(model="gpt-4o-mini", temperature=0)
# llm_rewrite = ChatOpenAI(model="gpt-4o-mini", temperature=0)
# # Keep potentially different model for main generation if intended
# llm_generate = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0)

# # --- Grade Documents (Vector Store Relevance) ---
# class GradeDocuments(LangchainBaseModelV1):
#     """Binary score for relevance check on retrieved documents."""
#     binary_score: str = Field(..., description="Documents are relevant to the question, 'yes' or 'no'") # Corrected

# structured_llm_grader_docs = llm_grader.with_structured_output(GradeDocuments)
# system_grade_docs = """You are a grader assessing relevance of a retrieved document to a user question.
#     It does not need to be a stringent test. The goal is to filter out erroneous retrievals.
#     If the document contains keyword(s) or semantic meaning related to the user question, grade it as relevant.
#     Give a binary score 'yes' or 'no' score to indicate whether the document is relevant to the question."""
# grade_prompt = ChatPromptTemplate.from_messages(
#     [("system", system_grade_docs), ("human", "Retrieved document: \n\n {document} \n\n User question: {question}")]
# )
# retrieval_grader = grade_prompt | structured_llm_grader_docs

# # --- Generate Answer ---
# prompt_generate = hub.pull("rlm/rag-prompt")
# def format_docs(docs: List[Document]) -> str:
#     return "\n\n".join(doc.page_content for doc in docs if hasattr(doc, 'page_content') and doc.page_content)
# rag_chain = prompt_generate | llm_generate | StrOutputParser()

# # --- Grade Hallucinations ---
# class GradeHallucinations(LangchainBaseModelV1):
#     """Binary score for hallucination present in generation answer."""
#     binary_score: str = Field(..., description="Answer is grounded in the facts, 'yes' or 'no'") # Corrected

# structured_llm_grader_hallucinations = llm_grader.with_structured_output(GradeHallucinations)
# system_grade_hallucinations = """You are a grader assessing whether an LLM generation is grounded in / supported by a set of retrieved facts.
#      Give a binary score 'yes' or 'no'. 'Yes' means that the answer is grounded in / supported by the set of facts."""
# hallucination_prompt = ChatPromptTemplate.from_messages(
#     [("system", system_grade_hallucinations), ("human", "Set of facts: \n\n {documents} \n\n LLM generation: {generation}")]
# )
# hallucination_grader = hallucination_prompt | structured_llm_grader_hallucinations

# # --- Grade Answer Relevance ---
# class GradeAnswer(LangchainBaseModelV1):
#     """Binary score to assess answer addresses question."""
#     binary_score: str = Field(..., description="Answer addresses the question, 'yes' or 'no'") # Corrected

# structured_llm_grader_answer = llm_grader.with_structured_output(GradeAnswer)
# system_grade_answer = """You are a grader assessing whether an answer addresses / resolves a question.
#      Give a binary score 'yes' or 'no'. 'Yes' means that the answer resolves the question."""
# answer_prompt = ChatPromptTemplate.from_messages(
#     [("system", system_grade_answer), ("human", "User question: \n\n {question} \n\n LLM generation: {generation}")]
# )
# answer_grader = answer_prompt | structured_llm_grader_answer

# # --- Rewrite Question ---
# system_rewrite = """You are a question re-writer that converts an input question to a better version that is optimized
#      for vectorstore retrieval. Look at the input and try to reason about the underlying semantic intent / meaning."""
# re_write_prompt = ChatPromptTemplate.from_messages(
#     [("system", system_rewrite), ("human", "Here is the initial question: \n\n {question} \n Formulate an improved question.")]
# )
# question_rewriter = re_write_prompt | llm_rewrite | StrOutputParser()

# # --- SQL Database Relevance Checker ---
# class GradeDatabaseRelevance(LangchainBaseModelV1):
#     """Binary score to assess if the database would be relevant for answering a question."""
#     binary_score: str = Field(..., description="Database contains information relevant to the question, 'yes' or 'no'") # Corrected
#     explanation: str = Field(..., description="Brief explanation of why the database is or is not relevant") # Corrected

# structured_llm_sql_relevance = llm_sql_helper.with_structured_output(GradeDatabaseRelevance)
# sql_relevance_checker_system = """You are an expert at determining whether a database would be useful for answering user questions about cricket statistics.
#      Based on the user's question and the database description, determine if querying this database
#      would provide relevant information to help answer the question.

#      Database Description: The database contains cricket match delivery information from IPL matches, stored in a table called 'deliveries'.
#      Schema: match_id, inning, batting_team, bowling_team, over, ball, batter, bowler, non_striker, batsman_runs, extra_runs, total_runs, extras_type, is_wicket, player_dismissed, dismissal_kind, fielder.
#      It contains statistics about cricket matches, teams, and players.

#      Consider:
#      1. Is the question asking about specific cricket stats (runs, wickets, scores, overs, players, teams)?
#      2. Could numerical data or aggregations (counts, sums, averages) from the database help?
#      3. Is the question about general cricket rules, history, or information *not* likely in ball-by-ball data?

#      Give a binary score 'yes' or 'no'. 'Yes' means the database is relevant. Also provide a brief explanation.
#      Only respond 'yes' if the database likely contains the specific information asked for.
#      """
# sql_relevance_checker_prompt = ChatPromptTemplate.from_messages(
#     [("system", sql_relevance_checker_system), ("human", "User question: \n\n {question}")]
# )
# sql_relevance_checker = sql_relevance_checker_prompt | structured_llm_sql_relevance

# # --- SQL Query Generator ---
# sql_query_generator_system = """You are an expert PostgreSQL query writer for a cricket database.
#      Your task is to generate a valid SQL query to retrieve information needed to answer the user's question, based on the 'deliveries' table.

#      Database Description: Contains cricket match delivery information from IPL matches in a table named 'deliveries'.
#      Schema: match_id, inning, batting_team, bowling_team, over, ball, batter, bowler, non_striker, batsman_runs, extra_runs, total_runs, extras_type, is_wicket, player_dismissed, dismissal_kind, fielder.

#      Given the user question, return ONLY the SQL query.
#      Rules:
#      1. Only use the 'deliveries' table and its columns listed above.
#      2. Return ONLY the SQL query text - no explanations, backticks, or markdown.
#      3. Use aggregations (COUNT, SUM, AVG) and GROUP BY where appropriate for statistical questions.
#      4. Use WHERE clauses to filter by player names, teams, match conditions etc. mentioned in the question. Be precise with names if possible.
#      5. LIMIT results to a reasonable number (e.g., LIMIT 20) if querying many individual records.
#      6. Ensure the query is valid PostgreSQL.
#      7. Handle potential case sensitivity for names if needed (e.g., use ILIKE or lower()). Example: WHERE lower(batter) = lower('Player Name')
#      """
# sql_query_generator_prompt = ChatPromptTemplate.from_messages(
#     [("system", sql_query_generator_system), ("human", "User question: \n\n {question}")]
# )
# sql_query_generator = sql_query_generator_prompt | llm_sql_helper | StrOutputParser()

# # --- Live Match Data Relevance Checker ---
# class GradeMatchDataRelevance(LangchainBaseModelV1):
#     """Binary score to assess if the live match data would be relevant for answering a question."""
#     binary_score: str = Field(..., description="Live match data contains information relevant to the question, 'yes' or 'no'")
#     explanation: str = Field(..., description="Brief explanation of why the live match data is or is not relevant")

# structured_llm_match_relevance = llm_grader.with_structured_output(GradeMatchDataRelevance)
# match_relevance_checker_system = """You are an expert at determining whether live cricket match data would be useful for answering user questions.
#      Based on the user's question, determine if accessing current live cricket match data
#      would provide relevant information to help answer the question.

#      Live Match Data Description: The data contains real-time information about an ongoing cricket match including:
#      - Current score, run rate, wickets, and overs
#      - Details about current batsmen (runs, balls faced, strike rate)
#      - Details about current bowlers (wickets, economy, overs)
#      - Recent ball-by-ball commentary
#      - Match situation and context (target, required run rate)

#      Consider:
#      1. Is the question asking about the current state of a cricket match (score, players, events)?
#      2. Is the question about predictions or analysis based on the current match situation?
#      3. Does the question refer to "now", "current", "this match", "live", or other present-tense indicators?
#      4. Is the question about general cricket rules or historical data NOT related to a current match?

#      Give a binary score 'yes' or 'no'. 'Yes' means the live match data is relevant.
#      Also provide a brief explanation for your decision.
#      """
# match_relevance_checker_prompt = ChatPromptTemplate.from_messages(
#     [("system", match_relevance_checker_system), ("human", "User question: \n\n {question}")]
# )
# match_relevance_checker = match_relevance_checker_prompt | structured_llm_match_relevance

# print("LangGraph components defined.")
# print("-" * 30)


# # === Define Graph State and Nodes ===

# print("Defining LangGraph state and nodes...")

# class GraphState(TypedDict):
#     """
#     Represents the state of our graph.

#     Attributes:
#         question: The current question being processed.
#         generation: The LLM's generated answer.
#         documents: A list of LangChain Document objects retrieved from vector store and/or SQL DB.
#         iterations: Number of cycles (retrieval attempts) for loop prevention.
#         live_match_relevant: Boolean flag indicating if live match data is relevant.
#     """
#     question: str
#     generation: str
#     documents: List[Document]
#     iterations: int
#     live_match_relevant: bool

# # --- Node Functions ---

# def retrieve_node(state: GraphState) -> Dict[str, Any]:
#     """
#     Retrieve documents from retriever, SQL DB (if relevant), and live match data (if relevant).
    
#     This node handles document retrieval from multiple sources:
#     1. Vector store retrieval for unstructured data
#     2. SQL database for structured cricket data (if deemed relevant)
#     3. Live cricket match data (if available and deemed relevant)
#     """
#     print("---NODE: RETRIEVE---")
#     question = state["question"]
#     documents = []
    
#     # Check if live match data is relevant
#     if has_live_match_data:
#         # First check if query seems to be about live matches (quick check)
#         if is_query_about_live_match(question, llm_grader):
#             print("Query appears to be about live cricket. Getting match data...")
#             match_doc = live_match_checker.get_match_data_document()
#             if match_doc:
#                 documents.append(match_doc)
#                 return {"documents": documents, "live_match_relevant": True}
        
#         # If not obvious, use more advanced classifier
#         match_relevance = match_relevance_checker.invoke({"question": question})
#         if match_relevance.binary_score.lower() == "yes":
#             print(f"Live match data relevant: {match_relevance.explanation}")
#             match_doc = live_match_checker.get_match_data_document()
#             if match_doc:
#                 documents.append(match_doc)
#                 return {"documents": documents, "live_match_relevant": True}
    
#     # SQL DB Relevance check
#     if sql_engine is not None:
#         db_relevance = sql_relevance_checker.invoke({"question": question})
#         if db_relevance.binary_score.lower() == "yes":
#             print(f"SQL DB relevant: {db_relevance.explanation}")
            
#             # Generate and execute SQL query
#             sql_query = sql_query_generator.invoke({"question": question})
#             print(f"Generated SQL Query: {sql_query}")
            
#             try:
#                 # Execute the SQL query
#                 with sql_engine.connect() as connection:
#                     result = connection.execute(text(sql_query))
#                     column_names = result.keys()
#                     rows = result.fetchall()
                
#                 # Format the results as a string
#                 result_string = "SQL Query Results:\n"
#                 result_string += f"Query: {sql_query}\n\n"
                
#                 # Add column headers
#                 result_string += " | ".join(column_names) + "\n"
#                 result_string += "-" * 50 + "\n"
                
#                 # Add rows
#                 for row in rows:
#                     result_string += " | ".join(str(cell) for cell in row) + "\n"
                
#                 # Create Document from SQL results
#                 sql_document = Document(
#                     page_content=result_string,
#                     metadata={"source": "sql_database", "query": sql_query}
#                 )
#                 documents.append(sql_document)
                
#             except Exception as e:
#                 print(f"Error executing SQL query: {e}")
    
#     # Use vector store retrieval 
#     if retriever is not None:
#         try:
#             # Use vector retrieval for remaining document retrieval
#             vector_docs = retriever.invoke(question)
#             documents.extend(vector_docs)
#         except Exception as e:
#             print(f"Error during vector retrieval: {e}")
    
#     return {"documents": documents, "live_match_relevant": False}


# def generate_node(state: GraphState) -> Dict[str, Any]:
#     """
#     Generate answer using the RAG chain.
#     Args: state (GraphState): The current graph state.
#     Returns: Dict[str, Any]: State components updated with the generated answer.
#     """
#     print("---NODE: GENERATE---")
#     question = state["question"]
#     documents = state["documents"]
#     generation = "" # Default empty generation

#     if not documents:
#          print("---WARNING: No documents provided for generation. Generating based on question alone (may hallucinate).---")
#          # Attempt generation without context, or return a specific message
#          try:
#              # Use a simpler prompt if no context
#              simple_prompt_template = ChatPromptTemplate.from_messages([("human", "{question}")])
#              simple_chain = simple_prompt_template | llm_generate | StrOutputParser()
#              generation = simple_chain.invoke({"question": question})
#              print("---Generated fallback answer (no context)---")
#          except Exception as e:
#              print(f"---ERROR during fallback generation: {e}---")
#              generation = f"Error generating answer without documents: {e}"
#     else:
#         formatted_docs = format_docs(documents)
#         if not formatted_docs:
#              print("---WARNING: Documents found but could not be formatted (e.g., empty page_content?). Generating fallback.---")
#              generation = "Could not process the retrieved information to generate an answer." # Specific message
#         else:
#             try:
#                 print(f"---Generating answer based on {len(documents)} documents---")
#                 generation = rag_chain.invoke({"context": formatted_docs, "question": question})
#                 print(f"---Generated Answer Preview: {generation[:200]}...---")
#             except Exception as e:
#                 print(f"---ERROR during RAG generation: {e}---")
#                 generation = f"Error during generation: {e}"

#     # Return only the generation, assumes other state parts are passed through graph
#     return {"generation": generation}


# def grade_documents_node(state: GraphState) -> Dict[str, Any]:
#     """
#     Grade the retrieved documents and determine relevance.

#     This node evaluates the retrieved documents for relevance to the question.
#     For live match data or SQL query results, we skip grading and consider them always relevant.
#     """
#     print("---NODE: GRADE DOCUMENTS---")
#     documents = state["documents"]
#     question = state["question"]
    
#     print(f"Grading {len(documents)} documents")
    
#     # If no documents, return empty
#     if not documents:
#         return {"documents": []}

#     # Skip grading for live match data or SQL results
#     # These are considered valid by default
#     valid_docs = []
#     docs_to_grade = []

#     for doc in documents:
#         source = doc.metadata.get("source", "")
#         if source == "live_cricket_match" or source == "sql_database":
#             valid_docs.append(doc)
#         else:
#             docs_to_grade.append(doc)
    
#     # Grade the remaining documents
#     relevant_docs_to_grade = []
#     for doc in docs_to_grade:
#         grade = retrieval_grader.invoke(
#             {"question": question, "document": doc.page_content}
#         )
#         if grade.binary_score.lower() == "yes":
#             relevant_docs_to_grade.append(doc)
    
#     # Combine valid docs (ungraded) with relevant graded docs
#     all_relevant_docs = valid_docs + relevant_docs_to_grade
    
#     return {"documents": all_relevant_docs}


# def transform_query_node(state: GraphState) -> Dict[str, Any]:
#     """
#     Transform the query to potentially improve retrieval results.
#     Args: state (GraphState): The current graph state.
#     Returns: Dict[str, Any]: State components with the question updated and iterations reset.
#     """
#     print("---NODE: TRANSFORM QUERY---")
#     original_question = state["question"]
#     # Documents are implicitly discarded as the next step is 'retrieve' which fetches anew

#     try:
#         print(f"---Original Question: {original_question}---")
#         better_question = question_rewriter.invoke({"question": original_question})
#         print(f"---Rewritten Question: {better_question}---")
#     except Exception as e:
#         print(f"---ERROR rewriting question: {e}. Using original question.---")
#         better_question = original_question # Fallback

#     # Reset iterations when transforming query to allow retrieval again
#     # Return the updated question and reset iteration count
#     return {"question": better_question, "iterations": 0}


# def grade_generation_node(state: GraphState) -> Dict[str, Any]:
#     """
#     Evaluate the generated answer for hallucinations and relevance.
    
#     This node receives the generated text and evaluates its quality relative to:
#     1. Retrieved documents (hallucination/grounding check)
#     2. Original question (relevance/usefulness check)
    
#     It doesn't make routing decisions (that's handled by the edge function).
#     """
#     print("---NODE: GRADE GENERATION---")
#     question = state["question"]
#     documents = state["documents"]
#     generation = state["generation"] 
#     iterations = state.get("iterations", 0) + 1  # Increment iterations
    
#     # Just increment the iteration counter and pass through
#     # The actual grading is performed in the edge function
#     return {"iterations": iterations}


# # --- Edge Logic Functions ---

# def decide_to_generate_edge(state: GraphState) -> str:
#     """
#     Determine if we have enough relevant documents to proceed to generation.
    
#     This edge function decides whether to:
#     1. Proceed to generation if we have relevant docs or have exhausted retrieval attempts
#     2. Try rewriting the query if initial retrieval was unsuccessful
    
#     Live match data or SQL DB results are always considered sufficient for generation.
#     """
#     print("---EDGE: DECIDE TO GENERATE---")
#     documents = state["documents"]
#     iterations = state["iterations"]
    
#     # If we have passed max iterations, proceed to generation regardless
#     if iterations >= 2:
#         return "generate"
    
#     # Check if any documents are from live match data or SQL database
#     special_sources = False
#     for doc in documents:
#         source = doc.metadata.get("source", "")
#         if source in ["live_cricket_match", "sql_database"]:
#             special_sources = True
#             break
    
#     # If we have live match data or SQL DB results, always proceed to generation
#     if special_sources:
#         return "generate"
    
#     # If we have 0 documents, try rewriting
#     if len(documents) == 0:
#         return "transform_query"
    
#     # Otherwise, proceed to generation
#     return "generate"


# def grade_generation_edge(state: GraphState) -> str:
#     """
#     Determines the quality of the generation and decides the next step.
#     Args: state (GraphState): The current graph state.
#     Returns: str: Decision ('useful', 'not supported', 'not useful', 'transform_query').
#     """
#     print("---EDGE: GRADE GENERATION---")
#     question = state["question"]
#     documents = state["documents"]
#     generation = state["generation"]
#     iterations = state.get("iterations", 0) # Iterations count BEFORE this grade edge

#     # If we were forced to generate due to max iterations, consider the result final (useful).
#     if iterations > 3:
#         print("---DECISION: Max iterations reached previously. Treating generation as FINAL (useful).---")
#         return "useful" # End the loop

#     # Default decision if something goes wrong
#     decision = "transform_query"

#     if not generation or generation.startswith("Error") or generation.startswith("Could not process"):
#          print(f"---DECISION: Generation empty or indicates failure ('{generation[:50]}...'). --> transform_query ---")
#          return "transform_query"

#     if not documents:
#         # Handle case where generation occurred without docs (e.g., fallback)
#         print("---Checking relevance of fallback generation (no documents)---")
#         try:
#             score_answer = answer_grader.invoke({"question": question, "generation": generation})
#             grade_answer = score_answer.binary_score
#             if grade_answer and grade_answer.lower() == "yes":
#                 print("---DECISION: FALLBACK GENERATION ADDRESSES QUESTION --> useful---")
#                 decision = "useful"
#             else:
#                 print(f"---DECISION: FALLBACK GENERATION DOES NOT ADDRESS QUESTION (Grade: {grade_answer}) --> transform_query---")
#                 decision = "transform_query"
#         except Exception as e:
#             print(f"---ERROR grading fallback answer relevance: {e}. Defaulting to transform_query.---")
#             decision = "transform_query"
#         return decision

#     # Normal case: Grade generation based on documents
#     try:
#         print("---Checking Hallucinations (Grounding)---")
#         formatted_docs = format_docs(documents)
#         # Ensure formatted_docs is not empty before calling grader
#         if not formatted_docs:
#             print("---WARNING: Cannot check hallucination grade, formatted documents are empty. Assuming not grounded.---")
#             grade_hallucination = "no" # Treat as not grounded if context is empty
#         else:
#             score_hallucination = hallucination_grader.invoke({"documents": formatted_docs, "generation": generation})
#             grade_hallucination = score_hallucination.binary_score

#         if grade_hallucination and grade_hallucination.lower() == "yes":
#             print("---DECISION: GENERATION IS GROUNDED---")
#             print("---Checking Answer Relevance---")
#             score_answer = answer_grader.invoke({"question": question, "generation": generation})
#             grade_answer = score_answer.binary_score
#             if grade_answer and grade_answer.lower() == "yes":
#                 print("---DECISION: GENERATION ADDRESSES QUESTION --> useful (END)---")
#                 decision = "useful" # Grounded and relevant = END
#             else:
#                 print(f"---DECISION: GENERATION DOES NOT ADDRESS QUESTION (Grade: {grade_answer}) --> transform_query---")
#                 decision = "transform_query" # Grounded but not relevant -> Transform query
#         else:
#             print(f"---DECISION: GENERATION NOT GROUNDED (Hallucination Grade: {grade_hallucination}) --> generate (RETRY)---")
#             # Retry generation with the same documents
#             decision = "generate" # Not grounded -> Retry generation

#     except Exception as e:
#         print(f"---ERROR grading generation: {e}. Defaulting to transform_query.---")
#         decision = "transform_query"

#     return decision

# def initialize_state():
#     """Initialize the graph state with default values."""
#     return {
#         "question": "",
#         "generation": "",
#         "documents": [],
#         "iterations": 0,
#         "live_match_relevant": False
#     }

# print("LangGraph state and nodes defined.")
# print("-" * 30)


# # === Compose and Compile the Graph ===
# def compile_graph():
#     """Compile the LangGraph workflow"""
    
#     workflow = StateGraph(GraphState)
    
#     # Add nodes
#     workflow.add_node("retrieve", retrieve_node)
#     workflow.add_node("grade_documents", grade_documents_node)
#     workflow.add_node("transform_query", transform_query_node)
#     workflow.add_node("generate", generate_node)
#     workflow.add_node("grade_generation", grade_generation_node)
    
#     # Define edges
#     workflow.set_entry_point("retrieve")
#     workflow.add_edge("retrieve", "grade_documents")
    
#     # Add conditional edge for grade_documents
#     workflow.add_conditional_edges(
#         "grade_documents",
#         decide_to_generate_edge,
#         {
#             "transform_query": "transform_query",
#             "generate": "generate"
#         }
#     )
    
#     workflow.add_edge("transform_query", "retrieve")
#     workflow.add_edge("generate", "grade_generation")
#     workflow.add_conditional_edges(
#         "grade_generation",
#         grade_generation_edge,
#         {
#             "useful": END,
#             "generate": "generate",
#             "transform_query": "transform_query"
#         }
#     )
    
#     # Compile graph
#     app = workflow.compile()
    
#     return app

# # === Run the Agent ===
# def run_agent(app, initial_question: str):
#     """Run the agent with the compiled graph on an initial question."""
#     inputs = initialize_state()
#     inputs["question"] = initial_question
    
#     # Execute the graph
#     result = app.invoke(inputs)
    
#     # Return the final answer
#     return result["generation"]


# if __name__ == "__main__":
#     # Ensure database is set up and engine is available
#     if not sql_engine:
#         print("Cannot proceed without a valid database connection.")
#     else:
#         # Compile the graph
#         compiled_app = compile_graph()

#         # --- Define Test Questions ---
#         # Question likely relevant to vector store (Self-RAG paper)
#         question_vector = "How does self-RAG evaluate the relevance of retrieved documents?"
#         # Question likely relevant to SQL database (Cricket Stats)
#         question_sql = "How many runs did V Kohli score in total?"
#         # Another SQL Question
#         question_sql_wickets = "List the bowlers who took more than 150 wickets"
#         # Question likely relevant to BOTH (needs context + specific stats)
#         question_hybrid = "Explain the concept of an 'over' in cricket and show the total runs scored in the first over (over=1) of match_id 1."
#         # Question likely irrelevant to both
#         question_irrelevant = "What is the capital of France?"

#         # --- Run Agent with Test Questions ---
#         print("\n" + "="*50)
#         print(" RUNNING AGENT WITH VECTOR-RELEVANT QUESTION")
#         print("="*50)
#         run_agent(compiled_app, question_vector)

#         print("\n" + "="*50)
#         print(" RUNNING AGENT WITH SQL-RELEVANT QUESTION (Kohli Runs)")
#         print("="*50)
#         run_agent(compiled_app, question_sql)

#         print("\n" + "="*50)
#         print(" RUNNING AGENT WITH SQL-RELEVANT QUESTION (Wickets)")
#         print("="*50)
#         run_agent(compiled_app, question_sql_wickets)

#         print("\n" + "="*50)
#         print(" RUNNING AGENT WITH HYBRID QUESTION")
#         print("="*50)
#         run_agent(compiled_app, question_hybrid)

#         print("\n" + "="*50)
#         print(" RUNNING AGENT WITH IRRELEVANT QUESTION")
#         print("="*50)
#         run_agent(compiled_app, question_irrelevant)

#         print("\nScript finished.")


# -*- coding: utf-8 -*-
"""
LangGraph Agent powered by a Pathway Vector Store and integrated SQL Database.

This script defines and runs a LangGraph agent that uses:
1. A Pathway VectorStoreRetriever for unstructured data.
2. A PostgreSQL database for structured cricket data.
3. Web search for fallback when other data sources are insufficient.

It checks question relevance for the SQL DB, generates/executes queries if relevant,
and combines results with vector retrieval for the LLM generation.
"""

import os
import time
import sys
from typing import List, Dict, Any
# Use Pydantic V1 specifically if needed, or just BaseModel if V2 is okay
from pydantic.v1 import BaseModel as PydanticBaseModelV1, Field
from dotenv import load_dotenv
import pandas as pd
from sqlalchemy import text

# LangChain and LangGraph imports
from langchain_community.vectorstores import PathwayVectorClient # For LCEL integration
from langchain_core.prompts import ChatPromptTemplate
# Use the aliased Pydantic V1 BaseModel for Langchain compatibility
from langchain_core.pydantic_v1 import BaseModel as LangchainBaseModelV1
from langchain_core.output_parsers import StrOutputParser
from langchain_core.documents import Document # Ensure Document is imported
from langchain_openai import ChatOpenAI
from langchain import hub
from langgraph.graph import END, StateGraph, START
from typing_extensions import TypedDict

# Pathway client import
from pathway.xpacks.llm.vector_store import VectorStoreClient # For direct client interaction (optional checks)

# Web Search Import
from websearch import web_search

# SQL Database Setup Import
import sql_setup # Import the setup script

# Live Cricket Match Data Import
from live_match_processor import LiveMatchRelevanceChecker, is_query_about_live_match

# Pretty printing
from pprint import pprint

# === Configuration ===

# Load environment variables from .env file
load_dotenv(override=True)

# OpenAI API Key
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OpenAI API Key not found. Please set the OPENAI_API_KEY environment variable.")
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY

# Pathway Vector Store Server Configuration
PATHWAY_HOST: str = os.environ.get("PATHWAY_HOST", "0.0.0.0")
PATHWAY_PORT: int = int(os.environ.get("PATHWAY_PORT", 8000))

# Database Configuration (ensure these match .env and sql_setup.py)
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_USER = os.getenv("DB_USER", "postgres")
DB_NAME = os.getenv("DB_NAME", "quicksell_rag")

# === Initialize Database ===
print("Initializing PostgreSQL database connection...")
# The setup_database function returns the engine
sql_engine = sql_setup.setup_database(csv_filepath='deliveries.csv')
if sql_engine is None:
    print("FATAL: Database setup failed. Exiting.")
    sys.exit(1)
else:
    print(f"Successfully connected to database '{DB_NAME}' on {DB_HOST}:{DB_PORT}")
print("-" * 30)


# === Pathway Client and Retriever Setup ===

print("Setting up Pathway client and LangChain retriever...")
print(f"Attempting to connect to Pathway server at {PATHWAY_HOST}:{PATHWAY_PORT}...")

# Allow a moment for the server to potentially be ready if just started
time.sleep(5)

retriever = None # Initialize retriever
try:
    # Create LangChain retriever via PathwayVectorClient
    vectorstore_client_lc = PathwayVectorClient(PATHWAY_HOST, PATHWAY_PORT)
    retriever = vectorstore_client_lc.as_retriever()
    print("LangChain Pathway retriever created.")

    # Test the retriever (optional check)
    test_question = "self-RAG"
    print(f"\nTesting Pathway retriever with question: '{test_question}'")
    relevant_docs_vector = retriever.invoke(test_question) # Use invoke for LCEL compatibility
    print(f"Retrieved {len(relevant_docs_vector)} documents from Pathway for test question.")

except Exception as e:
    print(f"\n--- WARNING ---")
    print(f"Error connecting to or interacting with Pathway server at {PATHWAY_HOST}:{PATHWAY_PORT}: {e}")
    print("Pathway Vector Store retrieval will be unavailable.")
    # Allow continuation without vector store if needed, or exit:
    # sys.exit(1)

print("-" * 30)


# === Initialize Live Match Data Processor ===
print("Initializing Live Cricket Match Data Processor...")
live_match_checker = LiveMatchRelevanceChecker()
has_live_match_data = live_match_checker.check_for_live_data()
if has_live_match_data:
    print("Live cricket match data is available for processing.")
else:
    print("No live cricket match data found.")
print("-" * 30)


# === Define LangGraph Workflow Components ===

print("Defining LangGraph components (Graders, Generators, Rewriter, SQL Helpers)...")

# --- LLM Instances ---
# Use consistent models where appropriate
llm_grader = ChatOpenAI(model="gpt-4o-mini", temperature=0)
llm_sql_helper = ChatOpenAI(model="gpt-4o-mini", temperature=0)
llm_rewrite = ChatOpenAI(model="gpt-4o-mini", temperature=0)
# Keep potentially different model for main generation if intended
llm_generate = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0)

# --- Grade Documents (Vector Store Relevance) ---
class GradeDocuments(LangchainBaseModelV1):
    """Binary score for relevance check on retrieved documents."""
    binary_score: str = Field(..., description="Documents are relevant to the question, 'yes' or 'no'") # Corrected

structured_llm_grader_docs = llm_grader.with_structured_output(GradeDocuments)
system_grade_docs = """You are a grader assessing relevance of a retrieved document to a user question.
    It does not need to be a stringent test. The goal is to filter out erroneous retrievals.
    If the document contains keyword(s) or semantic meaning related to the user question, grade it as relevant.
    Give a binary score 'yes' or 'no' score to indicate whether the document is relevant to the question."""
grade_prompt = ChatPromptTemplate.from_messages(
    [("system", system_grade_docs), ("human", "Retrieved document: \n\n {document} \n\n User question: {question}")]
)
retrieval_grader = grade_prompt | structured_llm_grader_docs

# --- Generate Answer ---
prompt_generate = hub.pull("rlm/rag-prompt")
def format_docs(docs: List[Document]) -> str:
    return "\n\n".join(doc.page_content for doc in docs if hasattr(doc, 'page_content') and doc.page_content)
rag_chain = prompt_generate | llm_generate | StrOutputParser()

# --- Grade Hallucinations ---
class GradeHallucinations(LangchainBaseModelV1):
    """Binary score for hallucination present in generation answer."""
    binary_score: str = Field(..., description="Answer is grounded in the facts, 'yes' or 'no'") # Corrected

structured_llm_grader_hallucinations = llm_grader.with_structured_output(GradeHallucinations)
system_grade_hallucinations = """You are a grader assessing whether an LLM generation is grounded in / supported by a set of retrieved facts.
     Give a binary score 'yes' or 'no'. 'Yes' means that the answer is grounded in / supported by the set of facts."""
hallucination_prompt = ChatPromptTemplate.from_messages(
    [("system", system_grade_hallucinations), ("human", "Set of facts: \n\n {documents} \n\n LLM generation: {generation}")]
)
hallucination_grader = hallucination_prompt | structured_llm_grader_hallucinations

# --- Grade Answer Relevance ---
class GradeAnswer(LangchainBaseModelV1):
    """Binary score to assess answer addresses question."""
    binary_score: str = Field(..., description="Answer addresses the question, 'yes' or 'no'") # Corrected

structured_llm_grader_answer = llm_grader.with_structured_output(GradeAnswer)
system_grade_answer = """You are a grader assessing whether an answer addresses / resolves a question.
     Give a binary score 'yes' or 'no'. 'Yes' means that the answer resolves the question."""
answer_prompt = ChatPromptTemplate.from_messages(
    [("system", system_grade_answer), ("human", "User question: \n\n {question} \n\n LLM generation: {generation}")]
)
answer_grader = answer_prompt | structured_llm_grader_answer

# --- Rewrite Question ---
system_rewrite = """You are a question re-writer that converts an input question to a better version that is optimized
     for vectorstore retrieval. Look at the input and try to reason about the underlying semantic intent / meaning."""
re_write_prompt = ChatPromptTemplate.from_messages(
    [("system", system_rewrite), ("human", "Here is the initial question: \n\n {question} \n Formulate an improved question.")]
)
question_rewriter = re_write_prompt | llm_rewrite | StrOutputParser()

# --- SQL Database Relevance Checker ---
class GradeDatabaseRelevance(LangchainBaseModelV1):
    """Binary score to assess if the database would be relevant for answering a question."""
    binary_score: str = Field(..., description="Database contains information relevant to the question, 'yes' or 'no'") # Corrected
    explanation: str = Field(..., description="Brief explanation of why the database is or is not relevant") # Corrected

structured_llm_sql_relevance = llm_sql_helper.with_structured_output(GradeDatabaseRelevance)
sql_relevance_checker_system = """You are an expert at determining whether a database would be useful for answering user questions about IPL cricket (Indian Premier League) statistics.
     Based on the user's question and the database description, determine if querying this database
     would provide relevant information to help answer the question.

     Database Description: The database contains cricket match delivery information from IPL matches, stored in a table called 'deliveries'.
     Schema: match_id, inning, batting_team, bowling_team, over, ball, batter, bowler, non_striker, batsman_runs, extra_runs, total_runs, extras_type, is_wicket, player_dismissed, dismissal_kind, fielder.
     It contains statistics about cricket matches, teams, and players.

     Consider:
     1. Is the question asking about specific cricket stats (runs, wickets, scores, overs, players, teams)?
     2. Could numerical data or aggregations (counts, sums, averages) from the database help?
     3. Is the question about general cricket rules, history, or information *not* likely in ball-by-ball data?

     Give a binary score 'yes' or 'no'. 'Yes' means the database is relevant. Also provide a brief explanation.
     Only respond 'yes' if the database likely contains the specific information asked for.
     """
sql_relevance_checker_prompt = ChatPromptTemplate.from_messages(
    [("system", sql_relevance_checker_system), ("human", "User question: \n\n {question}")]
)
sql_relevance_checker = sql_relevance_checker_prompt | structured_llm_sql_relevance

# --- SQL Query Generator ---
sql_query_generator_system = """You are an expert PostgreSQL query writer for a cricket database.
     Your task is to generate a valid SQL query to retrieve information needed to answer the user's question, based on the 'deliveries' table.

     Database Description: Contains cricket match delivery information from IPL matches in a table named 'deliveries'.
     Schema: match_id, inning, batting_team, bowling_team, over, ball, batter, bowler, non_striker, batsman_runs, extra_runs, total_runs, extras_type, is_wicket, player_dismissed, dismissal_kind, fielder.

     Given the user question, return ONLY the SQL query.
     Rules:
     1. Only use the 'deliveries' table and its columns listed above.
     2. Return ONLY the SQL query text - no explanations, backticks, or markdown.
     3. Use aggregations (COUNT, SUM, AVG) and GROUP BY where appropriate for statistical questions.
     4. Use WHERE clauses to filter by player names, teams, match conditions etc. mentioned in the question. Be precise with names if possible.
     5. LIMIT results to a reasonable number (e.g., LIMIT 20) if querying many individual records.
     6. Ensure the query is valid PostgreSQL.
     7. Handle potential case sensitivity for names if needed (e.g., use ILIKE or lower()). Example: WHERE lower(batter) = lower('Player Name')
     """
sql_query_generator_prompt = ChatPromptTemplate.from_messages(
    [("system", sql_query_generator_system), ("human", "User question: \n\n {question}")]
)
sql_query_generator = sql_query_generator_prompt | llm_sql_helper | StrOutputParser()

# --- Live Match Data Relevance Checker ---
class GradeMatchDataRelevance(LangchainBaseModelV1):
    """Binary score to assess if the live match data would be relevant for answering a question."""
    binary_score: str = Field(..., description="Live match data contains information relevant to the question, 'yes' or 'no'")
    explanation: str = Field(..., description="Brief explanation of why the live match data is or is not relevant")

structured_llm_match_relevance = llm_grader.with_structured_output(GradeMatchDataRelevance)
match_relevance_checker_system = """You are an expert at determining whether live cricket match data would be useful for answering user questions.
     Based on the user's question, determine if accessing current live cricket match data
     would provide relevant information to help answer the question.

     Live Match Data Description: The data contains real-time information about an ongoing cricket match including:
     - Current score, run rate, wickets, and overs
     - Details about current batsmen (runs, balls faced, strike rate)
     - Details about current bowlers (wickets, economy, overs)
     - Recent ball-by-ball commentary
     - Match situation and context (target, required run rate)

     Consider:
     1. Is the question asking about the current state of a cricket match (score, players, events)?
     2. Is the question about predictions or analysis based on the current match situation?
     3. Does the question refer to "now", "current", "this match", "live", or other present-tense indicators?
     4. Is the question about general cricket rules or historical data NOT related to a current match?

     Give a binary score 'yes' or 'no'. 'Yes' means the live match data is relevant.
     Also provide a brief explanation for your decision.
     """
match_relevance_checker_prompt = ChatPromptTemplate.from_messages(
    [("system", match_relevance_checker_system), ("human", "User question: \n\n {question}")]
)
match_relevance_checker = match_relevance_checker_prompt | structured_llm_match_relevance

print("LangGraph components defined.")
print("-" * 30)


# === Define Graph State and Nodes ===

print("Defining LangGraph state and nodes...")

class GraphState(TypedDict):
    """
    Represents the state of our graph.

    Attributes:
        question: The current question being processed.
        generation: The LLM's generated answer.
        documents: A list of LangChain Document objects retrieved from vector store and/or SQL DB.
        iterations: Number of cycles (retrieval attempts) for loop prevention.
        live_match_relevant: Boolean flag indicating if live match data is relevant.
        tried_web_search: Boolean flag indicating if web search has been attempted.
        search_results: Dictionary containing web search results information.
    """
    question: str
    generation: str
    documents: List[Document]
    iterations: int
    live_match_relevant: bool
    tried_web_search: bool
    search_results: Dict[str, Any]

# --- Node Functions ---

def retrieve_node(state: GraphState) -> Dict[str, Any]:
    """
    Retrieve documents from retriever, SQL DB (if relevant), and live match data (if relevant).
    
    This node handles document retrieval from multiple sources:
    1. Vector store retrieval for unstructured data
    2. SQL database for structured cricket data (if deemed relevant)
    3. Live cricket match data (if available and deemed relevant)
    """
    print("---NODE: RETRIEVE---")
    question = state["question"]
    documents = []
    
    # Check if live match data is relevant
    if has_live_match_data:
        # First check if query seems to be about live matches (quick check)
        if is_query_about_live_match(question, llm_grader):
            print("Query appears to be about live cricket. Getting match data...")
            match_doc = live_match_checker.get_match_data_document()
            if match_doc:
                documents.append(match_doc)
                return {"documents": documents, "live_match_relevant": True}
        
        # If not obvious, use more advanced classifier
        match_relevance = match_relevance_checker.invoke({"question": question})
        if match_relevance.binary_score.lower() == "yes":
            print(f"Live match data relevant: {match_relevance.explanation}")
            match_doc = live_match_checker.get_match_data_document()
            if match_doc:
                documents.append(match_doc)
                return {"documents": documents, "live_match_relevant": True}
    
    # SQL DB Relevance check
    if sql_engine is not None:
        db_relevance = sql_relevance_checker.invoke({"question": question})
        if db_relevance.binary_score.lower() == "yes":
            print(f"SQL DB relevant: {db_relevance.explanation}")
            
            # Generate and execute SQL query
            sql_query = sql_query_generator.invoke({"question": question})
            print(f"Generated SQL Query: {sql_query}")
            
            try:
                # Execute the SQL query
                with sql_engine.connect() as connection:
                    result = connection.execute(text(sql_query))
                    column_names = result.keys()
                    rows = result.fetchall()
                
                # Format the results as a string
                result_string = f"Answer to your question {question}:\n"
                result_string += f"SQL Query Results:\n"
                result_string += f"Query: {sql_query}\n\n"
                
                # Add column headers
                result_string += " | ".join(column_names) + "\n"
                result_string += "-" * 50 + "\n"
                
                # Add rows
                for row in rows:
                    result_string += " | ".join(str(cell) for cell in row) + "\n"
                
                # Create Document from SQL results
                sql_document = Document(
                    page_content=result_string,
                    metadata={"source": "sql_database", "query": sql_query}
                )
                documents.append(sql_document)
                
            except Exception as e:
                print(f"Error executing SQL query: {e}")
    
    # Use vector store retrieval 
    if retriever is not None:
        try:
            # Use vector retrieval for remaining document retrieval
            vector_docs = retriever.invoke(question)
            documents.extend(vector_docs)
        except Exception as e:
            print(f"Error during vector retrieval: {e}")
    
    return {"documents": documents, "live_match_relevant": False}


def generate_node(state: GraphState) -> Dict[str, Any]:
    """
    Generate answer using the RAG chain.
    Args: state (GraphState): The current graph state.
    Returns: Dict[str, Any]: State components updated with the generated answer.
    """
    print("---NODE: GENERATE---")
    question = state["question"]
    documents = state["documents"]
    generation = "" # Default empty generation

    if not documents:
         print("---WARNING: No documents provided for generation. Generating based on question alone (may hallucinate).---")
         # Attempt generation without context, or return a specific message
         try:
             # Use a simpler prompt if no context
             simple_prompt_template = ChatPromptTemplate.from_messages([("human", "{question}")])
             simple_chain = simple_prompt_template | llm_generate | StrOutputParser()
             generation = simple_chain.invoke({"question": question})
             print("---Generated fallback answer (no context)---")
         except Exception as e:
             print(f"---ERROR during fallback generation: {e}---")
             generation = f"Error generating answer without documents: {e}"
    else:
        formatted_docs = format_docs(documents)
        if not formatted_docs:
             print("---WARNING: Documents found but could not be formatted (e.g., empty page_content?). Generating fallback.---")
             generation = "Could not process the retrieved information to generate an answer." # Specific message
        else:
            try:
                print(f"---Generating answer based on {len(documents)} documents---")
                generation = rag_chain.invoke({"context": formatted_docs, "question": question})
                print(f"---Generated Answer Preview: {generation[:200]}...---")
            except Exception as e:
                print(f"---ERROR during RAG generation: {e}---")
                generation = f"Error during generation: {e}"

    # Return only the generation, assumes other state parts are passed through graph
    return {"generation": generation}


def grade_documents_node(state: GraphState) -> Dict[str, Any]:
    """
    Grade the retrieved documents and determine relevance.

    This node evaluates the retrieved documents for relevance to the question.
    For live match data or SQL query results, we skip grading and consider them always relevant.
    """
    print("---NODE: GRADE DOCUMENTS---")
    documents = state["documents"]
    question = state["question"]
    
    print(f"Grading {len(documents)} documents")
    
    # If no documents, return empty
    if not documents:
        return {"documents": []}

    # Skip grading for live match data or SQL results
    # These are considered valid by default
    valid_docs = []
    docs_to_grade = []

    for doc in documents:
        source = doc.metadata.get("source", "")
        if source == "live_cricket_match" or source == "sql_database":
            valid_docs.append(doc)
        else:
            docs_to_grade.append(doc)
    
    # Grade the remaining documents
    relevant_docs_to_grade = []
    for doc in docs_to_grade:
        grade = retrieval_grader.invoke(
            {"question": question, "document": doc.page_content}
        )
        if grade.binary_score.lower() == "yes":
            relevant_docs_to_grade.append(doc)
    
    # Combine valid docs (ungraded) with relevant graded docs
    all_relevant_docs = valid_docs + relevant_docs_to_grade
    
    return {"documents": all_relevant_docs}


def transform_query_node(state: GraphState) -> Dict[str, Any]:
    """
    Transform the query to potentially improve retrieval results.
    Args: state (GraphState): The current graph state.
    Returns: Dict[str, Any]: State components with the question updated and iterations reset.
    """
    print("---NODE: TRANSFORM QUERY---")
    original_question = state["question"]
    # Documents are implicitly discarded as the next step is 'retrieve' which fetches anew

    try:
        print(f"---Original Question: {original_question}---")
        better_question = question_rewriter.invoke({"question": original_question})
        print(f"---Rewritten Question: {better_question}---")
    except Exception as e:
        print(f"---ERROR rewriting question: {e}. Using original question.---")
        better_question = original_question # Fallback

    # Reset iterations when transforming query to allow retrieval again
    # Return the updated question and reset iteration count
    return {"question": better_question, "iterations": 0}


def grade_generation_node(state: GraphState) -> Dict[str, Any]:
    """
    Evaluate the generated answer for hallucinations and relevance.
    
    This node receives the generated text and evaluates its quality relative to:
    1. Retrieved documents (hallucination/grounding check)
    2. Original question (relevance/usefulness check)
    
    It doesn't make routing decisions (that's handled by the edge function).
    """
    print("---NODE: GRADE GENERATION---")
    question = state["question"]
    documents = state["documents"]
    generation = state["generation"] 
    iterations = state.get("iterations", 0) + 1  # Increment iterations
    
    # Just increment the iteration counter and pass through
    # The actual grading is performed in the edge function
    return {"iterations": iterations}


# --- Edge Logic Functions ---

def decide_to_generate_edge(state: GraphState) -> str:
    """
    Determine if we have enough relevant documents to proceed to generation.
    
    This edge function decides whether to:
    1. Proceed to generation if we have relevant docs or have exhausted retrieval attempts
    2. Try web search if both SQL and vector retrievals were unsuccessful or irrelevant
    3. Try rewriting the query if initial retrieval was unsuccessful and web search was already tried
    
    Live match data, SQL DB results, or web search results are always considered sufficient for generation.
    """
    print("---EDGE: DECIDE TO GENERATE---")
    documents = state["documents"]
    iterations = state["iterations"]
    tried_web_search = state.get("tried_web_search", False)
    
    # If we have passed max iterations, proceed to generation regardless
    if iterations >= 2:
        return "generate"
    
    # Check if any documents are from special sources (live match, SQL DB, or web search)
    special_sources = False
    for doc in documents:
        source = doc.metadata.get("source", "")
        if source in ["live_cricket_match", "sql_database", "tavily_web_search"]:
            special_sources = True
            break
    
    # If we have special source data, always proceed to generation
    if special_sources:
        return "generate"
    
    # If we have 0 documents and haven't tried web search yet, try web search
    if len(documents) == 0 and not tried_web_search:
        return "web_search"
    
    # If we have 0 documents and already tried web search, try rewriting the query
    if len(documents) == 0 and tried_web_search:
        return "transform_query"
    
    # Otherwise, proceed to generation
    return "generate"


def grade_generation_edge(state: GraphState) -> str:
    """
    Determines the quality of the generation and decides the next step.
    Args: state (GraphState): The current graph state.
    Returns: str: Decision ('useful', 'not supported', 'not useful', 'transform_query', 'web_search').
    """
    print("---EDGE: GRADE GENERATION---")
    question = state["question"]
    documents = state["documents"]
    generation = state["generation"]
    iterations = state.get("iterations", 0) # Iterations count BEFORE this grade edge
    tried_web_search = state.get("tried_web_search", False)

    # If we were forced to generate due to max iterations, consider the result final (useful).
    if iterations > 3:
        print("---DECISION: Max iterations reached previously. Treating generation as FINAL (useful).---")
        return "useful" # End the loop

    # Default decision if something goes wrong
    decision = "transform_query"

    if not generation or generation.startswith("Error") or generation.startswith("Could not process"):
         print(f"---DECISION: Generation empty or indicates failure ('{generation[:50]}...'). --> transform_query ---")
         if not tried_web_search:
             return "web_search"
         return "transform_query"

    if not documents:
        # Handle case where generation occurred without docs (e.g., fallback)
        print("---Checking relevance of fallback generation (no documents)---")
        try:
            score_answer = answer_grader.invoke({"question": question, "generation": generation})
            grade_answer = score_answer.binary_score
            if grade_answer and grade_answer.lower() == "yes":
                print("---DECISION: FALLBACK GENERATION ADDRESSES QUESTION --> useful---")
                decision = "useful"
            else:
                print(f"---DECISION: FALLBACK GENERATION DOES NOT ADDRESS QUESTION (Grade: {grade_answer})---")
                if not tried_web_search:
                    print("---DECISION: TRY WEB SEARCH---")
                    decision = "web_search"
                else:
                    print("---DECISION: WEB SEARCH ALREADY TRIED, TRANSFORM QUERY---")
                    decision = "transform_query"
        except Exception as e:
            print(f"---ERROR grading fallback answer relevance: {e}.---")
            if not tried_web_search:
                print("---DECISION: ERROR IN GRADING, TRY WEB SEARCH---")
                decision = "web_search"
            else:
                print("---DECISION: ERROR IN GRADING, WEB SEARCH ALREADY TRIED, TRANSFORM QUERY---")
                decision = "transform_query"
        return decision

    # Normal case: Grade generation based on documents
    try:
        print("---Checking Hallucinations (Grounding)---")
        formatted_docs = format_docs(documents)
        # Ensure formatted_docs is not empty before calling grader
        if not formatted_docs:
            print("---WARNING: Cannot check hallucination grade, formatted documents are empty. Assuming not grounded.---")
            grade_hallucination = "no" # Treat as not grounded if context is empty
        else:
            score_hallucination = hallucination_grader.invoke({"documents": formatted_docs, "generation": generation})
            grade_hallucination = score_hallucination.binary_score

        if grade_hallucination and grade_hallucination.lower() == "yes":
            print("---DECISION: GENERATION IS GROUNDED---")
            print("---Checking Answer Relevance---")
            score_answer = answer_grader.invoke({"question": question, "generation": generation})
            grade_answer = score_answer.binary_score
            if grade_answer and grade_answer.lower() == "yes":
                print("---DECISION: GENERATION ADDRESSES QUESTION --> useful (END)---")
                decision = "useful" # Grounded and relevant = END
            else:
                print(f"---DECISION: GENERATION DOES NOT ADDRESS QUESTION (Grade: {grade_answer})---")
                if not tried_web_search:
                    print("---DECISION: TRY WEB SEARCH---")
                    decision = "web_search"
                else:
                    print("---DECISION: WEB SEARCH ALREADY TRIED, TRANSFORM QUERY---")
                    decision = "transform_query"
        else:
            print(f"---DECISION: GENERATION NOT GROUNDED (Hallucination Grade: {grade_hallucination})---")
            # If not grounded and haven't tried web search, try web search
            if not tried_web_search:
                print("---DECISION: TRY WEB SEARCH---")
                decision = "web_search"
            else:
                # If already tried web search, retry generation
                print("---DECISION: WEB SEARCH ALREADY TRIED, RETRY GENERATION---")
                decision = "generate" # Not grounded -> Retry generation

    except Exception as e:
        print(f"---ERROR grading generation: {e}.---")
        if not tried_web_search:
            print("---DECISION: ERROR IN GRADING, TRY WEB SEARCH---")
            decision = "web_search"
        else:
            print("---DECISION: ERROR IN GRADING, WEB SEARCH ALREADY TRIED, TRANSFORM QUERY---")
            decision = "transform_query"

    return decision

def initialize_state():
    """Initialize the graph state with default values."""
    return {
        "question": "",
        "generation": "",
        "documents": [],
        "iterations": 0,
        "live_match_relevant": False,
        "tried_web_search": False,
        "search_results": {}
    }

print("LangGraph state and nodes defined.")
print("-" * 30)


# === Compose and Compile the Graph ===
def compile_graph():
    """Compile the LangGraph workflow"""
    
    workflow = StateGraph(GraphState)
    
    # Add nodes
    workflow.add_node("retrieve", retrieve_node)
    workflow.add_node("grade_documents", grade_documents_node)
    workflow.add_node("transform_query", transform_query_node)
    workflow.add_node("generate", generate_node)
    workflow.add_node("grade_generation", grade_generation_node)
    workflow.add_node("web_search", web_search_node)  # Add web search node
    
    # Define edges
    workflow.set_entry_point("retrieve")
    workflow.add_edge("retrieve", "grade_documents")
    
    # Add conditional edge for grade_documents
    workflow.add_conditional_edges(
        "grade_documents",
        decide_to_generate_edge,
        {
            "transform_query": "transform_query",
            "generate": "generate",
            "web_search": "web_search"  # New edge to web search
        }
    )
    
    workflow.add_edge("transform_query", "retrieve")
    workflow.add_edge("web_search", "grade_documents")  # Web search results go through document grading
    workflow.add_edge("generate", "grade_generation")
    workflow.add_conditional_edges(
        "grade_generation",
        grade_generation_edge,
        {
            "useful": END,
            "generate": "generate",
            "transform_query": "transform_query",
            "web_search": "web_search"  # New edge from grade_generation to web_search
        }
    )
    
    # Compile graph
    app = workflow.compile()
    
    return app

# === Run the Agent ===
def run_agent(app, initial_question: str):
    """Run the agent with the compiled graph on an initial question."""
    inputs = initialize_state()
    inputs["question"] = initial_question
    
    # Execute the graph
    result = app.invoke(inputs)
    
    # Return the final answer
    return result["generation"]


if __name__ == "__main__":
    # Ensure database is set up and engine is available
    if not sql_engine:
        print("Cannot proceed without a valid database connection.")
    else:
        # Compile the graph
        compiled_app = compile_graph()

        # --- Define Test Questions ---
        # Question likely relevant to vector store (Self-RAG paper)
        question_vector = "How does self-RAG evaluate the relevance of retrieved documents?"
        # Question likely relevant to SQL database (Cricket Stats)
        question_sql = "How many runs did V Kohli score in total?"
        # Another SQL Question
        question_sql_wickets = "List the bowlers who took more than 150 wickets"
        # Question likely relevant to BOTH (needs context + specific stats)
        question_hybrid = "Explain the concept of an 'over' in cricket and show the total runs scored in the first over (over=1) of match_id 1."
        # Question likely irrelevant to both local sources (will trigger web search)
        question_web_search = "What are the latest developments in quantum computing in 2023?"
        # Question likely irrelevant to both
        question_irrelevant = "What is the capital of France?"

        # --- Run Agent with Test Questions ---
        print("\n" + "="*50)
        print(" RUNNING AGENT WITH VECTOR-RELEVANT QUESTION")
        print("="*50)
        run_agent(compiled_app, question_vector)

        print("\n" + "="*50)
        print(" RUNNING AGENT WITH SQL-RELEVANT QUESTION (Kohli Runs)")
        print("="*50)
        run_agent(compiled_app, question_sql)

        print("\n" + "="*50)
        print(" RUNNING AGENT WITH SQL-RELEVANT QUESTION (Wickets)")
        print("="*50)
        run_agent(compiled_app, question_sql_wickets)

        print("\n" + "="*50)
        print(" RUNNING AGENT WITH HYBRID QUESTION")
        print("="*50)
        run_agent(compiled_app, question_hybrid)
        
        print("\n" + "="*50)
        print(" RUNNING AGENT WITH WEB SEARCH QUESTION")
        print("="*50)
        run_agent(compiled_app, question_web_search)

        print("\n" + "="*50)
        print(" RUNNING AGENT WITH IRRELEVANT QUESTION")
        print("="*50)
        run_agent(compiled_app, question_irrelevant)

        print("\nScript finished.")

def web_search_node(state: GraphState) -> Dict[str, Any]:
    """
    Perform web search using Tavily API when other data sources are insufficient.
    
    This node is invoked when:
    1. SQL DB retrieval was not relevant or failed
    2. Vector store retrieval was not relevant or insufficient
    3. Live match data was not relevant or unavailable
    
    Args: state (GraphState): The current graph state.
    Returns: Dict[str, Any]: Updated state with web search results.
    """
    print("---NODE: WEB SEARCH---")
    
    # Check if web search was already attempted to prevent loops
    if state.get("tried_web_search", False):
        print("Web search already attempted, skipping to avoid loops.")
        return {}
    
    # Run web search function from websearch.py
    search_result = web_search(state)
    
    # Extract and return the results
    web_documents = search_result.get("documents", [])
    web_search_results = search_result.get("search_results", {})
    tried_web_search = search_result.get("tried_web_search", True)
    
    print(f"Web search retrieved {len(web_documents)} documents")
    
    return {
        "documents": web_documents,
        "search_results": web_search_results,
        "tried_web_search": tried_web_search
    }