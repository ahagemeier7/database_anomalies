FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN pip install --no-cache-dir pandas sqlalchemy psycopg2-binary

COPY *.csv *.py ./

CMD ["python", "automated_seed.py"]
