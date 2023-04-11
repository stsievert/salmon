FROM mambaorg/micromamba:1.4.2-bionic

VOLUME /salmon
VOLUME /data

RUN micromamba --version
COPY --chown=$MAMBA_USER:$MAMBA_USER salmon.lock.yml /salmon/salmon.lock.yml
RUN micromamba create -n salmon
RUN micromamba install -y -n salmon -f /salmon/salmon.lock.yml && sudo $(which micromamba) clean --all --yes

# RUN apt-get update
# RUN apt-get install -y gcc cmake g++

COPY --chown=$MAMBA_USER:$MAMBA_USER *.py *.cfg *.yml *.txt *.sh /salmon/
COPY --chown=$MAMBA_USER:$MAMBA_USER ./salmon/ /salmon/salmon/
RUN ls /salmon

RUN chmod +x /salmon/launch.sh
RUN chmod +rw /salmon

RUN micromamba run -n salmon pip install -e /salmon[server]

WORKDIR /salmon
CMD ["micromamba", "run", "-n", "salmon", "/bin/bash", "launch.sh"]
