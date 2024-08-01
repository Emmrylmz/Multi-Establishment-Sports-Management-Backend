# Use the official Python 3.11 slim image from the Docker Hub
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Copy .env file
COPY .env /app/.env

# Set environment variables
ENV ENV_FILE=/app/.env
ENV PYTHONUNBUFFERED 1
ENV FIREBASE_CREDENTIALS_PATH=/service/firebaseKey.json

# Ensure the Firebase credentials file is in the correct path
COPY app/service/firebaseKey.json /service/firebaseKey.json

COPY requirements.txt constraints.txt ./

# Copy the wait-for-it.sh script into the container and make it executable
COPY ./wait-for-it.sh ./wait-for-it.sh
RUN chmod +x /app/wait-for-it.sh

# Copy constraints.txt into the container
COPY constraints.txt /app/

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt -c constraints.txt

# Expose port 80 to the world outside this container
EXPOSE 80 5555

# Debugging step: Check if wait-for-it.sh is in the correct location and has execute permissions
RUN ls -l /app/wait-for-it.sh

# Command to run the application with wait-for-it.sh
CMD ["bash", "./wait-for-it.sh", "rabbitmq.rabbitmq-cluster.svc.cluster.local:5672", "--", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]
