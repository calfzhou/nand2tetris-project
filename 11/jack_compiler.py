"""Jack Compiler — Nand2Tetris Project 11

Compiles Jack source code (.jack) into Hack VM code (.vm).

Implemented:
  - JackTokenizer: tokenizes keywords, symbols, integers, strings, identifiers
  - SymbolTable: class-level (static, this/field) and subroutine-level (argument, local) scopes
  - VMWriter: emits VM commands (push, pop, arithmetic, label, goto, function, call, return)
  - CompilationEngine: recursive descent parser + code generator for the full Jack grammar
  - Object support: constructors (Memory.alloc), methods (this = argument 0), fields
  - String literals via String.new + appendChar
  - Arrays via Memory deref (pointer 1 = THAT)
  - Single file or directory input

Usage:
  python3 jack_compiler.py <file.jack | directory>
"""

import sys
import os
import re
import glob

KEYWORDS = {
    'class', 'constructor', 'function', 'method', 'field', 'static',
    'var', 'int', 'char', 'boolean', 'void', 'true', 'false', 'null',
    'this', 'let', 'do', 'if', 'else', 'while', 'return',
}

TOKEN_PATTERN = re.compile(
    r'(\d+)'
    r'|("[^"]*")'
    r'|([a-zA-Z_]\w*)'
    r'|([{}()\[\].,;+\-*/&|<>=~])'
)

OP_VM = {
    '+': 'add', '-': 'sub', '&': 'and', '|': 'or',
    '<': 'lt', '>': 'gt', '=': 'eq',
}

KIND_SEGMENT = {
    'static': 'static',
    'field': 'this',
    'arg': 'argument',
    'var': 'local',
}


class JackTokenizer:
    def __init__(self, text):
        # Replace comments with spaces (preserving offsets) so token spans align with original text.
        def blank(m):
            return re.sub(r'[^\n]', ' ', m.group(0))
        text = re.sub(r'//[^\n]*', blank, text)
        text = re.sub(r'/\*.*?\*/', blank, text, flags=re.DOTALL)
        self._source = text
        self._tokens = []
        self._spans = []
        for m in TOKEN_PATTERN.finditer(text):
            if m.group(1) is not None:
                self._tokens.append(('integerConstant', int(m.group(1))))
            elif m.group(2) is not None:
                self._tokens.append(('stringConstant', m.group(2)[1:-1]))
            elif m.group(3) is not None:
                word = m.group(3)
                self._tokens.append(('keyword' if word in KEYWORDS else 'identifier', word))
            elif m.group(4) is not None:
                self._tokens.append(('symbol', m.group(4)))
            self._spans.append((m.start(), m.end()))
        self._pos = 0

    def has_more(self):
        return self._pos < len(self._tokens)

    def peek(self):
        return self._tokens[self._pos][1]

    def peek_type(self):
        return self._tokens[self._pos][0]

    def peek_ahead(self, n=1):
        idx = self._pos + n
        return self._tokens[idx][1] if idx < len(self._tokens) else None

    def advance(self):
        tok = self._tokens[self._pos]
        self._pos += 1
        return tok

    def pos(self):
        return self._pos

    def source_text(self, start_idx, end_idx):
        """Return original source text spanning tokens [start_idx, end_idx)."""
        if start_idx >= end_idx or end_idx > len(self._spans):
            return ''
        s = self._spans[start_idx][0]
        e = self._spans[end_idx - 1][1]
        return ' '.join(self._source[s:e].split())

    def find_matching(self, open_idx, open_sym, close_sym):
        """Given idx of an open symbol, find idx of matching close. Returns close idx."""
        depth = 0
        for i in range(open_idx, len(self._tokens)):
            tt, v = self._tokens[i]
            if tt == 'symbol' and v == open_sym:
                depth += 1
            elif tt == 'symbol' and v == close_sym:
                depth -= 1
                if depth == 0:
                    return i
        return -1

    def find_token(self, start_idx, value):
        for i in range(start_idx, len(self._tokens)):
            if self._tokens[i][1] == value:
                return i
        return -1


