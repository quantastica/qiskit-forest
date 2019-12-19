#!/bin/bash
set -e

# Remove previous build
rm -rf ./build/
rm -rf ./dist/
rm -rf ./*.egg-info/

python3 setup.py sdist bdist_wheel
twine check dist/*

if [[ "$1" == "test" ]]; then
	echo "*** Publishing to TEST ***"
	twine upload --repository-url https://test.pypi.org/legacy/ dist/*
else
	if [[ "$1" == "production" ]]; then
		echo "*** Publishing to PRODUCTION ***"
		twine upload dist/*
	else
		echo "Please specify 'test' or 'production'"
	fi
fi
