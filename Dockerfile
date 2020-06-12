FROM continuumio/miniconda3
WORKDIR /usr/src/salmon/

RUN apt-get update
RUN apt-get install -y gcc
COPY salmon.yaml .
RUN conda env create -f salmon.yaml
RUN conda activate salmon

CMD ["bash", "launch.sh"]
