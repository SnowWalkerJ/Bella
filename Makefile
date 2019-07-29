.PHONY: clean build dependency install

clean:
	rm -r build dist bella.egg-info

build:
	python setup.py build_dist

dependency:
	pip install -r requirements.txt

install: dependency
	python setup.py install
