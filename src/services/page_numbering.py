import fitz
from fuzzywuzzy import fuzz


def text_chunks_to_page_numbers(
    file_path: str, text_chunks: list[str]
) -> list[list[int]]:
    pages_grouped_per_2_range = lambda n: (
        (i, i + 1) if i < n - 1 else (i, None) for i in range(n)
    )
    # TODO: add support for other extensions such as .docx
    doc = fitz.open(file_path)
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
            score_page1, score_page2 = scores[0][0], scores[1][0]
            page_number_page1, page_number_page2 = scores[0][1], scores[1][1]
            if score_page1 > score_page2 and score_page1 >= combined_score:
                best_pages = [page_number_page1]
                highest_score = score_page1
            elif score_page2 > score_page1 and score_page2 >= combined_score:
                best_pages = [page_number_page2]
                highest_score = score_page2
            else:  # combined page pair is used as list, but a None in the pair is removed
                best_pages = [
                    p + 1 for p in page_pair if p is not None
                ]  # pages start from 0
                highest_score = combined_score

        results.append(best_pages)

    return results
