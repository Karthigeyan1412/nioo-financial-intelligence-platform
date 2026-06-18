install:
	pip install -r requirements.txt

test:
	pytest

freeze:
	pip freeze > requirements.txt

run:
	python src/main.py