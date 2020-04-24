FORCE: ;

loop: FORCE
	python deploy.py
	docker-compose stop
	docker-compose rm -f
	docker-compose build
	docker-compose up -d  --remove-orphans  # start in background
	docker-compose logs -f

release: FORCE
	echo "Run these commands:\ngit tag -a VERSION\ngit push --tags"

frontend: FORCE
	docker run -i -t salmon_frontend /bin/bash

backend: FORCE
	docker run -i -t salmon_backend /bin/bash

watch: FORCE
	# for debugging on ec2, `sudo make watch`
	docker-compose logs -f
