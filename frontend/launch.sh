#!/bin/bash

if [ $SALMON_DEBUG ]
then
    uvicorn frontend:app --reload --port 8421 --host 0.0.0.0
else
    gunicorn -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8421 frontend:app
fi

