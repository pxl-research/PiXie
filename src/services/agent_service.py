import logging
import asyncio
from typing import Dict, Tuple, List, Any, Optional

from services.init_services import get_agent_services
from services import source_processing
from services.chat_history import chat_history_manager
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent

from services.database.document_db_operations import get_summaries_by_collection
from services.mcp_tools.tool_config import get_mcp_tool_configurations, ask_user
from services.prompt_manager import get_agent_system_prompt, get_tool_description

logger = logging.getLogger(__name__)

# Shared chat services
_services = get_agent_services()

# Global variables to hold the initialized client and agent
_mcp_client = None
_agent = None


async def init_mcp_agent():
    """
    Initialize the MCP client and agent once.
    """
    global _mcp_client, _agent
    if _agent is not None:
        return  # Already initialized

    configs = get_mcp_tool_configurations()
    _mcp_client = await MultiServerMCPClient(configs).__aenter__()
    _mcp_tools = _mcp_client.get_tools()
    _mcp_tools.append(ask_user)
    # Werk tool beschrijvingen bij
    for tool in _mcp_tools:
        description = get_tool_description(tool.name)
        if description:
            tool.description = description

    _agent = create_react_agent(_services["llm"].model, _mcp_tools)


async def execute_agent(
    message: str,
    formatted_history: List[Dict[str, str]],
    collection_name: str,
):
    """
    Asynchronously executes a multi-step agent process with tool usage and streaming updates.

    This function feeds a user message and chat history into a pre-initialized MCP-based agent,
    which may invoke tools and request additional user input during reasoning. The function yields
    intermediate status messages that can be used to update the UI in real time (e.g., "thinking...",
    "calling tool..."). If the agent requests user input mid-process, it yields (question, "") and exits.

    Final output is returned as (answer, "") once reasoning is complete.

    Args:
        message (str): The new user message to be processed by the agent.
        formatted_history (List[Dict[str, str]]): Previous conversation messages formatted for the agent.
        collection_name (str): The name of the document collection used for summaries and RAG search.

    Yields:
        Tuple[str, str]: Intermediate or final responses to be displayed in the UI.
                        First element is either the final answer or a question for the user.
                        Second element is a transient status message or empty string.
    """

    yield "", "🔄 Preparing AI to process your question..."
    if _agent is None:
        await init_mcp_agent()

    # Build custom system prompt from document and table summaries
    summaries = get_summaries_by_collection(collection_name)
    tabular_summaries = _services["tabular_vector_store"].get_summaries_by_collection(
        collection_name
    )
    custom_prompt = get_agent_system_prompt(summaries, tabular_summaries)
    input_data = {
        "messages": (
            [{"role": "system", "content": custom_prompt}]
            + formatted_history
            + [{"role": "user", "content": message}]
        ),
        "collection_name": collection_name,
    }

    thread_config = {
        "configurable": {"thread_id": 1},
        "recursion_limit": 5,
    }

    try:
        out = None
        async for step in _agent.astream(input_data, thread_config):

            # 1. Tool wordt opgeroepen
            if "agent" in step and step["agent"]["messages"]:
                message = step["agent"]["messages"][0]
                if message.content:
                    yield "", f"💬 AI denkt na .."
                elif "tool_calls" in message.additional_kwargs:
                    tool_name = message.additional_kwargs["tool_calls"][0]["function"][
                        "name"
                    ]
                    yield "", f"🛠 Tool wordt opgeroepen: {tool_name}"

            # 2. Tool geeft output terug
            elif "tools" in step and step["tools"]["messages"]:
                content = step["tools"]["messages"][0].content
                if content.startswith("__user_input_required__::"):
                    question = content.replace("__user_input_required__::", "").strip()
                    yield question, ""  # Signaal aan Gradio: wacht op user input
                    return
                yield "", f"📦 Tooloutput ontvangen"

            out = step

        if out and out.get("agent") and out["agent"]["messages"]:
            final_msg = out["agent"]["messages"][0].content
            answer, sources = source_processing.split_answer_and_sources(final_msg)
            sources_list = (
                source_processing.process_sources(sources.strip()) if sources else []
            )
            enriched_sources = source_processing.enrich_sources(sources_list)
            final_answer = source_processing.format_final_answer(
                answer_text=answer,
                enriched_sources=enriched_sources,
            )

            yield final_answer, ""

    except RecursionError as e:
        logger.error(f"RecursionError in agent execution: {str(e)}", exc_info=True)
        yield "Ik heb niet genoeg informatie om de vraag te beantwoorden.", ""

    except Exception as e:
        logger.error(f"Error in agent execution: {str(e)}", exc_info=True)
        yield f"Er is een fout opgetreden: {str(e)}", ""
