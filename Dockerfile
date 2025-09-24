# ----------------------------
# Base image
# ----------------------------
FROM python:3.11-slim

# ----------------------------
# Set working directory
# ----------------------------
WORKDIR /Auto-Filter-Bot

# ----------------------------
# System dependencies
# ----------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ----------------------------
# Copy bot files
# ----------------------------
COPY . /Auto-Filter-Bot

# ----------------------------
# Upgrade pip
# ----------------------------
RUN pip install --upgrade pip

# ----------------------------
# Install Python dependencies
# ----------------------------
RUN pip install --no-cache-dir -r requirements.txt

# ----------------------------
# Set environment variables (optional)
# ----------------------------
ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=UTF-8

# ----------------------------
# Run the bot
# ----------------------------
CMD ["python", "bot.py"]
