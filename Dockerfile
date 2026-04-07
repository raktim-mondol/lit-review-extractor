FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY process_papers.py /app/process_papers.py
COPY dashboard_api.py /app/dashboard_api.py
COPY columns_config.json /app/columns_config.json

EXPOSE 8000

CMD ["python", "dashboard_api.py"]
