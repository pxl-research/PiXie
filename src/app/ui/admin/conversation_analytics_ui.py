"""
Admin interface voor conversatie analytics.

Deze module biedt een Gradio interface voor het bekijken van conversatie statistieken,
gebruikersanalytics en andere logging data.
"""

import gradio as gr
import pandas as pd
from datetime import datetime, timedelta, timezone
from typing import List, Tuple
from services.conversation_analytics import conversation_analytics
from services.database.database import get_db_connection
import plotly.express as px


def get_period_statistics(days: int = 7) -> Tuple[str, str]:
    """
    Haal periode statistieken op en format ze voor weergave.

    Args:
        days: Aantal dagen terug te kijken

    Returns:
        Tuple van (statistics_text, chart_html)
    """
    try:
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)

        stats = conversation_analytics.get_period_stats(start_date, end_date)

        if stats:
            stats_text = f"""
            ## 📊 Conversatie Statistieken (Laatste {days} dagen)
            
            **Algemeen:**
            - 👥 Totaal sessies: {stats.total_sessions}
            - 💬 Totaal berichten: {stats.total_messages}
            - ❓ Gebruikersvragen: {stats.total_user_questions}
            - 🤖 AI antwoorden: {stats.total_ai_responses}
            - 👤 Unieke gebruikers: {stats.unique_users}
            
            **Performance:**
            - ⏱️ Gem. sessie duur: {stats.avg_session_duration_minutes:.1f} minuten
            - 🚀 Gem. response tijd: {stats.avg_response_time_ms:.0f} ms
            - ❌ Error rate: {stats.error_rate:.2%}
            
            **Populaire Collecties:**
            """

            for collection, count in stats.most_used_collections[:5]:
                stats_text += f"\n- 📚 {collection}: {count} keer gebruikt"

            # Maak een chart van daily activity
            daily_data = conversation_analytics.get_daily_activity_trend(days)

            if daily_data:
                df = pd.DataFrame(daily_data)
                fig = px.line(
                    df,
                    x="date",
                    y=["questions", "responses", "sessions"],
                    title=f"Dagelijkse Activiteit (Laatste {days} dagen)",
                    labels={"value": "Aantal", "variable": "Type"},
                )
                chart_html = fig.to_html(include_plotlyjs="cdn")
            else:
                chart_html = "<p>Geen data beschikbaar voor grafiek.</p>"

        else:
            stats_text = "❌ Geen statistieken beschikbaar voor deze periode."
            chart_html = ""

        return stats_text, chart_html

    except Exception as e:
        return f"❌ Error bij ophalen statistieken: {str(e)}", ""


