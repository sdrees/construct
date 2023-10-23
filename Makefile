help:
	cat Makefile

test:
	python3.10 -m pytest --benchmark-disable --showlocals

verbose:
	python3.10 -m pytest --benchmark-disable --showlocals --verbose

xfails:
	python3.10 -m pytest --benchmark-disable --verbose | egrep --color=always "xfail|XFAIL|xpass|XPASS"

cover:
	python3.10 -m pytest --benchmark-disable --cov construct --cov-report html --cov-report term --verbose

bench:
	python3.10 -m pytest --benchmark-enable --benchmark-columns=min,stddev --benchmark-sort=name --benchmark-compare

benchsave:
	python3.10 -m pytest --benchmark-enable --benchmark-columns=min,stddev --benchmark-sort=name --benchmark-compare --benchmark-autosave

html:
	cd docs; make html

installdeps:
	apt-get install python3.10 python3-pip python3-sphinx --upgrade
	python3.10 -m pip install pytest pytest-benchmark pytest-cov twine wheel --upgrade
	python3.10 -m pip install numpy arrow ruamel.yaml cloudpickle lz4 cryptography --upgrade

version:
	./version-increment

upload:
	python3.10 ./setup.py sdist bdist_wheel
	python3.10 -m twine check dist/*
	python3.10 -m twine upload dist/*

