import os
from dotenv import load_dotenv
from typing import Dict, List
from langchain.schema import Document
from services.strategies.pandoc_strategy import PandocStrategy
from services.strategies.azure_strategy import AzureStrategy
from services.strategies.docling_strategy import DoclingStrategy

load_dotenv()

class ConfigurableDocumentProcessingManager:
    def __init__(self, file_to_strategy: Dict[str, str]):
        self.file_to_strategy = file_to_strategy
        self.strategies = self._initialize_strategies()

    def _initialize_strategies(self) -> Dict[str, object]:
        return {
            "PANDOC": PandocStrategy(),
            "AZURE": AzureStrategy(
                api_endpoint=os.getenv("AZURE_API_ENDPOINT"),
                api_key=os.getenv("AZURE_API_KEY")
            ),
            "DOCLING": DoclingStrategy()
        }

    def load(self, file_path: str) -> List[Document]:
        extension = file_path.split(".")[-1].lower()

        if extension not in self.file_to_strategy:
            raise ValueError(f"No strategy configured for file type: {extension}")

        strategy_name = self.file_to_strategy[extension]
        if strategy_name not in self.strategies:
            raise ValueError(f"Unknown strategy: {strategy_name}")

        strategy = self.strategies[strategy_name]
        return strategy.process(file_path)