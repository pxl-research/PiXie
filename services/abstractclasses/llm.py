# llm.py
from abc import ABC, abstractmethod


class LLM(ABC):
    """
    Abstract base class for language models.
    """

    def __init__(self, model_name: str):
        """
        Initialize the LLM with a model name.

        Args:
            model_name (str): The name of the model.
        """
        self.model_name = model_name
