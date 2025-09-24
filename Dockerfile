# Use official Python 3.11 image
FROM python:3.11

# Set working directory
WORKDIR /Auto-Filter-Bot

# Copy all files to container
COPY . /Auto-Filter-Bot

# Upgrade pip
RUN pip install --upgrade pip

# Install Python dependencies
RUN pip install -r requirements.txt

# Start the bot
CMD ["python", "bot.py"]