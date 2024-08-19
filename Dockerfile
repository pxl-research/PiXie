FROM python:3.11

# Update the package list
RUN apt-get update

# Install pandoc
RUN apt-get install -y pandoc

WORKDIR /app

COPY . /app

RUN pip install -r requirements.txt
RUN pip install pipreqs

ENV PYTHONPATH="/app:/app/services"