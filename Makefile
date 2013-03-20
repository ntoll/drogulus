clean:
	rm -rf dist
	rm -rf docs/_build
	find . \( -name '*.py[co]' -o -name dropin.cache \) -print0 | xargs -0 -r rm
	find . -name _trial_temp -type d -print0 | xargs -0 -r rm -r

