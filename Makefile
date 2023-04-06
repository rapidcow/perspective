PY3 = /usr/bin/env python3
.PHONY: help install test

help:
	@echo "hi this is a makefile i wrote"
	@echo "targets below:"
	@echo
	@echo "  make help    : this you are seeing"
	@echo "  make install : install psp"
	@echo "  make dev     : install psp in editable mode"
	@echo "  make test    : run unittest + doctest"

test:
	@$(PY3) -m unittest discover .
	@cd docs && make doctest

install:
	@$(PY3) -m pip install ./src

uninstall:
	@$(PY3) -m pip uninstall perspe -y

dev:
	@$(PY3) -m pip install -e ./src