class SymbolTable:
    def __init__(self):
        self._class = {}     # name -> (type, kind, index)
        self._sub = {}
        self._counts = {'static': 0, 'field': 0, 'arg': 0, 'var': 0}

    def start_subroutine(self):
        self._sub = {}
        self._counts['arg'] = 0
        self._counts['var'] = 0

    def define(self, name, type_, kind):
        index = self._counts[kind]
        self._counts[kind] += 1
        if kind in ('static', 'field'):
            self._class[name] = (type_, kind, index)
        else:
            self._sub[name] = (type_, kind, index)

    def var_count(self, kind):
        return self._counts[kind]

    def lookup(self, name):
        if name in self._sub:
            return self._sub[name]
        if name in self._class:
            return self._class[name]
        return None


class VMWriter:
    def __init__(self, out):
        self._out = out

    def write(self, s):
        # Indent everything except `function` and `label` lines.
        if s.startswith('function ') or s.startswith('label '):
            self._out.write(s + '\n')
        else:
            self._out.write('    ' + s + '\n')

    def comment(self, text):
        self._out.write(f'    // {text}\n')

    def push(self, segment, index):
        self.write(f'push {segment} {index}')

    def pop(self, segment, index):
        self.write(f'pop {segment} {index}')

    def arithmetic(self, command):
        self.write(command)

    def label(self, name):
        self.write(f'label {name}')

    def goto(self, name):
        self.write(f'goto {name}')

    def if_goto(self, name):
        self.write(f'if-goto {name}')

    def call(self, name, n_args):
        self.write(f'call {name} {n_args}')

    def function(self, name, n_locals):
        self.write(f'function {name} {n_locals}')

    def ret(self):
        self.write('return')


