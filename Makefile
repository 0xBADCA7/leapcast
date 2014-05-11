.PHONY: clean-pyc clean-build docs

help:
	@echo "clean-build - remove build artifacts"
	@echo "clean-pyc - remove Python file artifacts"
	@echo "test - run tests quickly with the default Python"
	@echo "release - package and upload a release"
	@echo "sdist - package"

clean: clean-build clean-pyc clean-proto

clean-build:
	rm -fr build/
	rm -fr dist/
	rm -fr *.egg-info

clean-pyc:
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +

clean-proto:
	rm leapcast/cast_proto/cast_channel_pb2.py

test:
	flake8 leapcast --ignore=E501,F403

proto:
	protoc -I=leapcast/cast_proto/ --python_out=leapcast/cast_proto/ leapcast/cast_proto/cast_channel.proto

release: clean
	pandoc --from=markdown --to=rst --output=README.rst README.md
	python setup.py sdist upload

sdist: clean
	python setup.py sdist
	ls -l dist
