from typing import Optional, Callable
import subprocess
import os
import shutil
import logging
import fitz  # For PDF handling (PyMuPDF)
from fuzzywuzzy import fuzz

import io
import re
from tempfile import NamedTemporaryFile
from typing import Any


def _match_chunks_and_page_numbers(
    doc: Any, text_chunks: list[str]
) -> list[Optional[int]]:
    """
    Maps text chunks to the first page number based on fuzzy matching in a PDF file.

    Parameters:
    - doc: Any
        The PDF document.
    - text_chunks: list[str]
        The list of text chunks to map to pages.

    Returns:
    - list[Optional[int]]: A list where each element is the first page number corresponding
      to the respective text chunk, or None if not applicable.
    """
    pages_grouped_per_2_range = lambda n: (
        (i, i + 1) if i < n - 1 else (i, None) for i in range(n)
    )

    # doc: Any = fitz.open(file_path)
    num_pages = doc.page_count

    results = []

    for text_chunk in text_chunks:
        best_pages = []
        highest_score = 0

        for page_pair in pages_grouped_per_2_range(num_pages):
            combined_text = ""
            scores = []
            for page_num in page_pair:
                if page_num is None:
                    continue
                page_text = doc[page_num].get_text()
                score = fuzz.partial_ratio(text_chunk, page_text)
                scores.append((score, page_num + 1))  # pages start from 0
                combined_text += page_text

            combined_score = fuzz.partial_ratio(text_chunk, combined_text)
            if combined_score <= highest_score:
                continue
            score_page1, score_page2 = scores[0][0], (
                scores[1][0] if len(scores) > 1 else 0
            )
            page_number_page1, page_number_page2 = scores[0][1], (
                scores[1][1] if len(scores) > 1 else None
            )

            if score_page1 > score_page2 and score_page1 >= combined_score:
                best_pages = [page_number_page1]
                highest_score = score_page1
            elif score_page2 > score_page1 and score_page2 >= combined_score:
                best_pages = [page_number_page2]
                highest_score = score_page2
            else:
                best_pages = [p + 1 for p in page_pair if p is not None]
                highest_score = combined_score

        # Append the first page of the best_pages to results
        if best_pages:
            results.append(best_pages[0])

    return results if len(results) > 0 else [None for _ in text_chunks]


def _pdf_matching(file_path: str, text_chunks: list[str]) -> list[Optional[int]]:
    """
    Maps text chunks to the first page number based on fuzzy matching in a PDF file.

    Parameters:
    - file_path: str
        The path to the PDF document.
    - text_chunks: list[str]
        The list of text chunks to map to pages.

    Returns:
    - list[Optional[int]]: A list where each element is the first page number corresponding
      to the respective text chunk, or None if not applicable.
    """
    try:
        doc: Any = fitz.open(file_path)
        results = _match_chunks_and_page_numbers(doc, text_chunks)
    except Exception as e:
        return [None for _ in text_chunks]
    finally:
        doc.close()
    return results


def _docx_or_pptx_matching(
    file_path: str, text_chunks: list[str]
) -> list[Optional[int]]:
    """
    Maps text chunks to the first page number based on fuzzy matching in a docx or pptx file.

    Parameters:
    - file_path: str
        The path to the docx document or pptx presentation.
    - text_chunks: list[str]
        The list of text chunks to map to pages.

    Returns:
    - list[Optional[int]]: A list where each element is the first page number corresponding
      to the respective text chunk, or None if not applicable.
    """
    docx_or_pptx_file_path = file_path
    file_extension = os.path.splitext(file_path)[1].lower()

    # Create a temporary file to store the PDF output
    with NamedTemporaryFile(suffix=".pdf") as temp_pdf:
        temp_pdf.flush()
        temp_pdf.seek(0)  # start at beginning

        output_dir = os.path.dirname(temp_pdf.name)
        temp_output_pdf = os.path.join(
            output_dir,
            os.path.basename(docx_or_pptx_file_path).replace(file_extension, ".pdf"),
        )
        try:
            subprocess.run(
                [
                    "libreoffice",
                    "--headless",
                    "--convert-to",
                    "pdf",
                    docx_or_pptx_file_path,
                    "--outdir",
                    output_dir,
                ],
                check=True,
                stdout=open(os.devnull, "wb"),
            )
        except subprocess.CalledProcessError as e:
            return [None for _ in text_chunks]

        # Rename the output file to the desired name (temporary pdf)
        try:
            shutil.move(temp_output_pdf, temp_pdf.name)
        except Exception as e:
            return [None for _ in text_chunks]

        # Text chunk matching for on temporary pdf
        try:
            pdf_document: Any = fitz.open(temp_pdf.name, filetype="pdf")
            results = _match_chunks_and_page_numbers(pdf_document, text_chunks)
        except Exception as e:
            return [None for _ in text_chunks]
        finally:
            pdf_document.close()
        return results


def text_chunks_to_page_numbers(
    file_path: str, text_chunks: list[str]
) -> list[Optional[int]]:
    """
    Maps text chunks to page numbers based on the file type.
    For PDF files, returns the first page number where the chunk starts.
    For unsupported file types, returns None.

    Parameters:
    - file_path: str
        The path to the document file.
    - text_chunks: list[str]
        The list of text chunks to map to pages.

    Returns:
    - list[Optional[int]]: A list where each element is the first page number
      corresponding to the respective text chunk, or None if not applicable.
    """
    # Determine the file extension
    file_extension = os.path.splitext(file_path)[1].lower()

    if file_extension == ".pdf":
        return _pdf_matching(file_path, text_chunks)
    elif file_extension in (".docx", ".pptx"):
        return _docx_or_pptx_matching(file_path, text_chunks)
    else:
        logging.warning(
            f"File type {file_extension} is not yet supported for page number extraction."
        )
        return [None for _ in text_chunks]
