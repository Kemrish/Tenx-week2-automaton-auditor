FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Copy dependency files
COPY pyproject.toml .

# Install dependencies
RUN uv pip install --system -e .

# Copy application
COPY src/ ./src/
COPY rubric/ ./rubric/

# Create audit directory
RUN mkdir -p audit

# Set entrypoint
ENTRYPOINT ["python", "-m", "src.graph"]