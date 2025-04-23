import logging
import asyncio
from typing import Dict, Tuple, List, Any, Optional

from services.init_services import get_agent_services
from services import source_processing
from services.chat_history import chat_history_manager
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent

from services.database.document_db_operations import get_summaries_by_collection
from services.mcp_tools.tool_config import get_mcp_tool_configurations
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
    logging.info("Initializing MCP agent ...")
    global _mcp_client, _agent
    if _agent is not None:
        return  # Already initialized

    configs = get_mcp_tool_configurations()
    logging.info(f"Initializing MCP client with configs")
    _mcp_client = await MultiServerMCPClient(configs).__aenter__()
    logging.info("MCP client initialized")
    _mcp_tools = _mcp_client.get_tools()
    logging.info("Tools loaded from MCP client")
    # Werk tool beschrijvingen bij
    for tool in _mcp_tools:
        description = get_tool_description(tool.name)
        if description:
            tool.description = description

    logging.info("Tools loaded")
    _agent = create_react_agent(_services["llm"].model, _mcp_tools)
    logging.info("Agent created")


async def execute_agent(
    message: str,
    formatted_history: List[Dict[str, str]],
    collection_name: str,
) -> Tuple[str, List[Dict]]:
    """
    Execute the agent with the given message and process the response.

    Returns:
        Tuple[str, List[Dict]]: The processed answer and any source information
    """
    logging.info(f"Executing agent ...")
    if _agent is None:
        await init_mcp_agent()
    logging.info("MCP agent initialized")

    # Build custom system prompt from document and table summaries
    summaries = get_summaries_by_collection(collection_name)
    logging.info(f"Got document summaries")
    tabular_summaries = _services["tabular_vector_store"].get_summaries_by_collection(
        collection_name
    )
    logging.info(f"Got table summaries")
    custom_prompt = get_agent_system_prompt(summaries, tabular_summaries)
    logging.info("Custom prompt defined")
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
        logging.info(f"Executing agent with input data inside try block")
        out = await _agent.ainvoke(input_data, thread_config)
        logging.info(f"Direct na ainvoke")
        content = out["messages"][-1].content

        answer, sources = source_processing.split_answer_and_sources(content)
        sources_list = (
            source_processing.process_sources(sources.strip()) if sources else []
        )
        enriched_sources = source_processing.enrich_sources(sources_list)

        final_answer = source_processing.format_final_answer(
            answer_text=answer, enriched_sources=enriched_sources
        )

        return final_answer, out["messages"]

    except RecursionError as e:
        logger.error(f"RecursionError in agent execution: {str(e)}", exc_info=True)
        return "Ik heb niet genoeg informatie om de vraag te beantwoorden.", []

    except Exception as e:
        logger.error(f"Error in agent execution: {str(e)}", exc_info=True)
        return f"Er is een fout opgetreden: {str(e)}", []
