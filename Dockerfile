# Use an official Python runtime as a parent image
# We use a lightweight base image (slim-buster)
FROM python:3.11-slim-buster

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the working directory
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the working directory
COPY main.py .
ENV PORT 8080

# --- PRODUCTION-GRADE STARTUP COMMAND ---
# Use Gunicorn as the process manager with Uvicorn workers.
# This avoids the fragile pure Uvicorn setup and correctly uses the $PORT.
CMD exec gunicorn --bind 0.0.0.0:$PORT --workers 1 --worker-class uvicorn.workers.UvicornWorker main:app
