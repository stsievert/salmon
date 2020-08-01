FORCE: ;

loop: clean stop
	docker-compose rm -f
	docker-compose build
	docker-compose up -d  --remove-orphans  # start in background
	docker-compose logs -f

stop: FORCE
	docker-compose stop

release: FORCE
	echo "Run these commands:\n\ngit tag -a VERSION\npython versioning.py\ngit add .; git commit --amend\ngit push --tags"

login: FORCE
	docker run -i -t salmon_server /bin/bash

watch: FORCE
	# for debugging on ec2, `sudo make watch`
	docker-compose logs -f

clean: FORCE
	rm -f out/dump*.rdb
	rm -f out/salmon*.log
	rm -f out/redis.csv
