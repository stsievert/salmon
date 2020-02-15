loop:
	docker-compose stop
	docker-compose build
	docker-compose up -d  --remove-orphans  # start in background

login:
	docker run -i -t salmon_frontend /bin/bash

watch:
	docker-compose logs -f
