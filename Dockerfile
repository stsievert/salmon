FROM continuumio/miniconda3:4.7.12

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
COPY salmon.yml /salmon/salmon.yml
RUN conda env update --file /salmon/salmon.yml --prefix $(which python)/../..

# to view Dask dashboard
RUN pip install jupyter-server-proxy

VOLUME /salmon
VOLUME /data
COPY *.py *.cfg *.yml *.txt *.sh /salmon/
COPY ./salmon/ /salmon/salmon/
RUN ls /salmon
RUN pip install -e /salmon

RUN chmod +x /salmon/launch.sh
RUN chown -R docker /salmon
RUN chmod +rw /salmon
# ENTRYPOINT bash launch.sh
WORKDIR /salmon
CMD ["bash", "launch.sh"]
