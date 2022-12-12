DOC_DIR = './docs/'
STUB_DIR = './docs/source/rst/'


.Phony: doc 
doc:
			sphinx-apidoc -o docs/source/rst/icepolcka_utils icepolcka_utils/icepolcka_utils --separate
			cd $(DOC_DIR) && make html

.Phony: clean
clean:
			cd $(STUB_DIR)/icepolcka_utils && rm *.rst
			cd $(DOC_DIR) && make clean

