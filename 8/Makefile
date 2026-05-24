SINGLE_VM := ProgramFlow/BasicLoop/BasicLoop.vm \
             ProgramFlow/FibonacciSeries/FibonacciSeries.vm \
             FunctionCalls/SimpleFunction/SimpleFunction.vm

MULTI_VM_DIRS := FunctionCalls/NestedCall \
                 FunctionCalls/FibonacciElement \
                 FunctionCalls/StaticsTest

SINGLE_ASM := $(SINGLE_VM:.vm=.asm)
MULTI_ASM := $(foreach d,$(MULTI_VM_DIRS),$(d)/$(notdir $(d)).asm)

all: $(SINGLE_ASM) $(MULTI_ASM)

%.asm: %.vm vm_translator.py
	python3 vm_translator.py $<

$(MULTI_ASM): vm_translator.py
	python3 vm_translator.py $(dir $@)

clean:
	rm -f $(SINGLE_ASM) $(MULTI_ASM)

re: clean all

.PHONY: all clean re