def get_user_list() -> List[List]:
    """
    Haal lijst van gebruikers op voor dropdown.

    Returns:
        List van [user_id, username] paren
    """
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT u.id, u.username, 
                       COUNT(cs.session_id) as session_count,
                       MAX(cs.end_time) as last_activity
                FROM users u
                LEFT JOIN conversation_sessions cs ON u.id = cs.user_id
                GROUP BY u.id, u.username
                ORDER BY session_count DESC, u.username
            """
            )

            users = []
            for row in cursor.fetchall():
                user_id, username, session_count, last_activity = row
                last_activity_str = (
                    last_activity.strftime("%Y-%m-%d") if last_activity else "Nooit"
                )
                users.append(
                    [
                        user_id,
                        f"{username} ({session_count} sessies, laatst: {last_activity_str})",
                    ]
                )

            return users

    except Exception as e:
        return [[0, f"Error: {str(e)}"]]
    finally:
        if "conn" in locals():
            conn.close()


def get_user_analytics_display(user_selection: str) -> str:
    """
    Haal en format gebruiker analytics.

    Args:
        user_selection: Geselecteerde gebruiker string

    Returns:
        Geformatteerde analytics string
    """
    try:
        if not user_selection or user_selection.startswith("Error"):
            return "❓ Selecteer een gebruiker om analytics te bekijken."

        # Extract user_id from selection (eerste waarde voor spatie)
        user_id = int(user_selection.split()[0])

        analytics = conversation_analytics.get_user_analytics(user_id)

        if analytics:
            active_hours = ", ".join(
                [f"{h:02d}:00" for h in analytics.most_active_hours]
            )
            collections = (
                ", ".join(analytics.favorite_collections)
                if analytics.favorite_collections
                else "Geen"
            )

            return f"""
            ## 👤 Gebruiker Analytics: {analytics.username}
            
            **Activiteit:**
            - 🎯 Totaal sessies: {analytics.total_sessions}
            - ❓ Totaal vragen: {analytics.total_questions}
            - ⏱️ Gem. sessie duur: {analytics.avg_session_duration:.1f} minuten
            - 🕐 Actieve uren: {active_hours}
            - 📅 Laatste activiteit: {analytics.last_activity.strftime('%Y-%m-%d %H:%M')}
            
            **Voorkeuren:**
            - 📚 Favoriete collecties: {collections}
            """
        else:
            return f"❌ Geen analytics gevonden voor gebruiker ID {user_id}"

    except ValueError:
        return "❌ Ongeldige gebruiker selectie"
    except Exception as e:
        return f"❌ Error bij ophalen gebruiker analytics: {str(e)}"


def get_session_details_display(session_id: str) -> str:
    """
    Haal en format sessie details.

    Args:
        session_id: Sessie ID

    Returns:
        Geformatteerde sessie details
    """
    try:
        if not session_id.strip():
            return "❓ Voer een sessie ID in om details te bekijken."

        details = conversation_analytics.get_session_details(session_id.strip())

        if details:
            messages_count = len(details["messages"])
            start_time = details["start_time"] or "Onbekend"
            end_time = details["end_time"] or "Nog actief"

            result = f"""
            ## 🎯 Sessie Details: {session_id}
            
            **Informatie:**
            - 👤 Gebruiker: {details['username']} (ID: {details['user_id']})
            - 🕐 Start tijd: {start_time}
            - 🕑 Eind tijd: {end_time}
            - ⏱️ Duur: {details['session_duration_minutes'] or 0:.1f} minuten
            - 💬 Totaal berichten: {messages_count}
            - ❓ Gebruikersvragen: {details['total_user_questions']}
            - 🤖 AI antwoorden: {details['total_ai_responses']}
            - 🚀 Gem. response tijd: {details['avg_response_time_ms'] or 0:.0f} ms
            - 📚 Gebruikte collecties: {', '.join(details['collections_used'] or [])}
            
            **Conversatie Verloop:**
            """

            for i, msg in enumerate(details["messages"], 1):
                msg_type = (
                    "❓ Vraag" if msg["type"] == "user_question" else "🤖 Antwoord"
                )
                timestamp = msg["timestamp"][:19]  # Remove microseconds
                content_preview = (
                    msg["content"][:100] + "..."
                    if len(msg["content"]) > 100
                    else msg["content"]
                )

                result += f"\n**{i}. {msg_type}** ({timestamp})\n"
                result += f"   {content_preview}\n"

                if msg["processing_time_ms"]:
                    result += f"   ⏱️ Verwerkingstijd: {msg['processing_time_ms']} ms\n"

                if msg["error_occurred"]:
                    result += "   ❌ Error opgetreden\n"

            return result
        else:
            return f"❌ Geen sessie gevonden met ID: {session_id}"

    except Exception as e:
        return f"❌ Error bij ophalen sessie details: {str(e)}"


def get_popular_questions_display(days: int = 30, limit: int = 10) -> str:
    """
    Haal en format populaire vragen.

    Args:
        days: Aantal dagen terug
        limit: Maximum aantal resultaten

    Returns:
        Geformatteerde populaire vragen
    """
    try:
        questions = conversation_analytics.get_popular_questions(limit=limit, days=days)

        if questions:
            result = f"## 🔥 Populaire Vragen (Laatste {days} dagen)\n\n"

            for i, q in enumerate(questions, 1):
                result += f"**{i}. Vraag** (gevraagd {q['frequency']} keer)\n"
                result += f"   {q['question']}\n"
                result += f"   ⏱️ Gem. verwerkingstijd: {q['avg_processing_time_ms']:.0f} ms\n\n"

            return result
        else:
            return f"❓ Geen populaire vragen gevonden voor de laatste {days} dagen."

    except Exception as e:
        return f"❌ Error bij ophalen populaire vragen: {str(e)}"


def create_conversation_analytics_ui():
    """
    Maak de conversatie analytics UI.

    Deze functie bouwt de volledige analytics interface op binnen de bestaande Gradio context.
    """
    gr.Markdown("# 📈 Conversatie Analytics Dashboard")

    with gr.Row():
        with gr.Column(scale=2):

            with gr.Tabs():
                # Tab 1: Algemene Statistieken
                with gr.Tab("📊 Statistieken"):
                    days_input = gr.Slider(
                        minimum=1,
                        maximum=90,
                        value=7,
                        step=1,
                        label="Aantal dagen terug",
                    )

                    refresh_stats_btn = gr.Button(
                        "🔄 Ververs Statistieken", variant="primary"
                    )

                    stats_output = gr.Markdown(
                        "Klik op 'Ververs Statistieken' om data te laden..."
                    )
                    chart_output = gr.HTML()

                    refresh_stats_btn.click(
                        fn=get_period_statistics,
                        inputs=[days_input],
                        outputs=[stats_output, chart_output],
                    )

                # Tab 2: Gebruiker Analytics
                with gr.Tab("👤 Gebruikers"):
                    refresh_users_btn = gr.Button("🔄 Ververs Gebruikerslijst")

                    user_dropdown = gr.Dropdown(
                        choices=[],
                        label="Selecteer Gebruiker",
                        info="Kies een gebruiker om analytics te bekijken",
                    )

                    user_analytics_output = gr.Markdown(
                        "Selecteer een gebruiker om analytics te bekijken..."
                    )

                    refresh_users_btn.click(fn=get_user_list, outputs=[user_dropdown])

                    user_dropdown.change(
                        fn=get_user_analytics_display,
                        inputs=[user_dropdown],
                        outputs=[user_analytics_output],
                    )

                # Tab 3: Sessie Details
                with gr.Tab("🎯 Sessies"):
                    session_id_input = gr.Textbox(
                        label="Sessie ID", placeholder="Voer sessie ID in..."
                    )

                    get_session_btn = gr.Button(
                        "🔍 Haal Sessie Details Op", variant="primary"
                    )

                    session_details_output = gr.Markdown(
                        "Voer een sessie ID in en klik op 'Haal Sessie Details Op'..."
                    )

                    get_session_btn.click(
                        fn=get_session_details_display,
                        inputs=[session_id_input],
                        outputs=[session_details_output],
                    )

                # Tab 4: Populaire Vragen
                with gr.Tab("🔥 Trends"):
                    with gr.Row():
                        trend_days = gr.Slider(
                            minimum=1,
                            maximum=90,
                            value=30,
                            step=1,
                            label="Aantal dagen terug",
                        )

                        trend_limit = gr.Slider(
                            minimum=5,
                            maximum=50,
                            value=10,
                            step=5,
                            label="Aantal resultaten",
                        )

                    refresh_trends_btn = gr.Button(
                        "🔄 Ververs Trends", variant="primary"
                    )

                    trends_output = gr.Markdown(
                        "Klik op 'Ververs Trends' om populaire vragen te laden..."
                    )

                    refresh_trends_btn.click(
                        fn=get_popular_questions_display,
                        inputs=[trend_days, trend_limit],
                        outputs=[trends_output],
                    )

        with gr.Column(scale=1):
            gr.Markdown(
                """
            ## 💡 Gebruiksaanwijzing
            
            **Statistieken Tab:**
            - Bekijk algemene conversatie statistieken
            - Pas het aantal dagen aan voor verschillende periodes
            - Bekijk dagelijkse activiteit trends
            
            **Gebruikers Tab:**
            - Selecteer een gebruiker voor gedetailleerde analytics
            - Bekijk activiteitspatronen en voorkeuren
            
            **Sessies Tab:**
            - Voer een specifieke sessie ID in
            - Bekijk volledige conversatie geschiedenis
            
            **Trends Tab:**
            - Ontdek populaire vragen en onderwerpen
            - Analyseer verwerkingstijden en performance
            
            ---
            
            ⚡ **Tips:**
            - Gebruik de ververs knoppen om data bij te werken
            - Sessie IDs vind je in de logs of database
            - Langere periodes kunnen langzamer laden
            """
            )

    # Return wordt niet gebruikt in deze context omdat we direct in de Gradio context werken
