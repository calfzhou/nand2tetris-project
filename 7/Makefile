VM_FILES := $(wildcard StackArithmetic/*/*.vm MemoryAccess/*/*.vm)
ASM_FILES := $(VM_FILES:.vm=.asm)

all: $(ASM_FILES)

%.asm: %.vm vm_translator.py
	python3 vm_translator.py $<

clean:
	rm -f $(ASM_FILES)

re: clean all

.PHONY: all clean re
