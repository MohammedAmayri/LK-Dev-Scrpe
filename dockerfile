# Use an official Python runtime as a base image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Copy the local project files to the container
COPY . .

# Install system dependencies for Tesseract, OpenCV, and any other required packages
RUN apt-get update && \
    apt-get install -y tesseract-ocr poppler-utils libgl1-mesa-glx && \
    apt-get clean

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set environment variable for Tesseract path (if needed)
ENV TESSDATA_PREFIX=/usr/share/tesseract-ocr/4.00/tessdata

# Expose the port your app runs on (default for Flask is 5000)
EXPOSE 5000

# Run the application
CMD ["python", "app.py"]
