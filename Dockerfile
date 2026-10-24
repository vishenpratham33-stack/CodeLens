FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# libraries first: Docker re-uses this layer when only your code changes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY codelens ./codelens
COPY web ./web
COPY sample_docs ./sample_docs

# run as a normal user, not as root
RUN useradd --create-home appuser && mkdir /data && chown appuser /data
USER appuser

EXPOSE 8000
VOLUME /data


CMD python -m codelens serve --host 0.0.0.0 --port ${PORT:-8000} --data-dir /data --folder /app/sample_docs --behind-proxy
