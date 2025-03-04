from typing import TypedDict, Tuple, Dict, Any, List, Annotated, Union
import operator
import logging

from langchain_core.agents import AgentAction
from langchain_core.messages import BaseMessage
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from langgraph.types import interrupt

from services.oracle.oracle_tools import (
    rag_search,
    tabular_rag_search,
    weather_api,
    get_date,
    web_search,
    ask_user,
    final_answer,
)
from services.oracle.oracle_setup import create_oracle


class AgentState(TypedDict):
    """
    A TypedDict that represents the state of an agent during a conversation.

    Attributes:
        input (str): The user's current input or question for the agent.
        chat_history (List[BaseMessage]): A list containing the conversation history.
        collection_name (str): The name of the collection in which document summaries are stored.
        intermediate_steps (Annotated[List[Tuple[AgentAction, str]], operator.add]):
            A list of tuples tracking each intermediate step taken by the agent.
            Each tuple contains:
              - AgentAction: The action the agent has decided to take.
              - str: The output or result from that action.
    """

    input: str
    chat_history: List[BaseMessage]
    collection_name: str
    intermediate_steps: Annotated[List[Tuple[AgentAction, str]], operator.add]


def run_oracle(state: AgentState) -> Dict[str, Any]:
    """
    Execute the oracle's decision-making process to determine which tool to call based on the current state.

    This function invokes the oracle created for the specified collection, retrieves the next tool to execute and
    its arguments, and prepares an action output with a placeholder log for future updates. The returned action
    output is then added to the list of intermediate steps in the state.

    Args:
        state (AgentState): A dictionary representing the oracle's state, which includes user input,
            chat history, and intermediate steps.

    Returns:
        Dict[str, Any]: A dictionary containing the updated list of intermediate steps, including the selected tool
        and arguments.
    """
    logging.info("Running oracle decision process")
    logging.debug(f"Current intermediate steps: {state['intermediate_steps']}")

    # Create an oracle for the specified collection
    collection_name = state["collection_name"]
    tools = [
        rag_search,
        tabular_rag_search,
        weather_api,
        get_date,
        web_search,
        final_answer,
        ask_user,
    ]
    oracle = create_oracle(collection_name, tools)

    # Invoke the oracle with the given state
    out = oracle.invoke(state)

    tool_name = out.tool_calls[0]["name"]
    tool_args = out.tool_calls[0]["args"]

    # Prepare an action output with the selected tool and arguments
    action_out = AgentAction(tool=tool_name, tool_input=tool_args, log="TBD")

    return {"intermediate_steps": [action_out]}


def router(state: AgentState) -> str:
    """
    Determine the next tool to use based on the current state of intermediate steps.

    This function checks the last tool used in the intermediate steps. If the list of steps
    is empty or improperly formatted, the function defaults to selecting "final_answer" as the next step.

    Args:
        state (AgentState): A dictionary containing the current oracle state, including intermediate steps.

    Returns:
        str: The name of the tool to use next. If the format is invalid, returns "final_answer" by default.
    """
    if (
        isinstance(state["intermediate_steps"], list)
        and len(state["intermediate_steps"]) > 0
    ):
        return state["intermediate_steps"][-1].tool
    else:
        logging.warning(
            "Router detected an invalid format; defaulting to 'final_answer'"
        )
        return "final_answer"


def run_tool(state: AgentState) -> Dict[str, Any]:
    """
    Execute a tool based on the specified tool name and arguments in the current state.

    This function retrieves the tool name and input arguments from the most recent intermediate step,
    invokes the tool, and creates a new action output with the tool's response log. The result is
    added to the intermediate steps list.

    Args:
        state (AgentState): A dictionary representing the oracle's state, containing intermediate steps.

    Returns:
        Dict[str, Any]: A dictionary with an updated list of intermediate steps, including the executed
        tool and its response log.
    """
    # Map of tool functions based on tool names
    tool_str_to_func = {
        "rag_search": rag_search,
        "tabular_rag_search": tabular_rag_search,
        "weather_api": weather_api,
        "get_date": get_date,
        "web_search": web_search,
        "final_answer": final_answer,
        "ask_user": ask_user,
    }

    tool_name = state["intermediate_steps"][-1].tool
    tool_args = state["intermediate_steps"][-1].tool_input

    logging.info(f"Invoking tool: {tool_name} with input: {tool_args}")

    # Ensure collection name is added for rag_search tool
    if tool_name == "rag_search" or tool_name == "tabular_rag_search":
        collection_name = state.get("collection_name")
        if collection_name is not None:
            tool_args["collection_name"] = collection_name
        else:
            logging.error("Collection name is missing in state.")
            raise ValueError("Collection name is required for rag_search tool.")

    tool_function = tool_str_to_func.get(tool_name)
    if tool_function is None:
        logging.error(
            f"Tool '{tool_name}' not recognized. Ensure it is correctly defined."
        )
        raise ValueError(f"Unknown tool: {tool_name}")

    out = tool_function.invoke(input=tool_args)

    action_out = AgentAction(tool=tool_name, tool_input=tool_args, log=str(out))
    logging.debug(f"Tool output: {out}")

    return {"intermediate_steps": [action_out]}


def initialize_graph() -> StateGraph:
    """
    Initialize the state graph with nodes, edges, and entry points for oracle and tools.

    Returns:
        StateGraph: The initialized state graph with nodes and edges configured.
    """
    graph = StateGraph(AgentState)

    # Add nodes to the graph
    graph.add_node("oracle", run_oracle)
    graph.add_node("rag_search", run_tool)
    graph.add_node("tabular_rag_search", run_tool)
    graph.add_node("weather_api", run_tool)
    graph.add_node("get_date", run_tool)
    graph.add_node("web_search", run_tool)
    graph.add_node("final_answer", run_tool)
    graph.add_node("ask_user", run_tool)

    # Specify the entry node
    graph.set_entry_point("oracle")

    # Add conditional edges using the router function
    graph.add_conditional_edges(source="oracle", path=router)

    # Create edges from each tool back to the oracle, except for the final answer
    tools = [
        rag_search,
        tabular_rag_search,
        weather_api,
        get_date,
        web_search,
        ask_user,
    ]
    for tool_obj in tools:
        graph.add_edge(tool_obj.name, "oracle")

    # Add an edge from final_answer to END to terminate the graph
    graph.add_edge("final_answer", END)

    return graph


def compile_graph(graph: StateGraph) -> Any:
    """
    Compile the state graph to produce a runnable instance.

    Args:
        graph (StateGraph): The state graph with nodes and edges configured.

    Returns:
        Any: The compiled oracle graph ready for execution.
    """
    checkpointer = MemorySaver()
    return graph.compile(checkpointer=checkpointer)
