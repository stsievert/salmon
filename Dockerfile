FROM mambaorg/micromamba:1.4.2-bionic

VOLUME /salmon
VOLUME /data

RUN micromamba --version
COPY --chown=$MAMBA_USER:$MAMBA_USER salmon.lock.yml /salmon/salmon.lock.yml
RUN sudo $(which micromamba) install -y -n base -f /salmon/salmon.lock.yml && sudo $(which micromamba) clean --all --yes

# RUN apt-get update
# RUN apt-get install -y gcc cmake g++

COPY --chown=$MAMBA_USER:$MAMBA_USER *.py *.cfg *.yml *.txt *.sh /salmon/
COPY --chown=$MAMBA_USER:$MAMBA_USER ./salmon/ /salmon/salmon/
RUN ls /salmon

RUN chmod +x /salmon/launch.sh
RUN chmod +rw /salmon

RUN sudo $(which micromamba) run -n base pip install -e /salmon[server]

WORKDIR /salmon
CMD ["micromamba", "run", "-n", "base", "/bin/bash", "launch.sh"]
