FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN python -m pip install --no-cache-dir --upgrade pip==26.3
RUN pip install --no-cache-dir -r requirements.txt

COPY *.csv *.py ./

CMD ["python", "automated_seed.py"]
