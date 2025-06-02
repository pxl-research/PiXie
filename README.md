# PiXie - Retrieval-Augmented Generation (RAG) Project

## Korte beschrijving

PiXie is een implementatie van Retrieval-Augmented Generation (RAG) in Python. Het project is een concrete realisatie binnen het speerpuntproject **AIdopt** van **PXL Smart ICT**, en biedt een eenvoudige manier om antwoorden te genereren door informatie op te halen uit externe kennisbronnen. PiXie is verpakt in een Docker-container voor gemakkelijk gebruik en bevat een webinterface voor interactie.

## Functies

- Ondersteunt Retrieval-Augmented Generation (RAG), waarbij informatie uit documenten wordt opgehaald en gecombineerd met generatieve AI-modellen om nauwkeurige antwoorden te geven.
- Mogelijkheid om documenten te uploaden via een intuïtieve webinterface.
- Geeft gebruikers de mogelijkheid om vragen te stellen en antwoorden te ontvangen, inclusief bronvermeldingen van de geüploade documenten.
- Volledig verpakt in een Docker-container voor eenvoudige installatie en consistentie.
- Gebruiksvriendelijke interface via Gradio om interacties soepel te laten verlopen.

## Voorbereiding

Voordat je de applicatie kunt starten, zorg ervoor dat het `.env.dev` bestand aanwezig is in de hoofdmap van het project. Kopieer `.env.example` naar `.env.dev` en vul de juiste waarden in.

Deze bestanden bevatten belangrijke configuraties zoals:

- Azure Document Loader instellingen
- Azure Open AI LLM configuratie
- Azure Blob Storage details

## Installatie

Gebruikers kunnen de Docker-containers opzetten en starten met Docker Compose:

```bash
git clone https://github.com/pxl-research/PiXie.git
cd PiXie
cp .env.example .env.dev
# Vul de juiste waarden in .env.dev
docker compose up --build -d
```

## Gebruik

Na het starten van de containers zijn de volgende interfaces automatisch beschikbaar:

- **Admin interface** (document upload en beheer): http://localhost:8111/admin
- **Chat interface** (vraag-en-antwoord systeem): http://localhost:8111/chat
- **API endpoints**: http://localhost:8111/docs (FastAPI documentatie)

### Development

De workspace wordt automatisch gemount in de container, zodat code wijzigingen direct zichtbaar zijn. Voor debugging kun je een bash-sessie openen:

```bash
docker exec -it pixie-agent-1 /bin/bash
```

## Afhankelijkheden

Alle afhankelijkheden zijn verpakt in de Docker-container. Het enige wat je nodig hebt is:

- Docker
- Docker Compose

## Achtergrond

PiXie is onderdeel van het speerpuntproject TransformAI van PXL Smart ICT, ontworpen om AI-technologieën zoals RAG te ontwikkelen en toepassen.

## Licentie

Dit project is gelicentieerd onder de MIT-licentie.
