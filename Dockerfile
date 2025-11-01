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

# Make port 8000 available to the world outside this container
EXPOSE 8000

# Run the application using Uvicorn with gunicorn workers (for production stability)
# The command starts your application when the container launches.
# We bind it to 0.0.0.0 so it is accessible outside the container.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
