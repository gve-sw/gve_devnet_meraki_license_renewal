# syntax=docker/dockerfile:1
FROM python:3
ENV PYTHONUNBUFFERED=1
COPY . .
RUN pip install -r requirements.txt
WORKDIR /merakirenewal
