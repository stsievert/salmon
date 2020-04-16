FROM continuumio/miniconda3
WORKDIR /usr/src/tmp

RUN apt-get update
RUN apt-get install -y gcc
RUN conda install -y numpy scipy pandas scikit-learn ujson

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY frontend frontend
COPY templates templates
RUN echo never > /sys/kernel/mm/transparent_hugepage/enabled
RUN echo never > /sys/kernel/mm/transparent_hugepage/defrag
CMD ["uvicorn", "frontend:app", "--port", "8421", "--host", "0.0.0.0"]
