loop:
	docker-compose stop
	docker-compose rm -f
	docker-compose build
	docker-compose up -d  --remove-orphans  # start in background
	docker-compose logs -f

frontend:
	docker run -i -t salmon_frontend /bin/bash

backend:
	docker run -i -t salmon_backend /bin/bash

watch:
	# for debugging on ec2, `sudo make watch`
	docker-compose logs -f
