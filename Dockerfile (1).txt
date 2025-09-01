FROM python:3.10

# Set working directory
WORKDIR /TamilanBotsZ

# Copy dependency file first (for caching)
COPY requirements.txt ./

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the project files
COPY . .

# Start the bot
CMD ["python3", "bot.py"]
