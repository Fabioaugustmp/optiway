# Solver Service Dockerfile
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copia o serviço do solver
COPY solver_service/ /app/solver_service/

EXPOSE 8002

CMD ["uvicorn", "solver_service.main:app", "--host", "0.0.0.0", "--port", "8002"]
