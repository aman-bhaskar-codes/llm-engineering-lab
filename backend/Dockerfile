FROM python:3.11.8-slim-bookworm

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080

# Install system dependencies required for PDF processing and OCR
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    poppler-utils \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

# Install uv for blazingly fast dependency resolution
RUN pip install uv

# Set the working directory
WORKDIR /app

# Copy dependencies
COPY requirements.txt ./

# Install dependencies using uv
RUN uv pip install --system -r requirements.txt

# Copy the entire backend directory into the container
COPY . .

# Expose the port Cloud Run expects
EXPOSE 8080

# Run FastAPI server
# Since the code is directly in /app (copied from backend/), we run main:app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
