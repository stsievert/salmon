FORCE: ;

loop: FORCE
	docker-compose stop
	docker-compose rm -f
	docker-compose build
	docker-compose up -d  --remove-orphans  # start in background
	docker-compose logs -f

release: FORCE
	echo "Run these commands:\n\ngit tag -a VERSION\npython versioning.py\ngit add .; git commit --amend\ngit push --tags"

frontend: FORCE
	docker run -i -t salmon /bin/bash

backend: FORCE
	docker run -i -t salmon /bin/bash

watch: FORCE
	# for debugging on ec2, `sudo make watch`
	docker-compose logs -f
