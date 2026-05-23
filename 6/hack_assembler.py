"""Hack Assembler — Nand2Tetris Project 6

Translates Hack assembly (.asm) into Hack machine code (.hack).

Implemented:
  - Two-pass assembly (first pass: build symbol table, second pass: generate code)
  - A-instructions: @value → 0 + 15-bit binary address
  - C-instructions: dest=comp;jump → 111 + acccccc + ddd + jjj
  - Full comp table (28 computations, a=0 for A-register, a=1 for M-register)
  - Full dest table (8 destinations: null/M/D/MD/A/AM/AD/ADM)
  - Full jump table (8 conditions: null/JGT/JEQ/JGE/JLT/JNE/JLE/JMP)
  - Predefined symbols: R0–R15, SP, LCL, ARG, THIS, THAT, SCREEN, KBD
  - Label symbols: (LABEL) pseudo-commands mapped to ROM addresses
  - Variable symbols: auto-allocated from RAM[16] onward
  - Comment stripping (// ...) and whitespace handling
  - Streaming I/O: reads the file twice (one pass each) without loading all lines into memory

Usage:
  python3 hack_assembler.py <file.asm>
  → outputs <file.hack> in the same directory
"""

import sys

COMP_TABLE = {
    '0':   '0101010',
    '1':   '0111111',
    '-1':  '0111010',
    'D':   '0001100',
    'A':   '0110000', 'M':   '1110000',
    '!D':  '0001101',
    '!A':  '0110001', '!M':  '1110001',
    '-D':  '0001111',
    '-A':  '0110011', '-M':  '1110011',
    'D+1': '0011111',
    'A+1': '0110111', 'M+1': '1110111',
    'D-1': '0001110',
    'A-1': '0110010', 'M-1': '1110010',
    'D+A': '0000010', 'D+M': '1000010',
    'D-A': '0010011', 'D-M': '1010011',
    'A-D': '0000111', 'M-D': '1000111',
    'D&A': '0000000', 'D&M': '1000000',
    'D|A': '0010101', 'D|M': '1010101',
}

DEST_TABLE = {
    None:  '000',
    'M':   '001',
    'D':   '010',
    'MD':  '011', 'DM':  '011',
    'A':   '100',
    'AM':  '101', 'MA':  '101',
    'AD':  '110', 'DA':  '110',
    'ADM': '111', 'AMD': '111', 'DAM': '111', 'DMA': '111', 'MAD': '111', 'MDA': '111',
}

JUMP_TABLE = {
    None:  '000',
    'JGT': '001',
    'JEQ': '010',
    'JGE': '011',
    'JLT': '100',
    'JNE': '101',
    'JLE': '110',
    'JMP': '111',
}

PREDEFINED_SYMBOLS = {
    'R0': 0, 'R1': 1, 'R2': 2, 'R3': 3,
    'R4': 4, 'R5': 5, 'R6': 6, 'R7': 7,
    'R8': 8, 'R9': 9, 'R10': 10, 'R11': 11,
    'R12': 12, 'R13': 13, 'R14': 14, 'R15': 15,
    'SP': 0, 'LCL': 1, 'ARG': 2, 'THIS': 3, 'THAT': 4,
    'SCREEN': 16384, 'KBD': 24576,
}


def clean(line):
    line = line.split('//')[0].strip()
    return line


def first_pass(path):
    symbol_table = dict(PREDEFINED_SYMBOLS)
    rom_address = 0
    with open(path) as f:
        for line in f:
            line = clean(line)
            if not line:
                continue
            if line.startswith('(') and line.endswith(')'):
                symbol_table[line[1:-1]] = rom_address
            else:
                rom_address += 1
    return symbol_table


def translate_a(value, symbol_table, next_var):
    if value.isdigit():
        addr = int(value)
    elif value in symbol_table:
        addr = symbol_table[value]
    else:
        symbol_table[value] = next_var[0]
        addr = next_var[0]
        next_var[0] += 1
    return f'0{addr:015b}'


def translate_c(line):
    dest = None
    jump = None
    if '=' in line:
        dest, line = line.split('=', 1)
    if ';' in line:
        line, jump = line.split(';', 1)
    comp = line
    return '111' + COMP_TABLE[comp] + DEST_TABLE[dest] + JUMP_TABLE[jump]


def assemble(path, out_path):
    symbol_table = first_pass(path)
    next_var = [16]
    count = 0
    with open(path) as fin, open(out_path, 'w') as fout:
        for line in fin:
            line = clean(line)
            if not line or (line.startswith('(') and line.endswith(')')):
                continue
            if line.startswith('@'):
                binary = translate_a(line[1:], symbol_table, next_var)
            else:
                binary = translate_c(line)
            fout.write(binary + '\n')
            count += 1
    return count


def main():
    if len(sys.argv) != 2:
        print(f'Usage: python {sys.argv[0]} <file.asm>')
        sys.exit(1)
    path = sys.argv[1]
    out_path = path.replace('.asm', '.hack')
    count = assemble(path, out_path)
    print(f'Wrote {count} instructions to {out_path}')


if __name__ == '__main__':
    main()
