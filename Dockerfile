FROM python:3.12-slim
LABEL authors="APozhar"

COPY requirements.txt requirements.txt
RUN python -m pip install --upgrade pip && pip install -r requirements.txt


COPY app ./app
COPY *.py ./


CMD ["python", "main.py"]