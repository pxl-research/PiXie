import os
from string import Template

# Pad naar de prompt template bestanden
PROMPT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "assets", "helper"
)


def load_prompt(filename):
    """Laad een prompt template uit een bestand."""
    filepath = os.path.join(PROMPT_DIR, filename)
    with open(filepath, "r", encoding="utf-8") as file:
        return file.read()


def get_agent_system_prompt(summaries, tabular_summaries):
    """Formatteer de system prompt voor de agent met de juiste waarden."""
    system_prompt_template = load_prompt("agent_system_prompt.txt")
    citation_guidelines = load_prompt("citation_guidelines.txt")

    return system_prompt_template.format(
        summaries=summaries,
        tabular_summaries=tabular_summaries,
        citation_guidelines=citation_guidelines,
    )


def get_tool_description(tool_name):
    """Haal een tool beschrijving op uit een bestand als deze bestaat."""
    filename = f"tool_description_{tool_name}.txt"
    try:
        return load_prompt(filename)
    except FileNotFoundError:
        return None
