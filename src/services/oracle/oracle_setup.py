from typing import List, Callable

from langchain_core.agents import AgentAction
from langchain_core.tools import Tool

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from services.database.document_db_operations import get_summaries_by_collection
from app import llm


def get_system_prompt(collection_name: str) -> str:
    """
    Generate the system prompt for the oracle based on document summaries from a specified collection.

    This function fetches summaries of documents related to the given collection name
    and incorporates them into a system prompt. The prompt guides the oracle in deciding
    which tools to use to answer a user’s query, with specific instructions on tool usage and limitations.

    Args:
        collection_name (str): The name of the document collection from which summaries are retrieved.

    Returns:
        str: A formatted prompt string containing instructions for the oracle, including
             available tools and topics covered by the rag_search tool.
    """
    summaries = get_summaries_by_collection(collection_name)
    return f"""
You are the oracle, the great AI decision maker.  
Given the user's query, you must decide what to do with it based on the list of tools provided to you.

Key Instructions:
- Tool Usage Rules:
  - If a tool has already been used (appearing in the scratchpad) with a particular query, do NOT use that same tool with the same query again.
  - Do NOT use any tool more than three times. If a tool appears in the scratchpad three times, it is exhausted and should not be used again.

- Information Collection Strategy:
  - Always prioritize using the `rag_search` tool for topics it covers: {summaries}.
  - You should aim to collect information from a diverse range of sources before providing the answer to the user. Continue gathering information until you have thoroughly explored all relevant sources.

- Final Answer Requirement:
  - IMPORTANT: You must always conclude by using the `final_answer` tool to deliver the answer to the user. Do not provide an answer directly.
  - Even if you already know the answer or if the answer is available in the chat history, do not respond directly. Instead, pass the answer through the `final_answer` tool.
  - If none of the sources provide the answer or additional details are unavailable, proceed immediately to the `final_answer` tool, stating this explicitly.

- Citing Sources:
  - Always mention the sources you used by their exact names and include specific page numbers if applicable. Do not alter the names of sources. If the source is a URL, include the full URL in markdown format.

Remember: The `final_answer` tool is the only way you should relay an answer. Direct responses are not permitted under any circumstances.
"""


def create_scratchpad(intermediate_steps: List[AgentAction]) -> str:
    """
    Generate a formatted string (scratchpad) that summarizes completed tool actions
    based on a list of intermediate steps taken by the oracle.

    This function iterates over the list of `AgentAction` steps, filtering out actions
    that are still pending ("TBD") and formatting completed actions with the tool name,
    input, and output. The resulting list of strings is joined with a separator to create
    a scratchpad overview of the oracle's research steps.

    Args:
        intermediate_steps (List[AgentAction]): A list of actions taken by the oracle,
            where each action includes details on the tool used, input provided, and output generated.

    Returns:
        str: A formatted string containing details of each completed action, separated by "---".
    """
    research_steps = []
    for i, action in enumerate(intermediate_steps):
        if action.log != "TBD":
            # This was a completed ToolExecution
            research_steps.append(
                f"Tool: {action.tool}, input: {action.tool_input}\n"
                f"Output: {action.log}"
            )
    return "\n---\n".join(research_steps)


def create_oracle(collection_name: str, tools: List[Tool]) -> Callable:
    """
    Create an oracle language model that dynamically selects tools and responds to user input.

    Args:
        collection_name (str): The name of the collection to retrieve summaries for.
        tools (List[Tool]): A list of tools the oracle can choose from.

    Returns:
        Callable: An oracle language model configured with the system prompt, tools, and input mappings.
    """
    # Generate the system prompt based on the collection name
    system_prompt = get_system_prompt(collection_name)

    # Define the prompt template
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="chat_history"),
            ("user", "{input}"),
            ("assistant", "scratchpad: {scratchpad}"),
        ]
    )

    # Define input mappings for the oracle model
    input_mappings = {
        "input": lambda x: x["input"],
        "chat_history": lambda x: x["chat_history"],
        "scratchpad": lambda x: create_scratchpad(
            intermediate_steps=x["intermediate_steps"]
        ),
    }

    # Bind tools to the model with "auto" tool choice
    oracle = llm.model.bind_tools(tools, tool_choice="auto")

    # Return the configured oracle model with prompt and input mappings
    return input_mappings | prompt | oracle
