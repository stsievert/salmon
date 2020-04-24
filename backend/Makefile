build:
	docker image build -t salmon:1.0 .

run:
	docker container run -p 8000:8000 --name sal salmon:1.0

rm:
	docker container rm --force sal

debug:
	docker exec -it sal /bin/bash
