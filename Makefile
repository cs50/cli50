.PHONY: build
build: clean
	python3 setup.py sdist

.PHONY: clean
clean:
	rm -rf *.egg-info build dist

.PHONY: install
install: build
	pip install dist/cli50*.tar.gz
