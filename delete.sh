#!/bin/bash

# Define RabbitMQ credentials
HOST="localhost"
PORT="15672"
USERNAME="guest"
PASSWORD="guest"

# List all queue names and delete each one
rabbitmqadmin --host=$HOST --port=$PORT --username=$USERNAME --password=$PASSWORD list queues name -f tsv | while read -r QUEUE_NAME; do
    rabbitmqadmin --host=$HOST --port=$PORT --username=$USERNAME --password=$PASSWORD delete queue name=$QUEUE_NAME
    echo "Deleted queue: $QUEUE_NAME"
done
