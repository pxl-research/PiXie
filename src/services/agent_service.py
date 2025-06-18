import logging
import asyncio
from typing import Dict, List

from services.init_services import get_services
from services import source_processing
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent

from services.mcp_tools.tool_config import get_mcp_tool_configurations, ask_user
from services.prompt_manager import get_agent_system_prompt, get_tool_description


logger = logging.getLogger(__name__)

# Shared chat services
_services = get_services()

# Global variables to hold the initialized client and agent
_persistent_client = None
_agent = None


async def wait_for_agent_initialization(
    timeout: float = 15.0, poll_interval: float = 0.5
):
    """
    Waits asynchronously until the MCP agent is initialized or until a timeout is reached.

    Args:
        timeout (float): Maximum time to wait in seconds.
        poll_interval (float): Interval between checks in seconds.

    Returns:
        bool: True if agent is ready, False if timeout was reached.
    """
    global _agent

    logger.debug(
        f"Waiting for agent initialization - timeout: {timeout}s, poll_interval: {poll_interval}s"
    )

    elapsed = 0.0
    while elapsed < timeout:
        if _agent is not None:
            logger.info(f"Agent initialization confirmed - elapsed_time: {elapsed}s")
            return True
        await asyncio.sleep(poll_interval)
        elapsed += poll_interval

    logger.warning(f"Agent initialization timeout reached - elapsed_time: {elapsed}s")
    return False


class PersistentMCPClient:
    def __init__(self, configs):
        self.configs = configs
        self.client = None
        logger.debug(
            f"PersistentMCPClient initialized - config_count: {len(configs) if configs else 0}"
        )

    async def connect(self):
        try:
            logger.debug("Connecting PersistentMCPClient")
            self.client = MultiServerMCPClient(self.configs)
            logger.info("PersistentMCPClient connected successfully")
        except Exception as e:
            logger.error(f"Error connecting PersistentMCPClient: {e}", exc_info=True)
            raise

    async def disconnect(self):
        try:
            if self.client:
                logger.debug("Disconnecting PersistentMCPClient")
                await self.client.__aexit__(None, None, None)
                logger.info("PersistentMCPClient disconnected successfully")
        except Exception as e:
            logger.error(f"Error disconnecting PersistentMCPClient: {e}", exc_info=True)

    async def get_tools(self):
        try:
            if self.client:
                tools = await self.client.get_tools()
                logger.debug(f"Retrieved tools from client - tool_count: {len(tools)}")
                return tools
            else:
                logger.debug("No client available - returning empty tools list")
                return []
        except Exception as e:
            logger.error(f"Error retrieving tools from client: {e}", exc_info=True)
            return []


