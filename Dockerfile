# Use the official Python 3.11 slim image from the Docker Hub
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Copy .env file
COPY .env .env

ENV PYTHONUNBUFFERED 1

# Ensure the Firebase credentials file is in the correct path
COPY app/service/firebaseKey.json /service/firebaseKey.json

COPY /app/wait-for-it.sh /wait-for-it.sh

RUN chmod +x /wait-for-it.sh
# Set environment variable for Firebase credentials
ENV FIREBASE_CREDENTIALS_PATH=/service/firebaseKey.json

# Copy constraints.txt into the container
COPY constraints.txt /app/

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt -c constraints.txt

# Expose port 80 to the world outside this container
EXPOSE 80

# Command to run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]
