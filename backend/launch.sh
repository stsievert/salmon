#!/bin/bash

if [ $SALMON_DEBUG ]
then
    uvicorn backend:app --reload --port 8400 --host 0.0.0.0
else
    # Specifically don't use gunicorn. Each algorithm has some state;
    # multiple processes removes that state.
    #
    # This could be different if each worker defined get_query.
    uvicorn backend:app --port 8400 --host 0.0.0.0
fi

