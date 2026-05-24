"""VM Translator — Nand2Tetris Project 8

Translates Hack VM code (.vm) into Hack assembly (.asm).

Implemented:
  - Arithmetic/logical commands: add, sub, neg, eq, gt, lt, and, or, not
  - Memory access: push/pop for constant, local, argument, this, that,
    temp, pointer, static segments
  - Branching commands: label, goto, if-goto
  - Function commands: function, call, return
  - Bootstrap code: SP=256, call Sys.init
  - Folder input: translates all .vm files in a directory into one .asm
  - Streaming I/O

Usage:
  python3 vm_translator.py <file.vm>        → outputs <file.asm>
  python3 vm_translator.py <directory>      → outputs <directory>/<dirname>.asm
"""

import sys
import os
import glob

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
        self._current_function = ''

    def set_filename(self, filename):
        self._filename = filename

    def _emit(self, *lines):
        for line in lines:
            self._out.write(line + '\n')

    def _comment(self, text):
        self._out.write(f'// {text}\n')

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

    def write_label(self, label):
        self._emit(f'({self._current_function}${label})')

    def write_goto(self, label):
        self._emit(f'@{self._current_function}${label}', '0;JMP')

    def write_if_goto(self, label):
        self._pop_to_d()
        self._emit(f'@{self._current_function}${label}', 'D;JNE')

    def write_function(self, name, n_vars):
        self._current_function = name
        self._emit(f'({name})')
        for _ in range(n_vars):
            self._emit('D=0')
            self._push_d()

    def write_call(self, name, n_args):
        return_label = self._unique_label()
        # push return address
        self._emit(f'@{return_label}', 'D=A')
        self._push_d()
        # push LCL, ARG, THIS, THAT
        for seg in ('LCL', 'ARG', 'THIS', 'THAT'):
            self._emit(f'@{seg}', 'D=M')
            self._push_d()
        # ARG = SP - 5 - nArgs
        self._emit('@SP', 'D=M', f'@{5 + n_args}', 'D=D-A', '@ARG', 'M=D')
        # LCL = SP
        self._emit('@SP', 'D=M', '@LCL', 'M=D')
        # goto function
        self._emit(f'@{name}', '0;JMP')
        # return label
        self._emit(f'({return_label})')

    def write_return(self):
        # endFrame (R14) = LCL
        self._emit('@LCL', 'D=M', '@R14', 'M=D')
        # retAddr (R15) = *(endFrame - 5)
        self._emit('@5', 'A=D-A', 'D=M', '@R15', 'M=D')
        # *ARG = pop()
        self._pop_to_d()
        self._emit('@ARG', 'A=M', 'M=D')
        # SP = ARG + 1
        self._emit('@ARG', 'D=M+1', '@SP', 'M=D')
        # restore THAT, THIS, ARG, LCL from endFrame
        for i, seg in enumerate(('THAT', 'THIS', 'ARG', 'LCL'), 1):
            self._emit('@R14', 'D=M', f'@{i}', 'A=D-A', 'D=M', f'@{seg}', 'M=D')
        # goto retAddr
        self._emit('@R15', 'A=M', '0;JMP')

    def write_bootstrap(self):
        self._comment('bootstrap')
        self._emit('@256', 'D=A', '@SP', 'M=D')
        self._comment('call Sys.init 0')
        self.write_call('Sys.init', 0)


def translate_file(path, writer):
    filename = os.path.splitext(os.path.basename(path))[0]
    writer.set_filename(filename)
    with open(path) as fin:
        for line in fin:
            line = line.split('//')[0].strip()
            if not line:
                continue
            parts = line.split()
            writer._comment(line)
            cmd = parts[0]
            if cmd in ('add', 'sub', 'neg', 'eq', 'gt', 'lt', 'and', 'or', 'not'):
                writer.write_arithmetic(cmd)
            elif cmd == 'push':
                writer.write_push(parts[1], int(parts[2]))
            elif cmd == 'pop':
                writer.write_pop(parts[1], int(parts[2]))
            elif cmd == 'label':
                writer.write_label(parts[1])
            elif cmd == 'goto':
                writer.write_goto(parts[1])
            elif cmd == 'if-goto':
                writer.write_if_goto(parts[1])
            elif cmd == 'function':
                writer.write_function(parts[1], int(parts[2]))
            elif cmd == 'call':
                writer.write_call(parts[1], int(parts[2]))
            elif cmd == 'return':
                writer.write_return()


def main():
    if len(sys.argv) != 2:
        print(f'Usage: python3 {sys.argv[0]} <file.vm | directory>')
        sys.exit(1)

    path = sys.argv[1]

    if os.path.isdir(path):
        dirname = os.path.basename(os.path.normpath(path))
        out_path = os.path.join(path, f'{dirname}.asm')
        vm_files = sorted(glob.glob(os.path.join(path, '*.vm')))
        with open(out_path, 'w') as fout:
            writer = CodeWriter(fout)
            writer.write_bootstrap()
            for vm_file in vm_files:
                translate_file(vm_file, writer)
    else:
        out_path = path.replace('.vm', '.asm')
        with open(out_path, 'w') as fout:
            writer = CodeWriter(fout)
            translate_file(path, writer)

    print(f'Wrote {out_path}')


if __name__ == '__main__':
    main()
