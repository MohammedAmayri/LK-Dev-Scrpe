# Use Python base image
FROM python:3.11-slim-bullseye

# Install CA certificates and other dependencies, including the Swedish Tesseract language pack
RUN apt-get update && apt-get install -y \
    ca-certificates \
    libgl1-mesa-glx \
    libglib2.0-0 \
    tesseract-ocr \
    tesseract-ocr-swe \  # Add Swedish language pack
    poppler-utils \
    python3-dev \
    build-essential \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy the Zscaler certificate into the container
COPY Zscaler.crt /usr/local/share/ca-certificates/Zscaler.crt

# Add Zscaler's certificate to the trusted CA bundle
RUN update-ca-certificates

# Upgrade pip and setuptools
RUN pip install --upgrade pip setuptools wheel

# Set the working directory
WORKDIR /app

# Copy application code
COPY . /app

# Install Python dependencies
RUN pip install --no-cache-dir --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt

# Expose port
EXPOSE 8080

# Run the application
CMD ["flask", "run", "--host=0.0.0.0", "--port=8080"]
