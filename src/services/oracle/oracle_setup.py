from typing import List, Callable

from langchain_core.agents import AgentAction
from langchain_core.tools import Tool

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from services.database.document_db_operations import get_summaries_by_collection
from app import llm, tabular_vector_store


def get_system_prompt(collection_name: str) -> str:
    """
    Generate the system prompt for the oracle based on document summaries from a specified collection.

    This function fetches summaries of documents related to the given collection name
    and incorporates them into a system prompt. The prompt guides the oracle in deciding
    which tools to use to answer a user's query, with specific instructions on tool usage and limitations.

    Args:
        collection_name (str): The name of the document collection from which summaries are retrieved.

    Returns:
        str: A formatted prompt string containing instructions for the oracle, including
             available tools and topics covered by the rag_search and tabular_rag_search tools.
    """

    summaries = get_summaries_by_collection(collection_name)
    tabular_summaries = tabular_vector_store.get_summaries_by_collection(
        collection_name
    )

    return f"""
You are the oracle, the great AI decision maker.
Given the user's query, you must decide what to do with it based on the list of tools provided to you.

**Key Instructions:**

**Tool Usage Rules:**

- **Single Use per Query and Tool**:
  - For each specific query, apply a tool only once.
  - Before using a tool, check the scratchpad to ensure that the same query has not been used with that tool already.

- **Tool Usage Limit**:
  - Each tool can be used up to **three times** in total.
  - Once a tool appears three times in the scratchpad, consider it fully utilized and do not use it again.

**Information Collection Strategy**:

- Prioritize using the `rag_search` tool for topics it covers: {summaries}.
- Prioritize using the `tabular_rag_search` tool for topics it covers: {tabular_summaries}.
- You may reformulate or split the question into sub-questions to gather more information.
- Aim to collect information from diverse sources before providing the final answer.
- If the question is time-sensitive, retrieve the current date first.
- When you use `tabular_rag_search` and you get a json as answer, you must continue to the final answer and present the json.

**User Interaction:**

- If you need additional information or clarification to properly answer the user's question, use the `ask_user` tool.
- Only use the `ask_user` tool when the information is necessary and cannot be inferred from context.
- Frame your questions clearly and specifically to help the user provide the exact information you need.
- After receiving a response from the user, continue with the appropriate tools to answer their original query.

**Final Answer Requirement**:

- **Important**: Always conclude by using the `final_answer` tool to deliver the answer to the user.
- Do not provide an answer directly; use the `final_answer` tool even if you already know the answer or it's available in the chat history.
- If no sources provide the answer or additional details are unavailable, proceed immediately to the `final_answer` tool and state this explicitly.

**Citing Sources**:

- Mention the sources you used by their exact names and include specific page numbers if applicable.
- Keep the original names of the sources.
- Only include the sources listed directly with the chunks.
- If the source is a URL, include the full URL in markdown format.

**Remember**: The `final_answer` tool is the only way you should relay an answer. Direct responses are not permitted under any circumstances.

**Scratchpad Usage**:

- Always review the scratchpad before deciding to use a tool.
- Use the scratchpad to keep track of tool usage and ensure compliance with the above rules.

**Examples**:

- *Correct Usage*:
  - **Tool**: `web_search`, **Query**: "Latest advancements in AI".
  - **Note**: Since this query hasn't been used with `web_search` before, and `web_search` hasn't been used three times yet, it's acceptable.

- *Incorrect Usage*:
  - **Tool**: `web_search`, **Query**: "Latest advancements in AI".
  - **Issue**: This query has already been used with `web_search`; do not repeat.

- **Tool Limit Exceeded**:
  - If `web_search` appears three times in the scratchpad, do not use it again.

**Example  output from the `tabular_rag_search` tool**:

- **Tool**: `tabular_rag_search`, **Query**: "Hoeveel pizza's met kaas worden er bij Giovanni verkocht?".
- **Output**: `{"aantal":24}`.
- **Note**: The output is given in JSON format. The final answer should be: "Er worden 24 pizza's met kaas verkocht bij Giovanni."

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
