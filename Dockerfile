FROM python:3.11-slim

WORKDIR /app

# Install system deps for pyart / numpy / scipy
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libhdf5-dev libnetcdf-dev && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["python", "run.py", "--host", "0.0.0.0", "--port", "5000", "--monitor"]
