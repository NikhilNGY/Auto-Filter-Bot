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
    ffmpeg \
    && apt-get clean \
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
# Expose port for UptimeRobot
# ----------------------------
EXPOSE 8080
ENV PORT=8080

# ----------------------------
# Run the bot
# ----------------------------
CMD ["python", "-u", "bot.py"]
