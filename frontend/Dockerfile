FROM continuumio/miniconda3
WORKDIR /usr/src/salmon/frontend

RUN apt-get update
RUN apt-get install -y gcc
RUN conda install -y numpy scipy pandas scikit-learn ujson

COPY requirements.txt .
RUN pip install -r requirements.txt
RUN conda install -c anaconda msgpack-python

CMD ["bash", "launch.sh"]
