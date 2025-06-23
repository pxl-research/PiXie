"""
Conversatie Analytics Service

Deze service biedt methoden voor het analyseren van conversatie logs
om inzichten te krijgen in gebruikersgedrag, AI performance en trends.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional, Tuple
from services.database.database import get_db_connection
from dataclasses import dataclass


logger = logging.getLogger(__name__)


@dataclass
class ConversationStats:
    """Statistieken voor een bepaalde periode"""

    total_sessions: int
    total_messages: int
    total_user_questions: int
    total_ai_responses: int
    avg_session_duration_minutes: float
    avg_response_time_ms: float
    unique_users: int
    most_used_collections: List[Tuple[str, int]]
    error_rate: float


@dataclass
class UserAnalytics:
    """Analytics voor een specifieke gebruiker"""

    user_id: int
    username: str
    total_sessions: int
    total_questions: int
    avg_session_duration: float
    most_active_hours: List[int]
    favorite_collections: List[str]
    last_activity: datetime


class ConversationAnalytics:
    """
    Hoofdklasse voor conversatie analytics.

    Biedt methoden voor het analyseren van conversatie data.
    """

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def get_period_stats(
        self, start_date: datetime, end_date: datetime, user_id: Optional[int] = None
    ) -> Optional[ConversationStats]:
        """
        Haal statistieken op voor een bepaalde periode.

        Args:
            start_date: Start datum
            end_date: Eind datum
            user_id: Optioneel - filter op specifieke gebruiker

        Returns:
            ConversationStats object of None bij error
        """
        try:
            conn = get_db_connection()
            with conn.cursor() as cursor:
                user_filter = ""
                params = [start_date, end_date]

                if user_id:
                    user_filter = "AND cs.user_id = %s"
                    params.append(user_id)

                # Basis statistieken uit sessions tabel
                cursor.execute(
                    f"""
                    SELECT 
                        COUNT(*) as total_sessions,
                        SUM(total_messages) as total_messages,
                        SUM(total_user_questions) as total_user_questions,
                        SUM(total_ai_responses) as total_ai_responses,
                        AVG(session_duration_minutes) as avg_session_duration,
                        AVG(avg_response_time_ms) as avg_response_time,
                        COUNT(DISTINCT user_id) as unique_users
                    FROM conversation_sessions cs
                    WHERE cs.start_time BETWEEN %s AND %s {user_filter}
                """,
                    params,
                )

                stats_row = cursor.fetchone()

                # Most used collections
                cursor.execute(
                    f"""
                    SELECT 
                        UNNEST(collections_used) as collection,
                        COUNT(*) as usage_count
                    FROM conversation_sessions cs
                    WHERE cs.start_time BETWEEN %s AND %s {user_filter}
                    AND collections_used IS NOT NULL
                    GROUP BY UNNEST(collections_used)
                    ORDER BY usage_count DESC
                    LIMIT 10
                """,
                    params,
                )

                collections = cursor.fetchall()

                # Error rate
                cursor.execute(
                    f"""
                    SELECT 
                        COUNT(CASE WHEN error_occurred THEN 1 END)::float / NULLIF(COUNT(*), 0) as error_rate
                    FROM conversation_logs cl
                    JOIN conversation_sessions cs ON cl.session_id = cs.session_id
                    WHERE cs.start_time BETWEEN %s AND %s {user_filter}
                """,
                    params,
                )

                error_rate_row = cursor.fetchone()

                if stats_row and stats_row[0] > 0:  # Als er sessies zijn
                    return ConversationStats(
                        total_sessions=stats_row[0] or 0,
                        total_messages=stats_row[1] or 0,
                        total_user_questions=stats_row[2] or 0,
                        total_ai_responses=stats_row[3] or 0,
                        avg_session_duration_minutes=float(stats_row[4] or 0),
                        avg_response_time_ms=float(stats_row[5] or 0),
                        unique_users=stats_row[6] or 0,
                        most_used_collections=collections or [],
                        error_rate=(
                            float(error_rate_row[0] or 0) if error_rate_row else 0.0
                        ),
                    )
                else:
                    return ConversationStats(
                        total_sessions=0,
                        total_messages=0,
                        total_user_questions=0,
                        total_ai_responses=0,
                        avg_session_duration_minutes=0.0,
                        avg_response_time_ms=0.0,
                        unique_users=0,
                        most_used_collections=[],
                        error_rate=0.0,
                    )

        except Exception as e:
            self.logger.error(f"Error getting period stats: {e}", exc_info=True)
            return None
        finally:
            if "conn" in locals():
                conn.close()

    def get_user_analytics(self, user_id: int) -> Optional[UserAnalytics]:
        """
        Haal gedetailleerde analytics op voor een specifieke gebruiker.

        Args:
            user_id: Gebruiker ID

        Returns:
            UserAnalytics object of None bij error
        """
        try:
            conn = get_db_connection()
            with conn.cursor() as cursor:
                # Basis gebruiker stats
                cursor.execute(
                    """
                    SELECT 
                        u.username,
                        COUNT(cs.session_id) as total_sessions,
                        SUM(cs.total_user_questions) as total_questions,
                        AVG(cs.session_duration_minutes) as avg_session_duration,
                        MAX(cs.end_time) as last_activity
                    FROM users u
                    LEFT JOIN conversation_sessions cs ON u.id = cs.user_id
                    WHERE u.id = %s
                    GROUP BY u.id, u.username
                """,
                    (user_id,),
                )

                user_row = cursor.fetchone()
                if not user_row:
                    return None

                # Most active hours
                cursor.execute(
                    """
                    SELECT 
                        EXTRACT(HOUR FROM cl.timestamp) as hour,
                        COUNT(*) as message_count
                    FROM conversation_logs cl
                    WHERE cl.user_id = %s
                    GROUP BY EXTRACT(HOUR FROM cl.timestamp)
                    ORDER BY message_count DESC
                    LIMIT 5
                """,
                    (user_id,),
                )

                active_hours = [int(row[0]) for row in cursor.fetchall()]

                # Favorite collections
                cursor.execute(
                    """
                    SELECT 
                        collection_used,
                        COUNT(*) as usage_count
                    FROM conversation_logs
                    WHERE user_id = %s AND collection_used IS NOT NULL
                    GROUP BY collection_used
                    ORDER BY usage_count DESC
                    LIMIT 5
                """,
                    (user_id,),
                )

                favorite_collections = [row[0] for row in cursor.fetchall()]

                return UserAnalytics(
                    user_id=user_id,
                    username=user_row[0],
                    total_sessions=user_row[1] or 0,
                    total_questions=user_row[2] or 0,
                    avg_session_duration=float(user_row[3] or 0),
                    most_active_hours=active_hours,
                    favorite_collections=favorite_collections,
                    last_activity=user_row[4] or datetime.now(timezone.utc),
                )

        except Exception as e:
            self.logger.error(
                f"Error getting user analytics for {user_id}: {e}", exc_info=True
            )
            return None
        finally:
            if "conn" in locals():
                conn.close()

    def get_daily_activity_trend(
        self, days: int = 30, user_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Haal dagelijkse activiteit trend op.

        Args:
            days: Aantal dagen terug te kijken
            user_id: Optioneel - filter op specifieke gebruiker

        Returns:
            List van dictionaries met datum en activiteit counts
        """
        try:
            start_date = datetime.now(timezone.utc) - timedelta(days=days)

            conn = get_db_connection()
            with conn.cursor() as cursor:
                user_filter = ""
                params = [start_date]

                if user_id:
                    user_filter = "AND cl.user_id = %s"
                    params.append(user_id)

                cursor.execute(
                    f"""
                    SELECT 
                        DATE(cl.timestamp) as date,
                        COUNT(CASE WHEN cl.message_type = 'user_question' THEN 1 END) as questions,
                        COUNT(CASE WHEN cl.message_type = 'ai_response' THEN 1 END) as responses,
                        COUNT(DISTINCT cl.session_id) as sessions
                    FROM conversation_logs cl
                    WHERE cl.timestamp >= %s {user_filter}
                    GROUP BY DATE(cl.timestamp)
                    ORDER BY date
                """,
                    params,
                )

                return [
                    {
                        "date": row[0].isoformat(),
                        "questions": row[1],
                        "responses": row[2],
                        "sessions": row[3],
                    }
                    for row in cursor.fetchall()
                ]

        except Exception as e:
            self.logger.error(f"Error getting daily activity trend: {e}", exc_info=True)
            return []
        finally:
            if "conn" in locals():
                conn.close()

    def get_popular_questions(
        self, limit: int = 20, days: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Haal populaire vragen op (gebaseerd op overeenkomsten).

        Args:
            limit: Maximum aantal resultaten
            days: Aantal dagen terug (None = alle tijd)

        Returns:
            List van dictionaries met vraag informatie
        """
        try:
            conn = get_db_connection()
            with conn.cursor() as cursor:
                date_filter = ""
                params = []

                if days:
                    date_filter = "WHERE cl.timestamp >= %s"
                    params.append(datetime.now(timezone.utc) - timedelta(days=days))

                # Voor nu, gewoon meest recente vragen
                # In de toekomst kun je dit uitbreiden met similarity matching
                cursor.execute(
                    f"""
                    SELECT 
                        cl.content,
                        COUNT(*) as frequency,
                        AVG(cl.processing_time_ms) as avg_processing_time
                    FROM conversation_logs cl
                    {date_filter}
                    AND cl.message_type = 'user_question'
                    AND LENGTH(cl.content) > 10  -- Filter korte vragen
                    GROUP BY cl.content
                    HAVING COUNT(*) > 1  -- Alleen vragen die meerdere keren gesteld zijn
                    ORDER BY frequency DESC, avg_processing_time ASC
                    LIMIT %s
                """,
                    params + [limit],
                )

                return [
                    {
                        "question": row[0],
                        "frequency": row[1],
                        "avg_processing_time_ms": float(row[2] or 0),
                    }
                    for row in cursor.fetchall()
                ]

        except Exception as e:
            self.logger.error(f"Error getting popular questions: {e}", exc_info=True)
            return []
        finally:
            if "conn" in locals():
                conn.close()

    def get_session_details(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Haal gedetailleerde informatie op voor een specifieke sessie.

        Args:
            session_id: Sessie ID

        Returns:
            Dictionary met sessie details of None bij error
        """
        try:
            conn = get_db_connection()
            with conn.cursor() as cursor:
                # Sessie informatie
                cursor.execute(
                    """
                    SELECT 
                        cs.*,
                        u.username
                    FROM conversation_sessions cs
                    JOIN users u ON cs.user_id = u.id
                    WHERE cs.session_id = %s
                """,
                    (session_id,),
                )

                session_row = cursor.fetchone()
                if not session_row:
                    return None

                # Conversatie berichten
                cursor.execute(
                    """
                    SELECT 
                        message_type,
                        content,
                        timestamp,
                        processing_time_ms,
                        collection_used,
                        error_occurred
                    FROM conversation_logs
                    WHERE session_id = %s
                    ORDER BY timestamp
                """,
                    (session_id,),
                )

                messages = [
                    {
                        "type": row[0],
                        "content": row[1],
                        "timestamp": row[2].isoformat(),
                        "processing_time_ms": row[3],
                        "collection_used": row[4],
                        "error_occurred": row[5],
                    }
                    for row in cursor.fetchall()
                ]

                return {
                    "session_id": session_row[0],
                    "user_id": session_row[1],
                    "username": session_row[-1],  # username is last column
                    "start_time": (
                        session_row[2].isoformat() if session_row[2] else None
                    ),
                    "end_time": session_row[3].isoformat() if session_row[3] else None,
                    "total_messages": session_row[4],
                    "total_user_questions": session_row[5],
                    "total_ai_responses": session_row[6],
                    "avg_response_time_ms": session_row[7],
                    "collections_used": session_row[8],
                    "session_duration_minutes": session_row[9],
                    "messages": messages,
                }

        except Exception as e:
            self.logger.error(
                f"Error getting session details for {session_id}: {e}", exc_info=True
            )
            return None
        finally:
            if "conn" in locals():
                conn.close()


# Singleton instance
conversation_analytics = ConversationAnalytics()
