FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir streamlit==1.39.0 httpx==0.27.2

COPY dashboard.py .

EXPOSE 8501

CMD ["streamlit", "run", "dashboard.py", "--server.address=0.0.0.0"]
