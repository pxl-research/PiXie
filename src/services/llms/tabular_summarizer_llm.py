from typing import Optional
import logging
from langchain.schema import SystemMessage
import pandas as pd
import numpy as np

from services.abstractclasses.llm import LLM


def sample_dataframe_description_dict(df: pd.DataFrame, n: int = 10) -> dict:
    """
    Sample up to n rows evenly spaced across the DataFrame and format the
    column names and sample data for an LLM to describe.

    Parameters:
        df (pd.DataFrame): The DataFrame to sample.
        n (int): Maximum number of rows to sample (default is 10).

    Returns:
        dict: A dictionary with column names and sample rows.
    """
    # ensure n doesn't exceed the number of available rows
    if n < 0:
        n = 0
    elif n > len(df):
        n = len(df)
    indices = list(
        map(int, np.linspace(0, len(df) - 1, n))
    )  # evenly spaced row indices
    sampled_rows = df.iloc[indices]  # sample n evenly spaced rows

    dict_table_data = {
        "columns": list(df.columns),
        "sample_rows": sampled_rows.to_dict(orient="records"),
    }
    return dict_table_data


class TabularSummarizerLLM:
    """
    Utility class for summarizing tabular data using a language model (LLM).
    It generates a global summary of the table based on its structure and sample data.

    Attributes:
        system_prompt_template (str): Predefined prompt template used to
            instruct the LLM to describe the table.
        llm (LLM): An instance of a language model used to generate summaries.
    """

    def __init__(self, llm: LLM):
        self.system_prompt_template = """
            You are a helpful assistant specialized in summarization of given table data.
            Given the following table structure, please describe the contents of the table.
            
            COLUMNS:
            
            {columns}
            =========
            
            SAMPLE DATA:
            
            {sample_rows}
            =========
            Describe the table in a few sentences, only describe the table globally, not per column:
        """
        self.llm = llm

    def generate(self, df: pd.DataFrame, n: int = 10) -> Optional[str]:
        """
        Generates a concise global description of the input
        DataFrame's structure and sample data.

        Args:
            df (pd.DataFrame): The input DataFrame to summarize.
            n (int): Maximum number of rows to sample (default is 10).

        Returns:
            Optional[str]: A summary describing the table's overall structure and content.
                Returns None if an error occurs during summary generation.
        """
        table_data = sample_dataframe_description_dict(df=df, n=n)

        system_prompt = self.system_prompt_template.format(
            columns=table_data["columns"], sample_rows=table_data["sample_rows"]
        )

        system_message = SystemMessage(content=system_prompt)
        try:
            response = self.llm.model.invoke([system_message])
            return response.content
        except Exception as e:
            logging.error(f"Error: {str(e)}")
        return None
