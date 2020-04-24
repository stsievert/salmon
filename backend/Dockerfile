FROM continuumio/miniconda3
WORKDIR /usr/src/salmon/backend

RUN apt-get update
RUN apt-get install -y gcc
RUN conda install -y numpy scipy pandas scikit-learn ujson

COPY requirements.txt .
RUN pip install -r requirements.txt

# This is a very minimal server; the only endpoints are
# /init and /model. Running it at scale isn't necessary
CMD uvicorn backend:app --reload --port 8400 --host 0.0.0.0
