from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline

# from transformers import BitsAndBytesConfig # works on GPU only
import torch

"""
# Define 2 lists (a blacklist consists of banned topics, a whitelist consists of allowed topics), e.g.:

blacklist_topics = [
    "illegal",
    "violence",
    "harm",
    "hate",
    "discrimination",
    "sex",
    "sensitive information",
    "suicide",
    "politics",
    "religion"
    "conspiracy theory",
    "offensive",
    "drugs",
    "scam",
    "fraud",
    "dangerous",
    "hacking",
    "weapons"
]

whitelist_topics = [
    "product information",
    "store",
    "gift cards",
    "promotions",
    "pricing",
    "discounts",
    "recommendations",    
    "store policies",
    "inventory",
    "shipping",
    "payment",
    "customer service",
    "returns",
    "warranties",
    "support",
    "order tracking",
    "membership"
]

# Define the topic scanner and define thresholds for each list
# You can also choose to use empty lists (e.g. blacklist without whitelist):
topic_scanner = TopicScanner(blacklist_topics=blacklist_topics, blacklist_threshold=0.9, 
                             whitelist_topics=whitelist_topics, whitelist_threshold=0.7)

# Apply scanning (if is_valid is False, the prompt should not be allowed):
# risk_score is a value in [0, 1] indicating the risk
is_valid, risk_score = topic_scanner.blacklist_scan("This is your text")
is_valid, risk_score = topic_scanner.whitelist_scan("This is your text")
# ...
"""


class TopicScanner:
    def __init__(
        self,
        blacklist_topics: list[str] = [],
        blacklist_threshold: float = 0.8,
        whitelist_topics: list[str] = [],
        whitelist_threshold: float = 0.8,
    ):
        self.blacklist_topics = blacklist_topics
        self.blacklist_threshold = blacklist_threshold
        self.whitelist_topics = whitelist_topics
        self.whitelist_threshold = whitelist_threshold
        # model_name = "MoritzLaurer/deberta-v3-large-zeroshot-v2.0"
        model_name = "MoritzLaurer/bge-m3-zeroshot-v2.0"
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        # nf4_config = BitsAndBytesConfig(
        #   load_in_4bit=True,
        #   bnb_4bit_quant_type="nf4",
        #   bnb_4bit_use_double_quant=False,#True,
        #   bnb_4bit_compute_dtype=torch.bfloat16
        # )
        model = AutoModelForSequenceClassification.from_pretrained(
            model_name
        )  # , quantization_config=nf4_config)
        self.zeroshot_classifier = pipeline(
            "zero-shot-classification",
            device=torch.device("cuda" if torch.cuda.is_available() else "cpu"),
            model=model,
            # truncation=True,
            # max_length=512,
            tokenizer=tokenizer,
        )

    def blacklist_scan(self, text: str) -> tuple[bool, float]:
        is_valid = False
        if text.strip() == "":
            is_valid = True
            return is_valid, 0.0
        # hypothesis_template = "The topic of this text is {}"
        hypothesis_template = "This text is about {}"

        max_score = 0.0
        if len(self.blacklist_topics) > 0:
            output_dict = self.zeroshot_classifier(
                text,
                self.blacklist_topics,
                hypothesis_template=hypothesis_template,
                multi_label=False,
            )
            max_score = max(output_dict["scores"]) if output_dict["scores"] else 0.0
            if max_score > self.blacklist_threshold:
                is_valid = False
                return is_valid, max_score
        is_valid = True
        return is_valid, max_score

    def whitelist_scan(self, text: str) -> tuple[bool, float]:
        is_valid = False
        if text.strip() == "":
            is_valid = False
            return is_valid, 1.0
        # hypothesis_template = "The topic of this text is {}"
        hypothesis_template = "This text is about {}"

        max_score = 0.0
        if len(self.whitelist_topics) > 0:
            output_dict = self.zeroshot_classifier(
                text,
                self.whitelist_topics,
                hypothesis_template=hypothesis_template,
                multi_label=False,
            )
            max_score = max(output_dict["scores"]) if output_dict["scores"] else 0.0
            if max_score > self.whitelist_threshold:
                is_valid = True
                return is_valid, 1.0 - max_score
        is_valid = False
        return is_valid, 1.0 - max_score
