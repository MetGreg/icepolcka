PACKAGE_DIR = '../icepolcka_utils'

.Phony: coverage
coverage:
			cd tests && python3 -m coverage run --source=$(PACKAGE_DIR) -m unittest && python3 -m coverage report && python3 -m coverage html

