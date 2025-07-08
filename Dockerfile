FROM python:3.12-slim
LABEL authors="APozhar"

COPY app ./app
COPY requirements.txt requirements.txt
COPY *.py ./

RUN python -m pip install --upgrade pip && pip install -r requirements.txt
RUN apt update -y && apt install ffmpeg -y

CMD ["python", "main.py"]