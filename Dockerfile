FROM debian:jessie

# Add extra repositories
RUN apt-get update && apt-get install -y --no-install-recommends wget apt-transport-https ca-certificates

RUN wget -qO - https://www.mongodb.org/static/pgp/server-3.6.asc | apt-key add -

RUN echo "deb http://repo.mongodb.org/apt/debian wheezy/mongodb-org/3.6 main" | tee /etc/apt/sources.list.d/mongodb-org-3.6.list

RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
		sudo \
		mongodb-org \
		gcc \
		make \
		g++ \
		build-essential \
		python-pip \
		python-dev \
		python3-pip \
		python3-dev

# Upgrade pip
RUN pip install --upgrade --ignore-installed pip
RUN pip3 install --upgrade --ignore-installed pip

# Put Python pip requirements files
ADD requirements.txt /tmp/requirements.txt
ADD requirements-tests.txt /tmp/requirements-tests.txt

RUN pip3 install -r /tmp/requirements.txt
RUN pip3 install -r /tmp/requirements-tests.txt

RUN pip install -r /tmp/requirements.txt
RUN pip install -r /tmp/requirements-tests.txt

RUN mkdir -p /data/db