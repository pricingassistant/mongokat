FROM debian:jessie

# Add extra repositories
RUN apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv EA312927
RUN echo "deb http://repo.mongodb.org/apt/debian wheezy/mongodb-org/3.2 main" | tee /etc/apt/sources.list.d/mongodb-org-3.2.list

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