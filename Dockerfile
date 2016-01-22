FROM debian:jessie

# Add extra repositories
RUN apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv 7F0CEB10
RUN echo "deb http://repo.mongodb.org/apt/debian wheezy/mongodb-org/3.0 main" | tee /etc/apt/sources.list.d/mongodb-org-3.0.list

RUN apt-get update
RUN apt-get install -y sudo mongodb-org-server gcc make g++ build-essential python-pip python-dev

# Put Python pip requirements files
ADD requirements.txt /tmp/requirements.txt
ADD requirements-tests.txt /tmp/requirements-tests.txt

RUN pip install -r /tmp/requirements.txt
RUN pip install -r /tmp/requirements-tests.txt

RUN mkdir -p /data/db