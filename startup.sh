#! /bin/bash

# Start docker database
docker run -d --name redis-container -p 6379:6379 redis