class CompilationEngine:
    def __init__(self, tokenizer, vm):
        self._t = tokenizer
        self._vm = vm
        self._st = SymbolTable()
        self._class_name = ''
        self._label_count = 0

    def _eat(self, expected=None):
        tt, val = self._t.advance()
        if expected is not None and val != expected:
            raise SyntaxError(f'Expected {expected!r}, got {val!r}')
        return val

    def _unique_label(self, prefix):
        label = f'{self._class_name}.{prefix}{self._label_count}'
        self._label_count += 1
        return label

    def _push_var(self, name):
        info = self._st.lookup(name)
        if info is None:
            raise SyntaxError(f'Undefined variable: {name}')
        _, kind, idx = info
        self._vm.push(KIND_SEGMENT[kind], idx)

    def _pop_var(self, name):
        info = self._st.lookup(name)
        if info is None:
            raise SyntaxError(f'Undefined variable: {name}')
        _, kind, idx = info
        self._vm.pop(KIND_SEGMENT[kind], idx)

    def compile_class(self):
        self._eat('class')
        self._class_name = self._eat()
        self._eat('{')
        while self._t.peek() in ('static', 'field'):
            self.compile_class_var_dec()
        while self._t.peek() in ('constructor', 'function', 'method'):
            self.compile_subroutine_dec()
        self._eat('}')

    def compile_class_var_dec(self):
        kind = self._eat()  # static | field
        type_ = self._eat()
        name = self._eat()
        self._st.define(name, type_, kind)
        while self._t.peek() == ',':
            self._eat(',')
            name = self._eat()
            self._st.define(name, type_, kind)
        self._eat(';')

    def compile_subroutine_dec(self):
        self._st.start_subroutine()
        start = self._t.pos()
        # find ')' of the parameter list for the comment
        paren_open = self._t.find_token(start, '(')
        paren_close = self._t.find_matching(paren_open, '(', ')') if paren_open >= 0 else -1
        if paren_close >= 0:
            self._vm.comment(self._t.source_text(start, paren_close + 1))
        sub_kind = self._eat()  # constructor | function | method
        self._eat()  # return type
        sub_name = self._eat()
        if sub_kind == 'method':
            self._st.define('this', self._class_name, 'arg')
        self._eat('(')
        self.compile_parameter_list()
        self._eat(')')
        self._eat('{')
        while self._t.peek() == 'var':
            self.compile_var_dec()
        n_locals = self._st.var_count('var')
        self._vm.function(f'{self._class_name}.{sub_name}', n_locals)
        if sub_kind == 'constructor':
            n_fields = self._st.var_count('field')
            self._vm.push('constant', n_fields)
            self._vm.call('Memory.alloc', 1)
            self._vm.pop('pointer', 0)
        elif sub_kind == 'method':
            self._vm.push('argument', 0)
            self._vm.pop('pointer', 0)
        self.compile_statements()
        self._eat('}')

    def compile_parameter_list(self):
        if self._t.peek() != ')':
            type_ = self._eat()
            name = self._eat()
            self._st.define(name, type_, 'arg')
            while self._t.peek() == ',':
                self._eat(',')
                type_ = self._eat()
                name = self._eat()
                self._st.define(name, type_, 'arg')

    def compile_var_dec(self):
        self._eat('var')
        type_ = self._eat()
        name = self._eat()
        self._st.define(name, type_, 'var')
        while self._t.peek() == ',':
            self._eat(',')
            name = self._eat()
            self._st.define(name, type_, 'var')
        self._eat(';')

    def _emit_statement_comment(self):
        """Emit the upcoming statement (header only for if/while) as a // comment."""
        t = self._t
        start = t.pos()
        kw = t.peek()
        if kw == 'let' or kw == 'do' or kw == 'return':
            # find next ';' at depth 0
            end = t.find_token(start, ';')
            if end >= 0:
                self._vm.comment(t.source_text(start, end + 1))
        elif kw == 'if' or kw == 'while':
            # find matching ')' after '('
            paren_idx = t.find_token(start, '(')
            if paren_idx >= 0:
                close = t.find_matching(paren_idx, '(', ')')
                if close >= 0:
                    self._vm.comment(t.source_text(start, close + 1))

    def compile_statements(self):
        while self._t.peek() in ('let', 'if', 'while', 'do', 'return'):
            self._emit_statement_comment()
            p = self._t.peek()
            if p == 'let':
                self.compile_let()
            elif p == 'if':
                self.compile_if()
            elif p == 'while':
                self.compile_while()
            elif p == 'do':
                self.compile_do()
            elif p == 'return':
                self.compile_return()

    def compile_let(self):
        self._eat('let')
        name = self._eat()
        is_array = self._t.peek() == '['
        if is_array:
            self._eat('[')
            self.compile_expression()
            self._eat(']')
            self._push_var(name)
            self._vm.arithmetic('add')  # arr base + index on stack
            self._eat('=')
            self.compile_expression()
            self._vm.pop('temp', 0)
            self._vm.pop('pointer', 1)
            self._vm.push('temp', 0)
            self._vm.pop('that', 0)
        else:
            self._eat('=')
            self.compile_expression()
            self._pop_var(name)
        self._eat(';')

    def compile_if(self):
        self._eat('if')
        self._eat('(')
        self.compile_expression()
        self._eat(')')
        label_else = self._unique_label('IF_ELSE_')
        label_end = self._unique_label('IF_END_')
        self._vm.arithmetic('not')
        self._vm.if_goto(label_else)
        self._eat('{')
        self.compile_statements()
        self._eat('}')
        self._vm.goto(label_end)
        self._vm.label(label_else)
        if self._t.has_more() and self._t.peek() == 'else':
            self._eat('else')
            self._eat('{')
            self.compile_statements()
            self._eat('}')
        self._vm.label(label_end)

    def compile_while(self):
        label_start = self._unique_label('WHILE_START_')
        label_end = self._unique_label('WHILE_END_')
        self._vm.label(label_start)
        self._eat('while')
        self._eat('(')
        self.compile_expression()
        self._eat(')')
        self._vm.arithmetic('not')
        self._vm.if_goto(label_end)
        self._eat('{')
        self.compile_statements()
        self._eat('}')
        self._vm.goto(label_start)
        self._vm.label(label_end)

    def compile_do(self):
        self._eat('do')
        name = self._eat()
        self._compile_subroutine_call(name)
        self._vm.pop('temp', 0)
        self._eat(';')

    def compile_return(self):
        self._eat('return')
        if self._t.peek() != ';':
            self.compile_expression()
        else:
            self._vm.push('constant', 0)
        self._vm.ret()
        self._eat(';')

    def compile_expression(self):
        self.compile_term()
        while self._t.has_more() and self._t.peek() in ('+', '-', '*', '/', '&', '|', '<', '>', '='):
            op = self._eat()
            self.compile_term()
            if op == '*':
                self._vm.call('Math.multiply', 2)
            elif op == '/':
                self._vm.call('Math.divide', 2)
            else:
                self._vm.arithmetic(OP_VM[op])

    def compile_term(self):
        tt = self._t.peek_type()
        val = self._t.peek()
        if tt == 'integerConstant':
            self._eat()
            self._vm.push('constant', val)
        elif tt == 'stringConstant':
            self._eat()
            self._vm.push('constant', len(val))
            self._vm.call('String.new', 1)
            for ch in val:
                self._vm.push('constant', ord(ch))
                self._vm.call('String.appendChar', 2)
        elif val == 'true':
            self._eat()
            self._vm.push('constant', 1)
            self._vm.arithmetic('neg')
        elif val in ('false', 'null'):
            self._eat()
            self._vm.push('constant', 0)
        elif val == 'this':
            self._eat()
            self._vm.push('pointer', 0)
        elif val == '(':
            self._eat('(')
            self.compile_expression()
            self._eat(')')
        elif val in ('-', '~'):
            op = self._eat()
            self.compile_term()
            self._vm.arithmetic('neg' if op == '-' else 'not')
        elif tt == 'identifier':
            name = self._eat()
            nxt = self._t.peek() if self._t.has_more() else None
            if nxt == '[':
                self._eat('[')
                self.compile_expression()
                self._eat(']')
                self._push_var(name)
                self._vm.arithmetic('add')
                self._vm.pop('pointer', 1)
                self._vm.push('that', 0)
            elif nxt in ('(', '.'):
                self._compile_subroutine_call(name)
            else:
                self._push_var(name)

    def _compile_subroutine_call(self, first_name):
        # first_name is already eaten. Could be: foo(...), Class.foo(...), var.foo(...)
        if self._t.peek() == '(':
            # method call on this
            self._vm.push('pointer', 0)
            self._eat('(')
            n_args = self.compile_expression_list() + 1
            self._eat(')')
            self._vm.call(f'{self._class_name}.{first_name}', n_args)
        else:
            self._eat('.')
            sub_name = self._eat()
            self._eat('(')
            info = self._st.lookup(first_name)
            if info is not None:
                # method call on variable
                type_, kind, idx = info
                self._vm.push(KIND_SEGMENT[kind], idx)
                n_args = self.compile_expression_list() + 1
                target = f'{type_}.{sub_name}'
            else:
                # function/constructor call on class
                n_args = self.compile_expression_list()
                target = f'{first_name}.{sub_name}'
            self._eat(')')
            self._vm.call(target, n_args)

    def compile_expression_list(self):
        n = 0
        if self._t.peek() != ')':
            self.compile_expression()
            n += 1
            while self._t.peek() == ',':
                self._eat(',')
                self.compile_expression()
                n += 1
        return n


def compile_file(path):
    with open(path) as f:
        text = f.read()
    tokenizer = JackTokenizer(text)
    out_path = path.replace('.jack', '.vm')
    with open(out_path, 'w') as fout:
        vm = VMWriter(fout)
        engine = CompilationEngine(tokenizer, vm)
        engine.compile_class()
    print(f'Wrote {out_path}')


def main():
    if len(sys.argv) != 2:
        print(f'Usage: python3 {sys.argv[0]} <file.jack | directory>')
        sys.exit(1)
    path = sys.argv[1]
    if os.path.isdir(path):
        for jack_file in sorted(glob.glob(os.path.join(path, '*.jack'))):
            compile_file(jack_file)
    else:
        compile_file(path)


if __name__ == '__main__':
    main()
