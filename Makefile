.PHONY: build
build: clean
	ln -f -s README.md README.txt
	python3 setup.py sdist

.PHONY: clean
clean:
	rm -rf *.egg-info build dist

.PHONY: install
install: build
	pip install dist/cli50*.tar.gz
