# Use an official Python runtime as a parent image
# We use a lightweight base image (slim-buster)
FROM python:3.11-slim-buster

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the working directory
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the working directory
COPY main.py .

ENV PORT 8080
CMD uvicorn main:app --host 0.0.0.0 --port $PORT
