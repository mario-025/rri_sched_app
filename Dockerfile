# Gunakan official Python runtime sebagai base image
FROM python:3.11-slim

# Set working directory di container
WORKDIR /app

# Set environment variables
# Mencegah Python dari menulis pyc files dan buffering stdout/stderr
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Install system dependencies yang diperlukan untuk MySQL connection
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements.txt dan install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy seluruh aplikasi ke container
COPY . .

# Expose port 5000 (Flask default port)
EXPOSE 5000

# Health check - cek apakah aplikasi masih berjalan
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:5000/health', timeout=5)" || exit 1

# Command untuk menjalankan aplikasi
CMD ["python", "run.py"]
