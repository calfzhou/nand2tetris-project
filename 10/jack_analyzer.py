"""Jack Analyzer — Nand2Tetris Project 10

Tokenizes and parses Jack source code, outputting XML parse trees.

Implemented:
  - JackTokenizer: keywords, symbols, integerConstants, stringConstants, identifiers
  - CompilationEngine: recursive descent parser for the full Jack grammar
    (class, classVarDec, subroutineDec, parameterList, subroutineBody,
     varDec, statements, letStatement, ifStatement, whileStatement,
     doStatement, returnStatement, expression, term, expressionList)
  - XML output with proper indentation and entity escaping
  - Single file or directory input

Usage:
  python3 jack_analyzer.py <file.jack | directory>
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

SYMBOLS = set('{}()[].,;+-*/&|<>=~')

XML_ENTITIES = {'<': '&lt;', '>': '&gt;', '&': '&amp;'}

TOKEN_PATTERN = re.compile(
    r'(\d+)'
    r'|(".*?")'
    r'|([a-zA-Z_]\w*)'
    r'|([{}()\[\].,;+\-*/&|<>=~])'
)


class JackTokenizer:
    def __init__(self, text):
        text = re.sub(r'//.*?\n', '\n', text)
        text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
        self._tokens = []
        for m in TOKEN_PATTERN.finditer(text):
            if m.group(1) is not None:
                self._tokens.append(('integerConstant', int(m.group(1))))
            elif m.group(2) is not None:
                self._tokens.append(('stringConstant', m.group(2)[1:-1]))
            elif m.group(3) is not None:
                word = m.group(3)
                if word in KEYWORDS:
                    self._tokens.append(('keyword', word))
                else:
                    self._tokens.append(('identifier', word))
            elif m.group(4) is not None:
                self._tokens.append(('symbol', m.group(4)))
        self._pos = 0

    def has_more_tokens(self):
        return self._pos < len(self._tokens)

    def token_type(self):
        return self._tokens[self._pos][0]

    def token_value(self):
        return self._tokens[self._pos][1]

    def advance(self):
        self._pos += 1

    def peek(self):
        return self._tokens[self._pos][1]

    def peek_type(self):
        return self._tokens[self._pos][0]


def xml_val(token_type, value):
    s = str(value)
    s = s.replace('&', '&amp;')
    s = s.replace('<', '&lt;')
    s = s.replace('>', '&gt;')
    return f'<{token_type}> {s} </{token_type}>'


class CompilationEngine:
    def __init__(self, tokenizer, out):
        self._t = tokenizer
        self._out = out
        self._indent = 0

    def _write(self, s):
        self._out.write('  ' * self._indent + s + '\n')

    def _eat(self, expected=None):
        tt = self._t.token_type()
        val = self._t.token_value()
        if expected is not None and val != expected:
            raise SyntaxError(f'Expected {expected!r}, got {val!r}')
        self._write(xml_val(tt, val))
        self._t.advance()
        return val

    def _eat_type(self, expected_type):
        tt = self._t.token_type()
        val = self._t.token_value()
        if tt != expected_type:
            raise SyntaxError(f'Expected type {expected_type}, got {tt}')
        self._write(xml_val(tt, val))
        self._t.advance()
        return val

    def _open(self, tag):
        self._write(f'<{tag}>')
        self._indent += 1

    def _close(self, tag):
        self._indent -= 1
        self._write(f'</{tag}>')

    def compile_class(self):
        self._open('class')
        self._eat('class')
        self._eat_type('identifier')
        self._eat('{')
        while self._t.has_more_tokens() and self._t.peek() in ('static', 'field'):
            self.compile_class_var_dec()
        while self._t.has_more_tokens() and self._t.peek() in ('constructor', 'function', 'method'):
            self.compile_subroutine_dec()
        self._eat('}')
        self._close('class')

    def compile_class_var_dec(self):
        self._open('classVarDec')
        self._eat()  # static | field
        self._eat()  # type
        self._eat_type('identifier')
        while self._t.peek() == ',':
            self._eat(',')
            self._eat_type('identifier')
        self._eat(';')
        self._close('classVarDec')

    def compile_subroutine_dec(self):
        self._open('subroutineDec')
        self._eat()  # constructor | function | method
        self._eat()  # return type
        self._eat_type('identifier')
        self._eat('(')
        self.compile_parameter_list()
        self._eat(')')
        self.compile_subroutine_body()
        self._close('subroutineDec')

    def compile_parameter_list(self):
        self._open('parameterList')
        if self._t.peek() != ')':
            self._eat()  # type
            self._eat_type('identifier')
            while self._t.peek() == ',':
                self._eat(',')
                self._eat()  # type
                self._eat_type('identifier')
        self._close('parameterList')

    def compile_subroutine_body(self):
        self._open('subroutineBody')
        self._eat('{')
        while self._t.peek() == 'var':
            self.compile_var_dec()
        self.compile_statements()
        self._eat('}')
        self._close('subroutineBody')

    def compile_var_dec(self):
        self._open('varDec')
        self._eat('var')
        self._eat()  # type
        self._eat_type('identifier')
        while self._t.peek() == ',':
            self._eat(',')
            self._eat_type('identifier')
        self._eat(';')
        self._close('varDec')

    def compile_statements(self):
        self._open('statements')
        while self._t.peek() in ('let', 'if', 'while', 'do', 'return'):
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
        self._close('statements')

    def compile_let(self):
        self._open('letStatement')
        self._eat('let')
        self._eat_type('identifier')
        if self._t.peek() == '[':
            self._eat('[')
            self.compile_expression()
            self._eat(']')
        self._eat('=')
        self.compile_expression()
        self._eat(';')
        self._close('letStatement')

    def compile_if(self):
        self._open('ifStatement')
        self._eat('if')
        self._eat('(')
        self.compile_expression()
        self._eat(')')
        self._eat('{')
        self.compile_statements()
        self._eat('}')
        if self._t.has_more_tokens() and self._t.peek() == 'else':
            self._eat('else')
            self._eat('{')
            self.compile_statements()
            self._eat('}')
        self._close('ifStatement')

    def compile_while(self):
        self._open('whileStatement')
        self._eat('while')
        self._eat('(')
        self.compile_expression()
        self._eat(')')
        self._eat('{')
        self.compile_statements()
        self._eat('}')
        self._close('whileStatement')

    def compile_do(self):
        self._open('doStatement')
        self._eat('do')
        self._eat_type('identifier')
        if self._t.peek() == '.':
            self._eat('.')
            self._eat_type('identifier')
        self._eat('(')
        self.compile_expression_list()
        self._eat(')')
        self._eat(';')
        self._close('doStatement')

    def compile_return(self):
        self._open('returnStatement')
        self._eat('return')
        if self._t.peek() != ';':
            self.compile_expression()
        self._eat(';')
        self._close('returnStatement')

    def compile_expression(self):
        self._open('expression')
        self.compile_term()
        while self._t.has_more_tokens() and self._t.peek() in ('+', '-', '*', '/', '&', '|', '<', '>', '='):
            self._eat()
            self.compile_term()
        self._close('expression')

    def compile_term(self):
        self._open('term')
        tt = self._t.peek_type()
        val = self._t.peek()
        if tt == 'integerConstant':
            self._eat()
        elif tt == 'stringConstant':
            self._eat()
        elif val in ('true', 'false', 'null', 'this'):
            self._eat()
        elif val == '(':
            self._eat('(')
            self.compile_expression()
            self._eat(')')
        elif val in ('-', '~'):
            self._eat()
            self.compile_term()
        elif tt == 'identifier':
            self._eat_type('identifier')
            if self._t.has_more_tokens() and self._t.peek() == '[':
                self._eat('[')
                self.compile_expression()
                self._eat(']')
            elif self._t.has_more_tokens() and self._t.peek() == '(':
                self._eat('(')
                self.compile_expression_list()
                self._eat(')')
            elif self._t.has_more_tokens() and self._t.peek() == '.':
                self._eat('.')
                self._eat_type('identifier')
                self._eat('(')
                self.compile_expression_list()
                self._eat(')')
        self._close('term')

    def compile_expression_list(self):
        self._open('expressionList')
        if self._t.has_more_tokens() and self._t.peek() != ')':
            self.compile_expression()
            while self._t.peek() == ',':
                self._eat(',')
                self.compile_expression()
        self._close('expressionList')


def analyze_file(path):
    with open(path) as f:
        text = f.read()
    tokenizer = JackTokenizer(text)
    out_path = path.replace('.jack', '.xml')
    with open(out_path, 'w') as fout:
        engine = CompilationEngine(tokenizer, fout)
        engine.compile_class()
    print(f'Wrote {out_path}')


def main():
    if len(sys.argv) != 2:
        print(f'Usage: python3 {sys.argv[0]} <file.jack | directory>')
        sys.exit(1)
    path = sys.argv[1]
    if os.path.isdir(path):
        for jack_file in sorted(glob.glob(os.path.join(path, '*.jack'))):
            analyze_file(jack_file)
    else:
        analyze_file(path)


if __name__ == '__main__':
    main()
