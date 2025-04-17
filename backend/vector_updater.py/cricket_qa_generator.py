# Force loading environment variables from .env first
from dotenv import load_dotenv
load_dotenv(override=True)  # override=True ensures .env values take precedence over existing env vars

import csv
import os
import time
from datetime import datetime
import random
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage
from langchain_core.tools import Tool
from langchain_core.documents import Document
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import MessagesPlaceholder
from tavily import TavilyClient

# Initialize Tavily client
tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

# Define Tavily search tool
def tavily_search(query):
    """Search the web with Tavily Search API."""
    response = tavily_client.search(query=query)
    return response

tavily_search_tool = Tool(
    name="tavily_search",
    description="Search for information on the web using Tavily Search API",
    func=tavily_search
)

# Define Tavily extract tool
def tavily_extract(url):
    """Extract content from a webpage using Tavily Extract API."""
    response = tavily_client.extract(urls=[url])
    return response

tavily_extract_tool = Tool(
    name="tavily_extract",
    description="Extract content from a specific webpage using Tavily Extract API",
    func=tavily_extract
)

def web_search(question):
    """
    Perform web search for cricket information
    """
    print(f"---PERFORMING WEB SEARCH FOR: {question}---")
    
    try:
        tools = [tavily_search_tool, tavily_extract_tool]
        agent_llm = ChatOpenAI(model="gpt-4o-mini", temperature=1.0)

        # Set up Prompt with 'agent_scratchpad'
        today = datetime.today().strftime("%B %d, %Y")
        prompt = ChatPromptTemplate.from_messages([
            ("system", f"""You are a cricket research assistant, you will be given a query about cricket 
            (especially IPL matches) and you will need to search the web for the most relevant information.
            The date today is {today}. Keep your searches focused on gathering factual information about 
            cricket matches, team/player performances, statistics, and turning points in matches."""),
            MessagesPlaceholder(variable_name="messages"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),  # Required for tool calls
        ])

        agent = create_openai_tools_agent(
            llm=agent_llm,
            tools=tools,
            prompt=prompt
        )

        agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

        response = agent_executor.invoke({"messages": [HumanMessage(content=question)]})
        print("Search completed successfully")

        return response.get("output", "")

    except Exception as e:
        print(f"Error during web search: {str(e)}")
        return f"Web search failed with error: {str(e)}"

def generate_base_question():
    """Generate a base question about recent IPL matches"""
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=1.0)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an expert cricket researcher focusing on IPL. 
        Generate a specific question about the most recent or current IPL match.
        Example: "Who played the rececent IPL match and who won?"
        Keep it concise and ensure it can be answered with factual information."""),
    ])
    
    chain = prompt | llm
    result = chain.invoke({})
    return result.content.strip()

def get_answer(question):
    """Get answer for a question using web search"""
    return web_search(question)

def generate_followup_question(base_question, base_answer):
    """Generate a follow-up question based on the base question and answer"""
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=1.0)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an expert cricket analyst focusing on IPL.
        Based on the provided question and answer, generate a follow-up question that digs deeper
        into player performance, team strategy, or turning points in the match.
        Your follow-up should be specific and related to the context provided.
        Keep it concise and ensure it can be answered with factual information."""),
        ("human", f"""Base question: {base_question}
        
        Answer: {base_answer}
        
        Generate a follow-up question about player performance, team strategy, or turning points in this match:""")
    ])
    
    chain = prompt | llm
    result = chain.invoke({})
    return result.content.strip()

def generate_final_question(base_question, base_answer, followup_question, followup_answer):
    """Generate a third question based on the previous questions and answers"""
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=1.0)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an expert cricket analyst focusing on IPL.
        Based on the provided questions and answers, generate a third question that connects
        insights from both previous answers or explores a new angle about the same match/teams/players.
        Your question should provide closure to the mini-conversation or reveal something interesting
        that wasn't directly addressed in the previous questions.
        Keep it concise and ensure it can be answered with factual information."""),
        ("human", f"""First question: {base_question}
        First answer: {base_answer}
        
        Second question: {followup_question}
        Second answer: {followup_answer}
        
        Generate a third question that builds on these insights:""")
    ])
    
    chain = prompt | llm
    result = chain.invoke({})
    return result.content.strip()

def save_to_csv(question_answers, filename="cricket_qa.csv"):
    """Save question-answer pairs to CSV file"""
    file_exists = os.path.isfile(filename)
    
    with open(filename, 'a', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        
        if not file_exists:
            writer.writerow(['question : answer'])
        
        for qa_pair in question_answers:
            writer.writerow([qa_pair])
    
    print(f"Saved {len(question_answers)} question-answer pairs to {filename}")

def generate_qa_set():
    """Generate a set of 5 question-answer pairs about cricket"""
    qa_pairs = []
    
    # First generate a base question and its answer
    base_question = generate_base_question()
    print(f"Base question: {base_question}")
    base_answer = get_answer(base_question)
    qa_pairs.append(f"{base_question} : {base_answer}")
    
    # Generate follow-up question based on the base Q&A
    followup_question = generate_followup_question(base_question, base_answer)
    print(f"Follow-up question: {followup_question}")
    followup_answer = get_answer(followup_question)
    qa_pairs.append(f"{followup_question} : {followup_answer}")
    
    # Generate third question based on previous Q&As
    final_question = generate_final_question(base_question, base_answer, followup_question, followup_answer)
    print(f"Final question: {final_question}")
    final_answer = get_answer(final_question)
    qa_pairs.append(f"{final_question} : {final_answer}")
    
    # Generate two more random cricket questions for variety
    cricket_topics = [
        "current IPL standings",
        "top run scorer in the current IPL season",
        "highest wicket-taker in IPL history",
        "most sixes in an IPL match",
        "IPL auction highlights",
        "IPL team with most titles",
        "IPL match upsets",
        "best bowling figures in IPL"
    ]
    
    for _ in range(2):
        topic = random.choice(cricket_topics)
        random_question = generate_base_question() if random.random() > 0.5 else f"Tell me about {topic}"
        print(f"Random question: {random_question}")
        random_answer = get_answer(random_question)
        qa_pairs.append(f"{random_question} : {random_answer}")
    
    return qa_pairs

def main():
    """Main function to generate question-answer pairs continuously"""
    try:
        while True:
            print("\n=== Generating new set of cricket Q&A pairs ===\n")
            qa_pairs = generate_qa_set()
            save_to_csv(qa_pairs)
            
            # Wait for some time before generating the next set
            wait_time = 3600  # 1 hour in seconds
            print(f"\nWaiting for {wait_time//60} minutes before generating next set...\n")
            time.sleep(wait_time)
            
    except KeyboardInterrupt:
        print("\nScript terminated by user.")
    except Exception as e:
        print(f"\nError occurred: {str(e)}")

if __name__ == "__main__":
    main() 