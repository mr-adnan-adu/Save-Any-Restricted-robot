FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY main.py .

# Create necessary directories
RUN mkdir -p /tmp/downloads

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Expose port (if needed for web service)
EXPOSE 8000

# Run the application
CMD ["python", "main.py"]
