all:
	@echo "\nThere is no default Makefile target right now."
	@echo "Try:\n"
	@echo "make clean - reset the project and remove auto-generated assets."
	@echo "make pyflakes - run the PyFlakes code checker."
	@echo "make pep8 - run the PEP8 style checker."
	@echo "make test - run the test suite."
	@echo "make check - run all the checkers and tests."
	@echo "make docs - run sphinx to create project documentation.\n"

clean:
	rm -rf dist
	rm -rf docs/_build
	find . \( -name '*.py[co]' -o -name dropin.cache \) -print0 | xargs -0 -r rm
	find . -name _trial_temp -type d -print0 | xargs -0 -r rm -r

pyflakes:
	find . \( -name _build -o -name var \) -type d -prune -o -name '*.py' -print0 | $(shell which parallel || which xargs) -0 pyflakes

pep8:
	find . \( -name _build -o -name var \) -type d -prune -o -name '*.py' -print0 | $(shell which parallel || which xargs) -0 -n 1 pep8 --repeat

test: clean
	trial --rterrors --coverage test
	@echo "\nMissing test coverage:"
	@cd _trial_temp/coverage; grep -n -T '>>>>>' drogulus.*

check: pep8 pyflakes test

docs: clean
	cd docs; make html
	@echo "\nDocumentation can be viewed in your browser here:"
	@echo file://`pwd`/docs/_build/html/index.html
	@echo "\n"
