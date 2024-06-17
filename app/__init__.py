from services.document_loader import AzureDocumentLoader

import os
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

document_loader = AzureDocumentLoader()