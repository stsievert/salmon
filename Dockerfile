FROM continuumio/miniconda3:4.10.3

RUN apt-get update
RUN apt-get install -y gcc cmake g++
RUN conda -V

COPY salmon.lock.yml /salmon/salmon.lock.yml
RUN conda env create -f /salmon/salmon.lock.yml

VOLUME /salmon
VOLUME /data
COPY *.py *.cfg *.yml *.txt *.sh /salmon/
COPY ./salmon/ /salmon/salmon/
RUN ls /salmon
RUN conda run -n salmon pip install -e /salmon[server]

RUN chmod +x /salmon/launch.sh
RUN chmod +rw /salmon
# ENTRYPOINT bash launch.sh
WORKDIR /salmon
CMD ["conda", "run", "-n", "salmon", "/bin/bash", "launch.sh"]
