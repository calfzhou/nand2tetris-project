"""VM Translator — Nand2Tetris Project 7

Translates Hack VM code (.vm) into Hack assembly (.asm).

Implemented:
  - Arithmetic/logical commands: add, sub, neg, eq, gt, lt, and, or, not
  - Memory access: push/pop for constant, local, argument, this, that,
    temp, pointer, static segments
  - Streaming I/O: reads .vm line-by-line, writes .asm line-by-line

Usage:
  python3 vm_translator.py <file.vm>
  → outputs <file.asm> in the same directory
"""

import sys
import os

SEGMENT_MAP = {
    'local': 'LCL',
    'argument': 'ARG',
    'this': 'THIS',
    'that': 'THAT',
}


class CodeWriter:
    def __init__(self, out):
        self._out = out
        self._label_count = 0
        self._filename = ''

    def set_filename(self, filename):
        self._filename = filename

    def _emit(self, *lines):
        for line in lines:
            self._out.write(line + '\n')

    def _unique_label(self):
        label = f'_L{self._label_count}'
        self._label_count += 1
        return label

    def _push_d(self):
        self._emit('@SP', 'A=M', 'M=D', '@SP', 'M=M+1')

    def _pop_to_d(self):
        self._emit('@SP', 'AM=M-1', 'D=M')

    def write_arithmetic(self, command):
        if command in ('add', 'sub', 'and', 'or'):
            op = {'add': 'D+M', 'sub': 'M-D', 'and': 'D&M', 'or': 'D|M'}[command]
            self._pop_to_d()
            self._emit('@SP', 'A=M-1', f'M={op}')
        elif command == 'neg':
            self._emit('@SP', 'A=M-1', 'M=-M')
        elif command == 'not':
            self._emit('@SP', 'A=M-1', 'M=!M')
        elif command in ('eq', 'gt', 'lt'):
            jump = {'eq': 'JEQ', 'gt': 'JGT', 'lt': 'JLT'}[command]
            label_true = self._unique_label()
            label_end = self._unique_label()
            self._pop_to_d()
            self._emit(
                '@SP', 'A=M-1', 'D=M-D',
                f'@{label_true}', f'D;{jump}',
                '@SP', 'A=M-1', 'M=0',
                f'@{label_end}', '0;JMP',
                f'({label_true})',
                '@SP', 'A=M-1', 'M=-1',
                f'({label_end})',
            )

    def write_push(self, segment, index):
        if segment == 'constant':
            self._emit(f'@{index}', 'D=A')
            self._push_d()
        elif segment in SEGMENT_MAP:
            self._emit(f'@{SEGMENT_MAP[segment]}', 'D=M', f'@{index}', 'A=D+A', 'D=M')
            self._push_d()
        elif segment == 'temp':
            self._emit(f'@{5 + index}', 'D=M')
            self._push_d()
        elif segment == 'pointer':
            symbol = 'THIS' if index == 0 else 'THAT'
            self._emit(f'@{symbol}', 'D=M')
            self._push_d()
        elif segment == 'static':
            self._emit(f'@{self._filename}.{index}', 'D=M')
            self._push_d()

    def write_pop(self, segment, index):
        if segment in SEGMENT_MAP:
            self._emit(f'@{SEGMENT_MAP[segment]}', 'D=M', f'@{index}', 'D=D+A', '@R13', 'M=D')
            self._pop_to_d()
            self._emit('@R13', 'A=M', 'M=D')
        elif segment == 'temp':
            self._pop_to_d()
            self._emit(f'@{5 + index}', 'M=D')
        elif segment == 'pointer':
            symbol = 'THIS' if index == 0 else 'THAT'
            self._pop_to_d()
            self._emit(f'@{symbol}', 'M=D')
        elif segment == 'static':
            self._pop_to_d()
            self._emit(f'@{self._filename}.{index}', 'M=D')


def translate(path):
    filename = os.path.splitext(os.path.basename(path))[0]
    out_path = path.replace('.vm', '.asm')
    with open(path) as fin, open(out_path, 'w') as fout:
        writer = CodeWriter(fout)
        writer.set_filename(filename)
        for line in fin:
            line = line.split('//')[0].strip()
            if not line:
                continue
            parts = line.split()
            fout.write(f'// {line}\n')
            if parts[0] in ('add', 'sub', 'neg', 'eq', 'gt', 'lt', 'and', 'or', 'not'):
                writer.write_arithmetic(parts[0])
            elif parts[0] == 'push':
                writer.write_push(parts[1], int(parts[2]))
            elif parts[0] == 'pop':
                writer.write_pop(parts[1], int(parts[2]))
    print(f'Wrote {out_path}')


def main():
    if len(sys.argv) != 2:
        print(f'Usage: python3 {sys.argv[0]} <file.vm>')
        sys.exit(1)
    translate(sys.argv[1])


if __name__ == '__main__':
    main()
