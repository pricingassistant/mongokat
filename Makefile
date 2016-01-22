virtualenv:
	rm -rf venv
	virtualenv venv
	sh -c "source venv/bin/activate && pip install -r requirements.txt"
	echo "Now do: source venv/bin/activate"

test:
	@echo "Remember to start MongoDB first!"
	sh -c "source venv/bin/activate && pip install -r requirements-tests.txt"
	sh -c "source venv/bin/activate && py.test tests/ -v"

doc:
	sh -c "PYTHONPATH=. sphinx-autobuild docs/ docs/_build/html -z mongokat"

test_cext:
	@echo "Remember to start MongoDB first!"
	python setup.py build_ext && cp build/lib.macosx-10.10-intel-2.7/mongokat/_cbson.so mongokat/ && py.test tests -sv

pypi:
	python setup.py sdist upload -r pypi

docker_build:
	docker build -t pricingassistant/mongokat .

docker_ssh:
	docker run -v `pwd`:/app:rw -w /app -t -i pricingassistant/mongokat bash

start_mongod:
	mongod --smallfiles --noprealloc --nojournal &

docker_test: docker_build
	docker run -v `pwd`:/app:rw -w /app -t -i pricingassistant/mongokat sh -c 'make start_mongod && py.test tests/ -v'