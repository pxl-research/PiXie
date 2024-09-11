# PiXie - Retrieval-Augmented Generation (RAG) Project

## Korte beschrijving

PiXie is een geavanceerde implementatie van Retrieval-Augmented Generation (RAG) in Python. Het project is een concrete realisatie binnen het speerpuntproject **TransformAI** van **PXL Smart ICT**, en biedt een eenvoudige manier om antwoorden te genereren door informatie op te halen uit externe kennisbronnen. PiXie is verpakt in een Docker-container voor gemakkelijk gebruik en bevat een webinterface voor interactie.

## Functies

- Ondersteunt Retrieval-Augmented Generation (RAG), waarbij informatie uit documenten wordt opgehaald en gecombineerd met generatieve AI-modellen om nauwkeurige antwoorden te geven.
- Mogelijkheid om documenten te uploaden via een intuïtieve webinterface.
- Geeft gebruikers de mogelijkheid om vragen te stellen en antwoorden te ontvangen, inclusief bronvermeldingen van de geüploade documenten.
- Volledig verpakt in een Docker-container voor eenvoudige installatie en consistentie.
- Gebruiksvriendelijke interface via Gradio om interacties soepel te laten verlopen.

## Voorbereiding

Voordat je de applicatie kunt starten, moet je een `.env` bestand aanmaken in de hoofdmap van het project. Er is een voorbeeldbestand voorzien genaamd `.env.example`. Hernoem dit bestand naar `.env` en vul de vereiste waarden in. Dit bestand bevat belangrijke configuraties zoals:

- Azure Document Loader instellingen
- Azure Open AI LLM configuratie
- Azure Blob Storage details

## Installatie

Gebruikers kunnen de Docker-container opzetten en starten met Docker Compose:
```bash
git clone https://github.com/pxl-research/PiXie.git
cd PiXie
docker-compose up -d
```

## Gebruik

1. Open een bash-sessie in de Docker-container:
```bash
docker exec -it pixie-web-1 /bin/bash
```

2.	Om het uploadsysteem te starten (draait op poort 7861):
```bash
python upload.py
```

3.	Om het vraag-en-antwoord systeem te starten (draait op poort 7860):
```bash
python chat.py
```

## Afhankelijkheden

Alle afhankelijkheden zijn verpakt in de Docker-container. Het enige wat je nodig hebt is:

- Docker
- Docker Compose

## Achtergrond

PiXie is onderdeel van het speerpuntproject TransformAI van PXL Smart ICT, ontworpen om AI-technologieën zoals RAG te ontwikkelen en toepassen.

## Licentie

Dit project is gelicentieerd onder de MIT-licentie.
