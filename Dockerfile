FROM continuumio/miniconda3:4.7.12
WORKDIR /usr/src/salmon/

RUN apt-get update
RUN apt-get install -y gcc cmake g++

# from https://hub.docker.com/r/daskdev/dask/dockerfile
RUN pip install --ignore-installed PyYAML
RUN conda install --yes \
    -c conda-forge \
    python==3.8 \
    python-blosc \
    cytoolz \
    dask==2.20.0 \
    lz4 \
    nomkl \
    numpy==1.18.1 \
    pandas==1.0.1 \
    tini==0.18.0

RUN pip install --ignore-installed PyYAML
COPY salmon.yml .
RUN conda env update --file salmon.yml --prefix $(which python)/../..

COPY setup.py versioneer.py setup.cfg ./
COPY salmon/ salmon/
RUN ls
RUN pip install -e .

CMD ["bash", "launch.sh"]
