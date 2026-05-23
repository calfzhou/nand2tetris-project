ASM_FILES := $(wildcard add/*.asm max/*.asm rect/*.asm pong/*.asm)
HACK_FILES := $(ASM_FILES:.asm=.hack)

all: $(HACK_FILES)

%.hack: %.asm hack_assembler.py
	python3 hack_assembler.py $<

clean:
	rm -f $(HACK_FILES)

re: clean all

.PHONY: all clean re
