import datetime
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage
from langchain_core.tools import Tool
from langchain_core.documents import Document
from langchain.agents import AgentExecutor, create_openai_tools_agent
from tavily import TavilyClient
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

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

def web_search(state):
    """
    Perform web search using Tavily Search and extract content with Tavily Extract
    """
    print("---PERFORMING WEB SEARCH WITH TAVILY---")
    question = state["question"]
    documents = state["documents"]

    try:
        tools = [tavily_search_tool, tavily_extract_tool]
        agent_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

        # Set up Prompt with 'agent_scratchpad'
        today = datetime.datetime.today().strftime("%B %d, %Y")
        prompt = ChatPromptTemplate.from_messages([
            ("system", f"""You are a helpful research assistant, you will be given a query and you will need to
            search the web for the most relevant information then extract content to gain more insights.
            The date today is {today}. Keep your searches focused on gathering factual information to answer the query."""),
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
        print("Agent search completed successfully")

        output_content = response.get("output", "")

        web_doc = Document(
            page_content=output_content,
            metadata={"source": "tavily_web_search", "query": question}
        )


        search_results = {"summary": output_content}

        print(f"Successfully performed web search for: {question}")


        return {
            "documents": [web_doc],
            "question": question,
            "search_results": search_results,
            "tried_web_search": True
        }

    except Exception as e:
        print(f"Error during web search: {str(e)}")
        # Return empty results but mark that we tried web search
        error_doc = Document(
            page_content=f"Web search attempted but failed with error: {str(e)}",
            metadata={"source": "tavily_web_search_error", "query": question}
        )
        return {
            "documents": [error_doc],
            "question": question,
            "search_results": {"error": str(e)},
            "tried_web_search": True
        }

# Main function for testing
def main():
    # Initial state with empty documents
    initial_state = {
        "question": "What are the latest developments in quantum computing?",
        "documents": []
    }
    
    # Run web search
    result = web_search(initial_state)
    
    # Print results
    print("\n--- SEARCH RESULTS ---")
    print(f"Question: {result['question']}")
    print(f"Search summary: {result['search_results']}")
    
    if result['documents']:
        print("\n--- DOCUMENT CONTENT ---")
        for i, doc in enumerate(result['documents']):
            print(f"Document {i+1}:")
            print(f"Source: {doc.metadata.get('source', 'Unknown')}")
            print(f"Content: {doc.page_content[:500]}...")  # Print first 500 chars
            print()

if __name__ == "__main__":
    main()


