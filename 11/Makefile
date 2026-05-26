JACK_FILES := $(wildcard Seven/*.jack ConvertToBin/*.jack Square/*.jack Average/*.jack Pong/*.jack ComplexArrays/*.jack)
VM_FILES := $(JACK_FILES:.jack=.vm)

all: $(VM_FILES)

%.vm: %.jack jack_compiler.py
	python3 jack_compiler.py $<

clean:
	rm -f $(VM_FILES)

re: clean all

.PHONY: all clean re
