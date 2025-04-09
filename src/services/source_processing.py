from services import blob_service
import re
import logging
from typing import List, Tuple, Union


def parse_page_numbers(pages_str: str) -> List[Tuple[int, int]]:
    """
    Parse and group page numbers from a string, separating contiguous ranges.

    Parameters:
    - pages_str: str
        A string containing page numbers in formats like "1, 2, 4" or "1-2 en 4".

    Returns:
    - List[Tuple[int, int]]: A list of tuples where each tuple represents a range (start, end).
    """
    pages = sorted(
        int(page) for page in re.split(r"[,\s\-en]+", pages_str) if page.isdigit()
    )
    if not pages:
        return []

    grouped_pages = []
    start = pages[0]
    end = start

    for i in range(1, len(pages)):
        if pages[i] == end + 1:
            end = pages[i]
        else:
            grouped_pages.append((start, end))
            start = pages[i]
            end = start

    grouped_pages.append((start, end))
    return grouped_pages


def parse_source_line(
    source_line: str,
) -> List[Union[str, Tuple[str, Union[int, None], Union[int, None]]]]:
    """
    Parse a source line into its file name and individual page ranges or retain as a URL.

    Parameters:
    - source_line: str
        A single source entry, formatted as "file_name (pagina page_numbers)" or a URL in markdown format.

    Returns:
    - List[Union[str, Tuple[str, Union[int, None], Union[int, None]]]]:
        A list containing:
        - tuples of (file_name, start page, end page) for file sources
        - strings for sources already in markdown URL format or sources without page numbers.
    """
    if re.match(r"\[.*?\]\(http.*?\)", source_line):
        return [source_line]  # Keep URLs intact

    source_line = re.sub(r"^Bron(?:nen)?:\s*", "", source_line.strip())
    match = re.match(r"^(.+?)\s+pagina\s+(\d+)$", source_line)

    if match:
        file_name = match.group(1).strip()
        pages_str = match.group(2).strip()

        if not pages_str:
            return [file_name]

        grouped_pages = parse_page_numbers(pages_str)
        if not grouped_pages:
            return [file_name]

        return [(file_name, start, end) for start, end in grouped_pages]

    return [source_line.strip()]


def split_sources(sources_text: str) -> List[str]:
    """
    Split sources based on semicolons, commas, 'en', and newlines as separators.
    Only split on separators that are outside parentheses.

    Parameters:
    - sources_text: str
        The full text containing multiple sources to be split.

    Returns:
    - List[str]: A list of split source strings.
    """
    sources = []
    current = []
    paren_level = 0

    i = 0
    while i < len(sources_text):
        char = sources_text[i]

        if char == "(":
            paren_level += 1
            current.append(char)
        elif char == ")":
            paren_level -= 1
            current.append(char)
        elif paren_level == 0 and (
            char == ";"
            or char == "\n"
            or (char == "," and not re.match(r"\d", sources_text[i + 1 : i + 2]))
        ):
            sources.append("".join(current).strip())
            current = []
        elif paren_level == 0 and sources_text[i : i + 3] == " en":
            sources.append("".join(current).strip())
            current = []
            i += 2
        else:
            current.append(char)

        i += 1

    if current:
        sources.append("".join(current).strip())

    return sources


def process_sources(
    sources_text: str,
) -> List[Union[str, Tuple[str, Union[int, None], Union[int, None]]]]:
    """
    Extract and deduplicate sources from the given text.

    Parameters:
    - sources_text: str
        The text containing sources in various formats.

    Returns:
    - List[Union[str, Tuple[str, Union[int, None], Union[int, None]]]]:
        A list of unique sources, where each entry is either:
        - A tuple (file_name, first_page, last_page) if pages are present.
        - A string if the source is a URL or lacks page numbers.
    """
    sources_list = [
        re.sub(r"^\d+\.\s*", "", re.sub(r"^-*\s*Bron(?:nen)?:\s*", "", source.strip()))
        for source in split_sources(sources_text)
    ]


    seen = set()
    deduped_sources = []
    for source in sources_list:
        parsed_sources = parse_source_line(source)
        for parsed_source in parsed_sources:
            if parsed_source not in seen:
                deduped_sources.append(parsed_source)
                seen.add(parsed_source)

    return deduped_sources


def enrich_sources(
    sources_list: List[Union[str, Tuple[str, Union[int, None], Union[int, None]]]],
) -> List[str]:
    """
    Enrich sources with hyperlinks and remove duplicates.

    Parameters:
    - sources_list: List[Union[str, Tuple[str, Union[int, None], Union[int, None]]]]
        A list of sources, where each entry is either:
        - A tuple in the format (file_name, first_page, last_page)
        - A string containing an existing URL in markdown format.

    Returns:
    - List[str]: A list of enriched sources with hyperlinks to specific pages in the document.
    """
    enriched_sources = []
    seen = set()

    for source in sources_list:
        if isinstance(source, str) and re.match(r"\[.*?\]\(http.*?\)", source):
            if source not in seen:
                enriched_sources.append(source)
                seen.add(source)
            continue

        # Skip invalid sources that don't have exactly 3 values
        try:
            file_name, first_page, last_page = source
        except ValueError:
            print(f"Skipping invalid source: {source}")
            continue

        if first_page is None:
            source_entry = f"{file_name}"
            if source_entry not in seen:
                enriched_sources.append(source_entry)
                seen.add(source_entry)
            continue

        url = blob_service.generate_blob_url(file_name.strip())
        if first_page is not None:
            url += f"#page={first_page}"

        page_text = (
            f"pagina {first_page}"
            if first_page == last_page
            else f"pagina {first_page}-{last_page}"
        )

        source_entry = f"[{file_name}, {page_text}]({url})"

        if source_entry not in seen:
            enriched_sources.append(source_entry)
            seen.add(source_entry)

    return enriched_sources


def format_final_answer(answer_text: str, enriched_sources: List[str]) -> str:
    """
    Format the final answer by appending a formatted sources section, if available.

    Parameters:
    - answer_text: str
        The main answer content.
    - enriched_sources: List[str]
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


def split_answer_and_sources(content: str) -> Tuple[str, str]:
    """
    Split the content into answer and sources.

    Parameters:
    - content: str
        The content to be split.

    Returns:
    - Tuple[str, str]: A tuple containing the answer and sources.
    """
    if "Bron:" in content:
        answer, sources = content.split("Bron:", 1)
        return answer.strip(), sources.strip()
    return content.strip(), ""
