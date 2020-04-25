#!/bin/bash

# This is a very minimal server; the only endpoints are
# /init and /model. Running it at scale isn't necessary

if [ $SALMON_DEBUG ]
then
    uvicorn backend:app --reload --port 8400 --host 0.0.0.0
else
    gunicorn -w 1 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8400 backend:app
fi

