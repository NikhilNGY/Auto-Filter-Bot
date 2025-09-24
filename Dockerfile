# Use official Python 3.11 image
FROM python:3.11-slim

# Set working directory
WORKDIR /Auto-Filter-Bot

# Copy all project files
COPY . /Auto-Filter-Bot

# Upgrade pip
RUN pip install --upgrade pip

# Install Python dependencies
RUN pip install -r requirements.txt

# Expose port if needed (optional)
# EXPOSE 8080

# Start the bot
CMD ["python", "bot.py"]