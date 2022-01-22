FORCE: ;
DNS:=ssievert@opt-a001.discovery.wisc.edu

loop: clean stop
	docker-compose rm -f
	docker-compose build
	docker-compose up -d  --remove-orphans  # start in background
	docker-compose logs -f

stop: FORCE
	docker-compose stop

login: FORCE
	docker run -i -t salmon_server /bin/bash

watch: FORCE
	# for debugging on ec2, `sudo make watch`
	docker-compose logs -f

clean: FORCE
	rm -f creds.json
	rm -f out/dump*.rdb
	rm -f out/salmon*.log
	rm -f out/redis.csv

paper: FORCE
	# from https://joss.readthedocs.io/en/latest/submitting.html#docker
	docker run --rm \
    --volume $(PWD)/paper:/data \
    --user $(id -u):$(id -g) \
    --env JOURNAL=joss \
    openjournals/paperdraft

up:
	rsync --exclude '.mypy_cache' --exclude 'docs' -v -r . $(DNS):~/salmon/

down:
	# scp -r $(DNS):~/salmon/examples/queries-searched/data-score-probs cluster-data-score-probs
	scp -r $(DNS):~/salmon/examples/queries-searched/data cluster-data-score-probs

paper: FORCE
	docker run --rm --volume $(PWD)/paper:/data --user $(id -u):$(id -g) --env JOURNAL=joss openjournals/paperdraft

