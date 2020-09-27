#FROM python:3.8-slim-buster
FROM tiangolo/uvicorn-gunicorn-fastapi:python3.8-slim

#RUN apt upgrade -y && apt install bash

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

WORKDIR /server
ADD ./src ./src
COPY ./test ./test

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "80"]
