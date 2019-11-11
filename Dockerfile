FROM continuumio/miniconda3
WORKDIR /usr/src/tmp

RUN apt install -y gcc
RUN conda install -y numpy scipy pandas scikit-learn ujson

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY salmon salmon
COPY templates templates
CMD ["uvicorn", "salmon:app", "--port", "8000", "--host", "0.0.0.0"]
