from services import blob_service
import re


def strip_sources(text: str) -> str:
    """
    Strip everything after the keyword 'Bronnen:' from the given text.

    Parameters:
    - text: str
        The input text from which to remove sources.

    Returns:
    - str: The text without the sources section.
    """
    # Zoek naar de positie van het keyword 'Bronnen:'
    keyword_position = text.find("Bronnen:")
    return text[:keyword_position].strip() if keyword_position != -1 else text.strip()


def process_full_answer(full_answer):
    """
    Process the full answer to separate the main answer and sources, then format the final output.

    Parameters:
    - full_answer: str
        The full answer text, which may contain the main answer and a sources section.

    Returns:
    - str: The formatted answer with enriched sources, or the original answer if sources are absent.
    """
    if full_answer != "Ik heb niet genoeg informatie om de vraag te beantwoorden.":
        if "[BRONNEN]" in full_answer:
            answer_text, sources_text = full_answer.split("[BRONNEN]", 1)
            sources_list = process_sources(sources_text.strip().splitlines())
            answer_text = answer_text.strip()
        else:
            answer_text = full_answer
            sources_list = []

        enriched_sources = enrich_sources(sources_list)
        return format_final_answer(answer_text, enriched_sources)
    else:
        return full_answer


def process_sources(sources_text):
    """
    Extract and deduplicate sources from the given text.

    Parameters:
    - sources_text: str
        The text containing sources in a specific format.

    Returns:
    - list: A list of unique sources formatted as "file_name, pagina page_number".
    """
    pattern = r"[^,\s]+\.[^\s,]+, pagina [^\s\]]+"
    sources_list = re.findall(pattern, sources_text)
    # Verwijder duplicaten terwijl de volgorde behouden blijft
    seen = set()
    deduped_sources = []
    for source in sources_list:
        if source not in seen:
            deduped_sources.append(source.strip())
            seen.add(source)
    return deduped_sources


def enrich_sources(sources_list):
    """
    Enrich sources with hyperlinks and remove duplicates.

    Parameters:
    - sources_list: list
        A list of sources in the format "file_name, pagina page_number".

    Returns:
    - list: A list of enriched sources with hyperlinks to specific pages in the document.
    """
    enriched_sources = []
    seen = set()
    for source_line in sources_list:
        file_name, page_numbers = parse_source_line(source_line)
        url = blob_service.generate_blob_url(file_name)
        if page_numbers:
            first_page = page_numbers.split("-")[0].strip()
            if first_page.lower() != "n.v.t.":
                url += f"#page={first_page}"
        source_entry = f"[{file_name}, pagina {page_numbers}]({url})"
        if source_entry not in seen:
            enriched_sources.append(source_entry)
            seen.add(source_entry)
    return enriched_sources


def parse_source_line(source_line):
    """
    Parse a source line into its file name and page numbers.

    Parameters:
    - source_line: str
        A single source entry in the format "file_name, pagina page_numbers".

    Returns:
    - tuple: A tuple containing the file name and page numbers, or None if no page numbers are present.
    """
    if ", pagina " in source_line:
        return source_line.split(", pagina ", 1)
    return source_line.strip(), None


def format_final_answer(answer_text, enriched_sources):
    """
    Format the final answer by appending a formatted sources section, if available.

    Parameters:
    - answer_text: str
        The main answer content.
    - enriched_sources: list
        A list of enriched sources to include in the final output.

    Returns:
    - str: The final formatted answer with sources listed in numbered order, or the answer alone if no sources exist.
    """
    if enriched_sources:
        sources_formatted = "\n".join(
            f"{idx + 1}. {source}" for idx, source in enumerate(enriched_sources)
        )
        return f"{answer_text}\n\nBronnen:\n{sources_formatted}"
    return answer_text
