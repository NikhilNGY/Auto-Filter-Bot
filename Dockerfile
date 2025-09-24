# Use official Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /Auto-Filter-Bot

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy bot files
COPY . /Auto-Filter-Bot

# Upgrade pip
RUN pip install --upgrade pip

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Run bot
CMD ["python", "bot.py"]
