FROM python:3.14-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY mail_agent ./mail_agent
USER 10001:10001
CMD ["uvicorn", "mail_agent.api:app", "--host", "0.0.0.0", "--port", "8000"]
