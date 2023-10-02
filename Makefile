SHELL := /bin/bash

all:
	echo 'Makefile for github-cicd'

init:
	pip install -U pip
	pip install -r req_develop.txt
	pip install -e .

format:
	black .
	isort . --skip-gitignore --profile black

lint:
	pylint pyjevsim > pylint.result.txt
	flake8 pyjevsim > flake8.result.txt

test:
	pytest tests --verbose --cov=pyjevsim/ --cov-report=html --cov-report=term-missing
