FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ src/
COPY config/ config/
COPY setup.py .
COPY README.md .

# Install package
RUN pip install -e .

# Create necessary directories
RUN mkdir -p data/raw data/processed data/graphs logs models

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV APP_ENV=production

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "atticus.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