async def init_mcp_agent(state=None):
    """
    Initialize the MCP client and agent once.
    """
    global _persistent_client, _agent

    if _agent is not None:
        logger.info("MCP agent already initialized - skipping initialization")
        return

    logger.info("Starting MCP agent initialization")
    try:
        configs = get_mcp_tool_configurations()
        logger.debug(
            f"Retrieved MCP tool configurations - config_count: {len(configs) if configs else 0}"
        )

        _persistent_client = PersistentMCPClient(configs)
        await _persistent_client.connect()

        _mcp_tools = await _persistent_client.get_tools()
        _mcp_tools.append(ask_user)
        logger.debug(f"MCP tools prepared - total_tool_count: {len(_mcp_tools)}")

        # Werk tool beschrijvingen bij
        updated_tools = 0
        for tool in _mcp_tools:
            description = get_tool_description(tool.name)
            if description:
                tool.description = description
                updated_tools += 1

        logger.debug(f"Tool descriptions updated - updated_count: {updated_tools}")

        _agent = create_react_agent(_services["llm"].model, _mcp_tools)
        logger.info("MCP agent initialization completed successfully")

    except Exception as e:
        logger.error(f"MCP agent initialization failed: {e}", exc_info=True)
        raise


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
    """
    global _agent

    logger.debug(
        f"Starting agent execution - message_length: {len(message)}, collection: {collection_name}"
    )

    yield "⏳ Een ogenblikje geduld... Bij het opstarten hebben we even tijd nodig om de beste modellen in te laden zodat we je vragen het beste kunnen beantwoorden. Geen nood, dit is enkel bij de eerste vraag.", ""

    ready = await wait_for_agent_initialization()
    if not ready:
        logger.error("MCP agent not ready after timeout - aborting execution")
        yield "Het systeem is nog bezig met opstarten. Probeer binnen enkele seconden opnieuw.", "⏳ Systeem nog niet klaar"
        return

    yield "De AI wordt klaargemaakt om je vraag te verwerken.", "🔄 Voorbereiding"

    try:
        summaries = _services["vector_store"].get_summaries(collection_name)
        tabular_summaries = _services["tabular_vector_store"].get_summaries(
            collection_name
        )
        logger.debug(
            f"Retrieved summaries - vector_count: {len(summaries) if summaries else 0}, tabular_count: {len(tabular_summaries) if tabular_summaries else 0}"
        )

        custom_prompt = get_agent_system_prompt(
            summaries, tabular_summaries, collection_name
        )

        # ...existing code for formatted_history validation...
        logger.debug(f"formatted_history type: {type(formatted_history)}")
        logger.debug(f"formatted_history content: {formatted_history}")

        # Ensure formatted_history is a list
        if isinstance(formatted_history, str):
            logger.warning("formatted_history is string - converting to empty list")
            formatted_history = []
        elif formatted_history is None:
            formatted_history = []
        elif not isinstance(formatted_history, list):
            logger.warning(
                f"formatted_history is {type(formatted_history)} - converting to empty list"
            )
            formatted_history = []

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
            "recursion_limit": 20,
        }

        logger.debug("Starting agent stream - thread_id: 1, recursion_limit: 20")

        out = None
        async for step in _agent.astream(input_data, thread_config):
            if "agent" in step and step["agent"]["messages"]:
                message = step["agent"]["messages"][0]
                if message.content:
                    yield "De AI is bezig met redeneren op basis van je vraag.", "💬 AI denkt na..."
                elif "tool_calls" in message.additional_kwargs:
                    tool_name = message.additional_kwargs["tool_calls"][0]["function"][
                        "name"
                    ]
                    logger.debug(f"Tool call initiated - tool_name: {tool_name}")
                    yield f"De tool '{tool_name}' wordt uitgevoerd om extra informatie te verzamelen.", f"🛠 Tool wordt opgeroepen: {tool_name}"

            elif "tools" in step and step["tools"]["messages"]:
                content = step["tools"]["messages"][0].content
                if content.startswith("__user_input_required__::"):
                    question = content.replace("__user_input_required__::", "").strip()
                    logger.info(
                        f"User input required - question_length: {len(question)}"
                    )
                    yield question, ""
                    return
                logger.debug("Tool output received")
                yield "De tool heeft resultaten opgeleverd. De AI verwerkt deze nu.", "📦 Tooloutput ontvangen"

            out = step

        if out and out.get("agent") and out["agent"]["messages"]:
            final_msg = out["agent"]["messages"][0].content
            logger.debug(f"Processing final message - content_length: {len(final_msg)}")
            yield "De AI is nu de bronnen aan het verwerken.", "📚 Bronnen worden verwerkt"

            answer, sources = source_processing.split_answer_and_sources(final_msg)
            sources_list = (
                source_processing.process_sources(sources.strip()) if sources else []
            )
            enriched_sources = source_processing.enrich_sources(sources_list)
            final_answer = source_processing.format_final_answer(
                answer_text=answer,
                enriched_sources=enriched_sources,
            )

            logger.info(
                f"Agent execution completed successfully - final_answer_length: {len(final_answer)}"
            )
            yield final_answer, ""

    except RecursionError as e:
        logger.error(f"RecursionError in agent execution: {e}", exc_info=True)
        yield "De AI heeft onvoldoende informatie kunnen verzamelen om je vraag correct te beantwoorden.", "❌ Niet genoeg informatie"

    except Exception as e:
        logger.error(f"Error in agent execution: {e}", exc_info=True)
        yield f"Er is een interne fout opgetreden: {str(e)}", "🚨 Interne fout"


async def execute_agent_for_avatar(
    message: str,
    formatted_history: List[Dict[str, str]],
    collection_name: str,
) -> str:
    """
    Execute agent for avatar use - returns only final answer without intermediate updates.
    All errors are handled gracefully and never shown to the user.
    """
    global _agent

    try:
        logger.debug(
            f"Starting avatar agent execution - message_length: {len(message)}, collection: {collection_name}"
        )
        logger.debug(f"formatted_history type: {type(formatted_history)}")

        # Wait for agent initialization without showing status
        ready = await wait_for_agent_initialization()
        if not ready:
            logger.error("MCP agent not ready for avatar execution")
            return "Ik ben nog bezig met opstarten. Geef me nog een momentje en probeer dan opnieuw."

        # Ensure formatted_history is a list of dicts
        if isinstance(formatted_history, str):
            logger.warning(
                "formatted_history is string for avatar - converting to empty list"
            )
            formatted_history = []
        elif formatted_history is None:
            logger.warning(
                "formatted_history is None for avatar - converting to empty list"
            )
            formatted_history = []
        elif not isinstance(formatted_history, list):
            logger.warning(
                f"formatted_history is {type(formatted_history)} for avatar - converting to empty list"
            )
            formatted_history = []

        # Validate collection_name is a string, not a dict
        if isinstance(collection_name, dict):
            logger.error(f"collection_name is dict for avatar: {collection_name}")
            return (
                "Er is een probleem met de collectie configuratie. Probeer het opnieuw."
            )

        summaries = _services["vector_store"].get_summaries(collection_name)
        tabular_summaries = _services["tabular_vector_store"].get_summaries(
            collection_name
        )
        logger.debug(
            f"Retrieved summaries for avatar - vector_count: {len(summaries) if summaries else 0}, tabular_count: {len(tabular_summaries) if tabular_summaries else 0}"
        )

        custom_prompt = get_agent_system_prompt(
            summaries, tabular_summaries, collection_name
        )

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
            "recursion_limit": 20,
        }

        out = None
        user_input_required = False

        async for step in _agent.astream(input_data, thread_config):
            if "tools" in step and step["tools"]["messages"]:
                content = step["tools"]["messages"][0].content
                if content.startswith("__user_input_required__::"):
                    question = content.replace("__user_input_required__::", "").strip()
                    user_input_required = True
                    logger.info(
                        f"User input required for avatar - question_length: {len(question)}"
                    )
                    return question  # Return the question directly for avatar to ask

            out = step

        # Check if we got a user input request
        if user_input_required:
            return "Ik heb nog wat meer informatie nodig om je goed te kunnen helpen."

        # Process final answer
        if out and out.get("agent") and out["agent"]["messages"]:
            final_msg = out["agent"]["messages"][0].content
            answer, sources = source_processing.split_answer_and_sources(final_msg)

            # For avatar, we want a clean answer without source formatting
            if answer:
                logger.info(
                    f"Avatar agent execution completed successfully - answer_length: {len(answer.strip())}"
                )
                return answer.strip()
            else:
                logger.warning("Avatar agent execution completed but no answer found")
                return "Ik kan je vraag helaas niet beantwoorden op basis van de beschikbare informatie. Kan ik je op een andere manier helpen?"

    except Exception as e:
        # Handle different types of errors gracefully
        error_str = str(e).lower()

        if "content_filter" in error_str or "responsibleai" in error_str:
            logger.warning(f"Content filter triggered for avatar: {e}")
            return "Ik kan je daarmee niet helpen, maar ik kan je wel helpen met het vinden van producten! Waar ben je naar op zoek?"

        elif "timeout" in error_str:
            logger.error(f"Timeout in avatar agent execution: {e}")
            return "Het duurt wat langer dan verwacht. Probeer het even opnieuw."

        elif "connection" in error_str or "network" in error_str:
            logger.error(f"Connection error in avatar agent execution: {e}")
            return "Er is een verbindingsprobleem. Probeer het over een moment opnieuw."

        elif "recursion" in error_str:
            logger.error(f"RecursionError in avatar agent execution: {e}")
            return "De vraag is te complex voor me om te beantwoorden. Kun je het anders formuleren?"

        else:
            logger.error(
                f"Unexpected error in avatar agent execution: {e}", exc_info=True
            )
            return "Er ging iets mis. Kan ik je op een andere manier helpen?"

    # Fallback if nothing was returned
    logger.warning("Avatar agent execution reached fallback return")
    return "Ik begrijp je vraag niet helemaal. Kun je het anders proberen?"
