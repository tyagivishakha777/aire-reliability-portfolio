FROM python:3.12-slim
WORKDIR /app
RUN pip install fastapi uvicorn prometheus-client
COPY app.py .
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]