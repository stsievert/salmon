#!/bin/bash

if [ $SALMON_DEBUG ]
then
    dask-scheduler --port 8786 --dashboard-address :8787 &
    dask-worker --nprocs 4 localhost:8786 &
    uvicorn salmon:app_algs --reload --reload-dir salmon --port 8400 --host 0.0.0.0 &
    sleep 1
    uvicorn salmon:app --reload --reload-dir salmon --reload-dir templates --port 8421 --host 0.0.0.0
else
    # Use shared memory for Gunicorn; apparelty can block on AWS
    # [1]:https://pythonspeed.com/articles/gunicorn-in-docker/
    #
    # Set timeout=90 so Gunicorn checks less frequently.
    # Use preload to reduce startup time
    # Use 2 threads to heartbeat gets sent more often
    gunicorn --preload --worker-tmp-dir /dev/shm --threads 2 --timeout 90 -w 1 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8400 salmon:app_algs &
    # uvicorn salmon:app_algs --reload --port 8400 --host 0.0.0.0 &
    sleep 1
    gunicorn --preload --worker-tmp-dir /dev/shm --threads 2 --timeout 90 -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8421 salmon:app
fi
