FROM python:3.11

WORKDIR /Auto-Filter-Bot

COPY . /Auto-Filter-Bot

# Upgrade pip and install requirements
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

CMD ["python", "bot.py"]