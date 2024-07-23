# Use the official Python image from the Docker Hub
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY . .

# Set environment variables
ENV FLASK_APP=app.py

# Expose the port on which the app will run
EXPOSE 8000

# Run the application
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-8000} app:app"]