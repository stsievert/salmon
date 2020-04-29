#!/bin/bash

if [ $SALMON_DEBUG ]
then
    uvicorn salmon:backend --reload --port 8400 --host 0.0.0.0 &
    sleep 1
    uvicorn salmon:frontend --reload --port 8421 --host 0.0.0.0
else
    gunicorn -w 1 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8400 salmon:backend
    sleep 1
    gunicorn -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8421 salmon:frontend
fi
