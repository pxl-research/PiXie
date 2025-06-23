"""
Conversatie Logger Service

Deze service is verantwoordelijk voor het vastleggen van alle belangrijke conversaties
tussen gebruikers en de AI, met focus op bruikbare data voor analyse.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum
from services.database.database import get_db_connection
from psycopg2.extras import Json


logger = logging.getLogger(__name__)


class MessageType(Enum):
    USER_QUESTION = "user_question"
    AI_RESPONSE = "ai_response"
    SYSTEM_EVENT = "system_event"
    ERROR_EVENT = "error_event"


@dataclass
class ConversationLogEntry:
    """Dataclass voor een conversatie log entry"""

    session_id: str
    user_id: int
    message_type: MessageType
    content: str
    metadata: Optional[Dict[str, Any]] = None
    processing_time_ms: Optional[int] = None
    token_count: Optional[int] = None
    collection_used: Optional[str] = None
    user_ip: Optional[str] = None
    user_agent: Optional[str] = None
    error_occurred: bool = False
    error_details: Optional[str] = None


class ConversationLogger:
    """
    Hoofdklasse voor conversatie logging.

    Deze klasse biedt methoden om conversaties te loggen en sessies bij te houden.
    """

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def log_user_question(
        self,
        session_id: str,
        user_id: int,
        question: str,
        user_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Log een gebruikersvraag.

        Args:
            session_id: Unieke sessie identificator
            user_id: Gebruiker ID
            question: De gestelde vraag
            user_ip: IP adres van gebruiker (optioneel)
            user_agent: Browser/app informatie (optioneel)
            metadata: Extra metadata (optioneel)

        Returns:
            bool: True als succesvol gelogd, False bij error
        """
        try:
            entry = ConversationLogEntry(
                session_id=session_id,
                user_id=user_id,
                message_type=MessageType.USER_QUESTION,
                content=question,
                user_ip=user_ip,
                user_agent=user_agent,
                metadata=metadata or {},
            )

            success = self._save_log_entry(entry)
            if success:
                self._update_session_stats(
                    session_id, user_id, increment_questions=True
                )

            return success

        except Exception as e:
            self.logger.error(f"Error logging user question: {e}", exc_info=True)
            return False

    def log_ai_response(
        self,
        session_id: str,
        user_id: int,
        response: str,
        processing_time_ms: Optional[int] = None,
        token_count: Optional[int] = None,
        collection_used: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Log een AI response.

        Args:
            session_id: Unieke sessie identificator
            user_id: Gebruiker ID
            response: Het AI antwoord
            processing_time_ms: Verwerkingstijd in milliseconden
            token_count: Aantal gebruikte tokens
            collection_used: Gebruikte kennisbank collectie
            metadata: Extra metadata

        Returns:
            bool: True als succesvol gelogd, False bij error
        """
        try:
            entry = ConversationLogEntry(
                session_id=session_id,
                user_id=user_id,
                message_type=MessageType.AI_RESPONSE,
                content=response,
                processing_time_ms=processing_time_ms,
                token_count=token_count,
                collection_used=collection_used,
                metadata=metadata or {},
            )

            success = self._save_log_entry(entry)
            if success:
                self._update_session_stats(
                    session_id,
                    user_id,
                    increment_responses=True,
                    processing_time_ms=processing_time_ms,
                    collection_used=collection_used,
                )

            return success

        except Exception as e:
            self.logger.error(f"Error logging AI response: {e}", exc_info=True)
            return False

    def log_error_event(
        self,
        session_id: str,
        user_id: int,
        error_message: str,
        error_details: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Log een error event.

        Args:
            session_id: Unieke sessie identificator
            user_id: Gebruiker ID
            error_message: Korte error beschrijving
            error_details: Uitgebreide error details
            metadata: Extra metadata

        Returns:
            bool: True als succesvol gelogd, False bij error
        """
        try:
            entry = ConversationLogEntry(
                session_id=session_id,
                user_id=user_id,
                message_type=MessageType.ERROR_EVENT,
                content=error_message,
                error_occurred=True,
                error_details=error_details,
                metadata=metadata or {},
            )

            return self._save_log_entry(entry)

        except Exception as e:
            self.logger.error(f"Error logging error event: {e}", exc_info=True)
            return False

    def start_session(
        self,
        session_id: str,
        user_id: int,
        client_info: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Start een nieuwe conversatie sessie.

        Args:
            session_id: Unieke sessie identificator
            user_id: Gebruiker ID
            client_info: Informatie over client (browser, app, etc.)

        Returns:
            bool: True als succesvol aangemaakt, False bij error
        """
        try:
            conn = get_db_connection()
            with conn.cursor() as cursor:
                query = """
                    INSERT INTO conversation_sessions 
                    (session_id, user_id, start_time, client_info)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (session_id) DO NOTHING
                """
                cursor.execute(
                    query,
                    (
                        session_id,
                        user_id,
                        datetime.now(timezone.utc),
                        Json(client_info or {}),
                    ),
                )
                conn.commit()

            self.logger.info(f"Session started: {session_id} for user {user_id}")
            return True

        except Exception as e:
            self.logger.error(
                f"Error starting session {session_id}: {e}", exc_info=True
            )
            return False
        finally:
            if "conn" in locals():
                conn.close()

    def end_session(self, session_id: str) -> bool:
        """
        Beëindig een conversatie sessie.

        Args:
            session_id: Unieke sessie identificator

        Returns:
            bool: True als succesvol beëindigd, False bij error
        """
        try:
            conn = get_db_connection()
            with conn.cursor() as cursor:
                # Update end time en bereken sessie duur
                query = """
                    UPDATE conversation_sessions 
                    SET end_time = %s,
                        session_duration_minutes = EXTRACT(EPOCH FROM (%s - start_time)) / 60
                    WHERE session_id = %s
                """
                end_time = datetime.now(timezone.utc)
                cursor.execute(query, (end_time, end_time, session_id))
                conn.commit()

            self.logger.info(f"Session ended: {session_id}")
            return True

        except Exception as e:
            self.logger.error(f"Error ending session {session_id}: {e}", exc_info=True)
            return False
        finally:
            if "conn" in locals():
                conn.close()

    def _save_log_entry(self, entry: ConversationLogEntry) -> bool:
        """
        Interne methode om een log entry op te slaan in de database.

        Args:
            entry: ConversationLogEntry object

        Returns:
            bool: True als succesvol opgeslagen, False bij error
        """
        try:
            conn = get_db_connection()
            with conn.cursor() as cursor:
                query = """
                    INSERT INTO conversation_logs 
                    (session_id, user_id, message_type, content, metadata, 
                     processing_time_ms, token_count, collection_used, 
                     user_ip, user_agent, error_occurred, error_details)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(
                    query,
                    (
                        entry.session_id,
                        entry.user_id,
                        entry.message_type.value,
                        entry.content,
                        Json(entry.metadata) if entry.metadata else None,
                        entry.processing_time_ms,
                        entry.token_count,
                        entry.collection_used,
                        entry.user_ip,
                        entry.user_agent,
                        entry.error_occurred,
                        entry.error_details,
                    ),
                )
                conn.commit()

            return True

        except Exception as e:
            self.logger.error(f"Error saving log entry: {e}", exc_info=True)
            return False
        finally:
            if "conn" in locals():
                conn.close()

    def _update_session_stats(
        self,
        session_id: str,
        user_id: int,
        increment_questions: bool = False,
        increment_responses: bool = False,
        processing_time_ms: Optional[int] = None,
        collection_used: Optional[str] = None,
    ) -> bool:
        """
        Update sessie statistieken.

        Args:
            session_id: Sessie ID
            user_id: Gebruiker ID
            increment_questions: Tel een vraag bij op
            increment_responses: Tel een antwoord bij op
            processing_time_ms: Verwerkingstijd voor gemiddelde
            collection_used: Gebruikte collectie voor tracking

        Returns:
            bool: True als succesvol bijgewerkt
        """
        try:
            conn = get_db_connection()
            with conn.cursor() as cursor:
                # Maak sessie aan als die nog niet bestaat
                cursor.execute(
                    """
                    INSERT INTO conversation_sessions (session_id, user_id)
                    VALUES (%s, %s) ON CONFLICT (session_id) DO NOTHING
                    """,
                    (session_id, user_id),
                )

                # Update basic counts
                if increment_questions:
                    cursor.execute(
                        """
                        UPDATE conversation_sessions 
                        SET total_messages = total_messages + 1,
                            total_user_questions = total_user_questions + 1
                        WHERE session_id = %s
                        """,
                        (session_id,),
                    )

                if increment_responses:
                    cursor.execute(
                        """
                        UPDATE conversation_sessions 
                        SET total_messages = total_messages + 1,
                            total_ai_responses = total_ai_responses + 1
                        WHERE session_id = %s
                        """,
                        (session_id,),
                    )

                    # Update average response time separately
                    if processing_time_ms is not None:
                        cursor.execute(
                            """
                            UPDATE conversation_sessions 
                            SET avg_response_time_ms = CASE 
                                WHEN total_ai_responses = 1 THEN %s
                                ELSE (COALESCE(avg_response_time_ms, 0) * (total_ai_responses - 1) + %s) / total_ai_responses
                            END
                            WHERE session_id = %s
                            """,
                            (processing_time_ms, processing_time_ms, session_id),
                        )

                # Update collections array
                if collection_used:
                    cursor.execute(
                        """
                        UPDATE conversation_sessions 
                        SET collections_used = CASE
                            WHEN collections_used IS NULL THEN ARRAY[%s]
                            WHEN NOT (%s = ANY(collections_used)) THEN array_append(collections_used, %s)
                            ELSE collections_used
                        END
                        WHERE session_id = %s
                        """,
                        (collection_used, collection_used, collection_used, session_id),
                    )

                conn.commit()
                return True

        except Exception as e:
            self.logger.error(f"Error updating session stats: {e}", exc_info=True)
            return False
        finally:
            if "conn" in locals():
                conn.close()


# Singleton instance voor globaal gebruik
conversation_logger = ConversationLogger()
