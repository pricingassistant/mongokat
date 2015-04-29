virtualenv:
	rm -rf venv
	virtualenv venv
	sh -c "source venv/bin/activate && pip install -r requirements.txt"
	echo "Now do: source venv/bin/activate"

test:
	py.test tests/ -v