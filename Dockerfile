FROM continuumio/miniconda3:4.9.2

RUN apt-get update
RUN apt-get install -y gcc cmake g++
RUN conda -V

COPY salmon.yml /salmon/salmon.yml
RUN conda env update --file /salmon/salmon.yml --prefix $(which python)/../..
RUN pip install PyYAML==5.4.1

VOLUME /salmon
VOLUME /data
COPY *.py *.cfg *.yml *.txt *.sh /salmon/
COPY ./salmon/ /salmon/salmon/
RUN ls /salmon
RUN pip install -e /salmon

RUN chmod +x /salmon/launch.sh
RUN chmod +rw /salmon
# ENTRYPOINT bash launch.sh
WORKDIR /salmon
CMD ["bash", "launch.sh"]
