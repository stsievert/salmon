FROM redislabs/rejson

# Run https://github.com/junegunn/redis-stat
RUN apt update && apt install -y wget
RUN apt-get install -y ruby-full
RUN apt-get install -y build-essential
RUN gem install redis-stat

CMD redis-stat redis:6379 --csv=/salmon/logs/redis.csv 5 --server=7389
