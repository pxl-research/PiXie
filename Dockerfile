# Gebruik de basis PyTorch image
FROM nvcr.io/nvidia/pytorch:23.09-py3

# Installeer vereiste pakketten, inclusief python3-venv en andere build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    gcc \
    python3-dev \
    python3-venv \
    libpq-dev \
    build-essential \
    libreoffice \
    pandoc && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Installeer uv en voeg het toe aan het PATH
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy from the cache instead of linking since it's a mounted volume
ENV UV_LINK_MODE=copy

# Werkdirectory instellen en maak een virtuele omgeving aan
WORKDIR /app
RUN rm -rf /app/.venv && python3 -m venv /app/.venv
ENV PATH="/app/.venv/bin:/root/.local/bin:$PATH"

# Kopieer de volledige projectbestanden naar de container
COPY . /app

# Installeer de projectdependencies met uv zonder caching
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Zet het pad voor Python scripts en services
ENV PYTHONPATH="/app/src:/app/src/services"