JACK_FILES := $(wildcard ArrayTest/*.jack ExpressionLessSquare/*.jack Square/*.jack)
XML_FILES := $(JACK_FILES:.jack=.xml)

all: $(XML_FILES)

%.xml: %.jack jack_analyzer.py
	python3 jack_analyzer.py $<

clean:
	rm -f $(XML_FILES)

re: clean all

.PHONY: all clean re
