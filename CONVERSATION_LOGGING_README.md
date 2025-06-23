# Conversatie Logging Systeem - Implementatie Plan

## 📋 Overzicht

Dit document beschrijft het nieuwe conversatie logging systeem voor PiXie-agent dat zich richt op het vastleggen van zinvolle conversatie data tussen klanten en de AI voor latere analyse.

## 🎯 Doelstellingen

1. **Conversatie Tracking**: Volledige conversaties vastleggen per sessie
2. **Performance Monitoring**: Response tijden en error rates bijhouden
3. **Gebruikersanalytics**: Inzicht in gebruikersgedrag en patronen
4. **Kennisbank Optimalisatie**: Analyseren welke collecties het meest gebruikt worden
5. **Privacy Bewust**: Alleen relevante data opslaan, minimale persoonlijke informatie

## 🏗️ Architectuur

### Database Schema

- `conversation_logs`: Individuele berichten (vraag/antwoord)
- `conversation_sessions`: Sessie-level statistieken en metadata

### Services

- `ConversationLogger`: Hoofdklasse voor logging
- `ConversationAnalytics`: Analytics en rapportage
- `ConversationLoggingConfig`: Configuratie management

### UI Components

- Admin dashboard voor analytics bekijken
- Statistieken en trends visualisatie

## 📊 Data Structure

### Conversation Logs

```sql
- session_id: Unieke sessie identifier
- user_id: Gebruiker ID (foreign key)
- message_type: 'user_question' | 'ai_response' | 'system_event' | 'error_event'
- content: De werkelijke vraag/antwoord tekst
- metadata: JSONB met extra informatie
- processing_time_ms: Verwerkingstijd voor AI responses
- collection_used: Welke kennisbank werd geraadpleegd
- timestamp: Wanneer het bericht werd gelogd
```

### Session Tracking

```sql
- session_id: Unieke sessie identifier (primary key)
- user_id: Gebruiker ID
- start_time/end_time: Sessie tijdspanne
- total_messages: Aantal berichten in sessie
- avg_response_time_ms: Gemiddelde AI response tijd
- collections_used: Array van gebruikte collecties
```

## 🔧 Implementatie Stappen

### Stap 1: Database Setup

```bash
# Run nieuwe schema tegen bestaande database
psql -h pixie-db -U $POSTGRES_USER -d $POSTGRES_DB -f conversation_logging_schema.sql
```

### Stap 2: Service Integratie

De `ConversationLogger` is reeds geïntegreerd in:

- `/api/v1/chat` endpoint in `src/app/api/llm.py`
- Automatische sessie tracking
- Error logging bij exceptions

### Stap 3: Admin Interface

Voeg conversatie analytics toe aan admin interface:

```python
# In src/app/ui/admin/admin_page.py
from app.ui.admin.conversation_analytics_ui import create_conversation_analytics_ui

# Voeg tab toe voor analytics
```

### Stap 4: Dependencies

Installeer benodigde packages:

```bash
pip install plotly pandas
# of voeg toe aan pyproject.toml
```

## 📈 Analytics Mogelijkheden

### Algemene Statistieken

- Aantal sessies per dag/week/maand
- Gemiddelde sessie duur
- Most gebruikte collecties
- Response tijd trends
- Error rates

### Gebruiker Analytics

- Individuele gebruikersactiviteit
- Meest actieve tijden
- Favoriete onderwerpen/collecties
- Sessie patronen

### Conversatie Analyse

- Populaire vragen
- Lange response tijden identificeren
- Error patterns
- Kennisbank effectiviteit

## 🔒 Privacy & Security

### Privacy Overwegingen

- IP adressen worden standaard NIET opgeslagen (configureerbaar)
- User agents alleen voor technische debugging
- Persoonlijke informatie in content wordt niet gefilterd (verantwoordelijkheid van gebruiker)

### Data Retention

- Standaard 365 dagen log retention
- Configureerbaar via environment variables
- Automatische cleanup mogelijk (TODO: implement)

## 🚀 Gebruik

### Voor Developers

```python
from services.conversation_logger import conversation_logger

# Log een gebruikersvraag
conversation_logger.log_user_question(
    session_id="session_123",
    user_id=1,
    question="Hoe werkt machine learning?"
)

# Log een AI response
conversation_logger.log_ai_response(
    session_id="session_123", 
    user_id=1,
    response="Machine learning is...",
    processing_time_ms=1250,
    collection_used="ml_docs"
)
```

### Voor Admins

1. Ga naar `/admin` interface
2. Klik op "Conversatie Analytics" tab
3. Bekijk statistieken per periode
4. Analyseer gebruikersgedrag
5. Monitor performance metrics

## 📋 Environment Configuration

```bash
# .env settings
CONVERSATION_LOGGING_ENABLED=true
LOG_USER_IP=false
LOG_RETENTION_DAYS=365
```

## 🔄 Future Enhancements

### Kort Termijn

- [ ] Automated log cleanup job
- [ ] Export functionaliteit (CSV, JSON)
- [ ] Real-time dashboard updates
- [ ] Performance alerts

### Lang Termijn

- [ ] Machine learning op conversation patterns
- [ ] Sentiment analysis van vragen
- [ ] Automatic FAQ generation
- [ ] Predictive analytics voor user behavior

## 🐛 Troubleshooting

### Logging werkt niet

1. Check database connectie
2. Verificeer of nieuwe tabellen bestaan
3. Check environment variables
4. Bekijk application logs voor errors

### Performance Issues

1. Check database indexes
2. Monitor log tabel grootte
3. Overweeg data archivering
4. Analyseer query performance

### Analytics laden langzaam

1. Verhoog cache tijd in config
2. Optimaliseer database queries
3. Voeg extra indexes toe indien nodig

## 📞 Support

Voor vragen over het logging systeem:

1. Check de application logs
2. Bekijk database tabellen direct
3. Test met kleine datasets eerst
4. Monitor performance impact

---

**Laatst bijgewerkt**: 23 juni 2025  
**Versie**: 1.0  
**Author**: PiXie Development Team
