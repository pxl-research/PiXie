import logging
from typing import Dict, Tuple, List, Any, Optional

from app import llm, tabular_vector_store
from services import source_processing
from services.chat_history import chat_history_manager
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent

from services.database.document_db_operations import get_summaries_by_collection
from services.mcp_tools.tool_config import get_mcp_tool_configurations
from services.prompt_manager import get_agent_system_prompt, get_tool_description

logger = logging.getLogger(__name__)


async def execute_agent(
    client: MultiServerMCPClient,
    message: str,
    custom_prompt: str,
    formatted_history: List[Dict[str, str]],
    collection_name: str,
) -> Tuple[str, List[Dict]]:
    """
    Execute the agent with the given message and process the response.

    Returns:
        Tuple[str, List[Dict]]: The processed answer and any source information
    """
    tools = client.get_tools()

    # Werk tool beschrijvingen bij
    for tool in tools:
        description = get_tool_description(tool.name)
        if description:
            tool.description = description

    agent = create_react_agent(llm.model, tools)

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
        out = await agent.ainvoke(input_data, thread_config)
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