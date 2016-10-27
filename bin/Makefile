SHELL = /bin/bash #requires bash
VENV = $(PWD)/.venv/
DEPS = $(wildcard *.py)
TMP_PIP = $(VENV)/get-pip.py
PYTHON3 := $(shell command -v python3 2> /dev/null)
WGET := $(shell command -v wget 2> /dev/null)

.PHONY: setup lint clean test help

.DEFAULT_GOAL := build

help:
	@echo "Make options for oe-chef development"
	@echo
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-10s\033[0m %s\n", $$1, $$2}'

$(VENV):
ifndef PYTHON3
    $(error "python3 is not installed.")
endif
ifndef WGET
    $(error "wget is not installed.")
endif
	test -d $(VENV) || python3 -m venv --without-pip $(VENV); \
	touch $(VENV); \
	. $(VENV)/bin/activate; \
	wget -O $(TMP_PIP) https://bootstrap.pypa.io/get-pip.py; \
	python3 $(TMP_PIP); \
	pip3 install pylint nose flake8;

setup: $(VENV) ## Install all python dependencies in virtualenv

clean: ## Delete virtualenv and all build directories
	rm -rf $(VENV)

test: setup ## Run tests
	. $(VENV)/bin/activate; python3 test/test_oe_chef.py

lint: setup ## Run pylint
	. $(VENV)/bin/activate; pylint $(DEPS)
