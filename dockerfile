# Start from the Python base image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Copy all project files into the container
COPY . .

# Install dependencies and utilities, including CA certificates and libssl-dev
RUN apt-get update && \
    apt-get install -y tesseract-ocr poppler-utils libgl1-mesa-glx ca-certificates libssl-dev && \
    apt-get clean && \
    update-ca-certificates

# Install pip, certifi and necessary dependencies with SSL verification temporarily disabled for pip
RUN pip install --upgrade pip --trusted-host pypi.org --trusted-host files.pythonhosted.org --trusted-host pypi.python.org \
    certifi pip-system-certs gunicorn -r requirements.txt --disable-pip-version-check

# Set SSL_CERT_FILE environment variable to use certifi's CA bundle
ENV SSL_CERT_FILE=/usr/local/lib/python3.12/site-packages/certifi/cacert.pem

# Expose the port Flask is using
EXPOSE 5000

# Run the app with gunicorn
CMD ["gunicorn", "-b", "0.0.0.0:5000", "app:app"]
