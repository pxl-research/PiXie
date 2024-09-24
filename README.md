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

Voordat je de applicatie kunt starten, zorg ervoor dat de juiste `.env` bestanden aanwezig zijn in de hoofdmap van het project. Dit project maakt gebruik van:

- `.env.dev` voor de ontwikkelomgeving
- `.env.prod` voor de productieomgeving

Deze bestanden bevatten belangrijke configuraties zoals:

- Azure Document Loader instellingen
- Azure Open AI LLM configuratie
- Azure Blob Storage details

## Installatie

Gebruikers kunnen de Docker-containers opzetten en starten met Docker Compose. Dit project maakt gebruik van twee configuratiebestanden voor ontwikkel- en productieomgevingen:

- **Voor de ontwikkelomgeving:**
```bash
git clone https://github.com/pxl-research/PiXie.git
cd PiXie
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build -d # Start de ontwikkelomgeving
```

- **Voor de ontwikkelomgeving:**
```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d  # Start de productieomgeving
```

## Gebruik

### Ontwikkelomgeving

In de ontwikkelomgeving wordt de hele workspace gekopieerd, zodat live code aangepast kan worden. Gebruik de volgende stappen:

1. Open een bash-sessie in de Docker-container:
```bash
docker exec -it pixie-web-1 /bin/bash
```

2.	Om het uploadsysteem te starten (draait op poort 7861):
```bash
uv run src/app/upload.py
```

3.	Om het vraag-en-antwoord systeem te starten (draait op poort 7860):
```bash
uv run src/app/chat.py
```

### Productieomgeving

In de productieomgeving worden de scripts automatisch uitgevoerd tijdens het opstarten van de Docker-container. Na het starten van de containers kun je direct naar de pagina’s surfen:

- Het uploadsysteem is toegankelijk op http://localhost:24026
- Het vraag-en-antwoord systeem is toegankelijk op http://localhost:24027

## Afhankelijkheden

Alle afhankelijkheden zijn verpakt in de Docker-container. Het enige wat je nodig hebt is:

- Docker
- Docker Compose

## Achtergrond

PiXie is onderdeel van het speerpuntproject TransformAI van PXL Smart ICT, ontworpen om AI-technologieën zoals RAG te ontwikkelen en toepassen.

## Licentie

Dit project is gelicentieerd onder de MIT-licentie.
