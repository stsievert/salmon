FROM continuumio/miniconda3
WORKDIR /usr/src/tmp

RUN apt-get update
RUN apt-get install -y gcc
RUN conda install -y numpy scipy pandas scikit-learn ujson

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY backend backend
CMD ["uvicorn", "backend:app", "--port", "8400", "--host", "0.0.0.0"]
