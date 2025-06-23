"""
Configuratie voor Conversatie Logging

Dit bestand bevat configuratie opties voor de conversatie logging functionaliteit.
"""

import os
from dataclasses import dataclass


@dataclass
class ConversationLoggingConfig:
    """Configuratie voor conversatie logging"""

    # Database configuratie
    enable_logging: bool = True
    log_user_ip: bool = False  # Privacy overweging
    log_user_agent: bool = True

    # Performance configuratie
    max_content_length: int = 10000  # Max lengte van content in characters
    batch_size: int = 100  # Voor bulk operations

    # Retention configuratie
    max_session_duration_hours: int = 24  # Auto-end sessies na X uren
    cleanup_logs_after_days: int = 365  # Behoud logs voor X dagen

    # Analytics configuratie
    enable_analytics: bool = True
    cache_analytics_minutes: int = 15  # Cache analytics results

    # Export configuratie
    enable_export: bool = True
    export_formats: list = None

    def __post_init__(self):
        if self.export_formats is None:
            self.export_formats = ["json", "csv"]

        # Override from environment variables
        self.enable_logging = (
            os.getenv("CONVERSATION_LOGGING_ENABLED", "true").lower() == "true"
        )
        self.log_user_ip = os.getenv("LOG_USER_IP", "false").lower() == "true"
        self.cleanup_logs_after_days = int(
            os.getenv("LOG_RETENTION_DAYS", str(self.cleanup_logs_after_days))
        )


# Singleton config instance
conversation_logging_config = ConversationLoggingConfig()


def get_logging_config() -> ConversationLoggingConfig:
    """
    Haal de logging configuratie op.

    Returns:
        ConversationLoggingConfig instance
    """
    return conversation_logging_config


def update_logging_config(**kwargs) -> None:
    """
    Update logging configuratie runtime.

    Args:
        **kwargs: Configuratie parameters om te updaten
    """
    global conversation_logging_config

    for key, value in kwargs.items():
        if hasattr(conversation_logging_config, key):
            setattr(conversation_logging_config, key, value)
        else:
            raise ValueError(f"Unknown configuration parameter: {key}")


def is_logging_enabled() -> bool:
    """
    Check of logging enabled is.

    Returns:
        bool: True als logging enabled is
    """
    return conversation_logging_config.enable_logging


def should_log_ip() -> bool:
    """
    Check of IP adressen gelogd moeten worden.

    Returns:
        bool: True als IP logging enabled is
    """
    return conversation_logging_config.log_user_ip


def get_content_length_limit() -> int:
    """
    Haal de maximum content lengte op.

    Returns:
        int: Maximum aantal characters
    """
    return conversation_logging_config.max_content_length


def truncate_content(content: str) -> str:
    """
    Truncate content als het te lang is.

    Args:
        content: Content om te truncaten

    Returns:
        str: Getrunacate content
    """
    max_length = get_content_length_limit()

    if len(content) <= max_length:
        return content

    # Truncate en voeg indicator toe
    return content[: max_length - 20] + "... [TRUNCATED]"
