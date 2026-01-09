# Flight Crawler Dockerfile
# Usa imagem oficial do Playwright com browsers e deps já instalados
FROM mcr.microsoft.com/playwright/python:v1.41.0-jammy

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY flight_crawler/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copia somente o diretório do crawler
COPY flight_crawler/ /app/flight_crawler/

EXPOSE 8001

CMD ["uvicorn", "flight_crawler.main:app", "--host", "0.0.0.0", "--port", "8001"]
