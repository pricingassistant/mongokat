virtualenv:
	rm -rf venv
	virtualenv venv
	sh -c "source venv/bin/activate && pip install -r requirements.txt"
	echo "Now do: source venv/bin/activate"

test:
	py.test tests/ -v

docs:
	pip install pdoc==0.3.1
	sh -c "PYTHONPATH=. pdoc mongokat --html --html-dir doc"