#!/usr/bin/env python
# -*- coding: utf-8 -*-
import collections
import pprint
import sys

from ply import lex


class ParserError(Exception):
    def __init__(self, fn, token, text):
        msg = 'File %s, line %i - %s'
        msg = msg % (fn, token.lineno, text)
        super(ParserError, self).__init__(msg)


tokens = [
    'SEP',
    'AT',
    'COMMA',
    'DREG',
    'IREG',
    'ADDR',
    'LABEL',
    'IDENT',
    'CONST',
    'OP00',
    'OP01',
    'OP11',
    'OP21',
]

# Label: set identifier to current address
def t_LABEL(t):
    r'[a-zA-Z0-9_]+:'
    t.value = t.value.strip(':')
    return t

# Operation with no args, no dest
def t_OP00(t):
    r'noop|halt'
    return t

# Operation with 1 arg, no dest
def t_OP01(t):
    r'one|zero|inc|dec|jmp(n|nc|z|nz|pos|neg)?'
    return t

# Operation with 1 arg, dest
def t_OP11(t):
    r'not|load|store'
    return t

# Operation with 2 args, dest
def t_OP21(t):
    r'addc?|subb?|and|or'
    return t

# Direct register addressing
def t_DREG(t):
    r'A|X|D|SP'
    return t

# Indirect register addressing
def t_IREG(t):
    r'\*A|\*X|\*SP'
    t.value = t.value.strip('*')
    return t

# Immediate addressing
def t_ADDR(t):
    r'&(0x[0-9a-fA-F])|([0-9]+)'
    t.value = t.value.strip('&')
    return t

# Numerical constant: store in mem, replace with address
def t_CONST(t):
    r'\#(0x[0-9a-fA-F])|([0-9]+)'
    return t

# Identifier: replace with immediate address
def t_IDENT(t):
    r'[a-zA-Z0-9_]+'
    return t

def t_AT(t):
    r'@'
    return t

def t_COMMA(t):
    r','
    return t

# Separation between instructions
def t_SEP(t):
    r'\n|;+'
    if t.value == '\n':
        t.lexer.lineno += 1
    return t

t_ignore_whitespace = r'\s+'
t_ignore_comment = r'//[^\n]*'

def t_error(t):
    raise ParserError(filename, t, 'Invalid syntax near "%s"' % t.value)


labels = {}
constants = {}
mc = 1  # memory counter

SRC_TYPES = ('ADDR', 'IREG', 'DREG', 'IDENT', 'CONST')
DEST_TYPES = ('ADDR', 'IREG', 'DREG', 'IDENT')


Statement = collections.namedtuple(
    'Statement', ('op', 'arg1', 'arg2', 'dest'))


def parse(tokens):
    """
    Splits a stream of tokens into a stream of statements.
    """
    global mc
    stmt_toks = []
    for tok in tokens:
        if tok.type == 'SEP':
            if stmt_toks:
                stmt = parse_statement(stmt_toks)
                if stmt:
                    mc += 1
                    yield parse_statement(stmt_toks)
            stmt_toks = []
        else:
            stmt_toks.append(tok)


def parse_statement(toks):
    """
    Parses and type-checks a group of tokens representing a
    single statement.
    """
    if toks and toks[0].type == 'LABEL':
        labels[toks[0].value] = mc
        toks = toks[1:]
    if not toks:
        return False
    if toks[0].type == 'OP00':
        return parse_op00(toks)
    elif toks[0].type == 'OP01':
        return parse_op01(toks)
    elif toks[0].type == 'OP11':
        return parse_op11(toks)
    elif toks[0].type == 'OP21':
        return parse_op21(toks)
    else:
        msg = 'Expected an operation keyword, got "%s"' % toks[0].value
        raise ParserError(filename, toks[0], msg)


def parse_op00(toks):
    if len(toks) != 1:
        msg = 'Wrong number of arguments for op "%s"' % toks[0].value
        raise ParserError(filename, toks[0], msg)
    op = toks[0]
    arg1 = arg2 = dest = None
    return Statement(op, arg1, arg2, dest)


def parse_op01(toks):
    if len(toks) != 2:
        msg = 'Wrong number of arguments for op "%s"' % toks[0].value
        raise ParserError(filename, toks[0], msg)
    if not (toks[1].type in SRC_TYPES and toks[1].type in DEST_TYPES):
        msg = 'Invalid type, 1st arg to op "%s"' % toks[0].value
        raise ParserError(filename, toks[1], msg)
    op, dest = toks
    arg1 = dest
    arg2 = None
    return Statement(op, arg1, arg2, dest)


def parse_op11(toks):
    if len(toks) != 4:
        msg = 'Wrong number of arguments for op "%s"' % toks[0].value
        raise ParserError(filename, toks[0], msg)
    if toks[1].type not in SRC_TYPES:
        msg = 'Invalid type, 1st arg to op "%s"' % toks[0].value
        raise ParserError(filename, toks[1], msg)
    if toks[2].type != 'AT':
        msg = 'Expected a destination (@), got: "%s"' % toks[2].value
        raise ParserError(filename, toks[2], msg)
    if toks[3].type not in DEST_TYPES:
        msg = 'Invalid type, 2nd arg to op "%s"' % toks[0].value
        raise ParserError(filename, toks[3], msg)
    op, arg1, at, dest = toks
    arg2 = None
    return Statement(op, arg1, arg2, dest)


def parse_op21(toks):
    if len(toks) != 6:
        msg = 'Wrong number of arguments for op "%s"' % toks[0].value
        raise ParserError(filename, toks[0], msg)
    if toks[1].type not in SRC_TYPES:
        msg = 'Invalid type, 1st arg to op "%s"' % toks[0].value
        raise ParserError(filename, toks[1], msg)
    if toks[2].type != 'COMMA':
        msg = 'Expected a comma, got: "%s"' % toks[2].value
        raise ParserError(filename, toks[2], msg)
    if toks[3].type not in SRC_TYPES:
        msg = 'Invalid type, 2nd arg to op "%s"' % toks[0].value
        raise ParserError(filename, toks[3], msg)
    if toks[4].type != 'AT':
        msg = 'Expected a destination (@), got: "%s"' % toks[4].value
        raise ParserError(filename, toks[4], msg)
    if toks[5].type not in DEST_TYPES:
        msg = 'Invalid type, 3rd arg to op "%s"' % toks[0].value
        raise ParserError(filename, toks[5], msg)
    op, arg1, comma, arg2, at, dest = toks
    return Statement(op, arg1, arg2, dest)


def assemble(statements):
    """
    Assemble stream of statements into machine code instructions.
    """
    for st in statements:
        yield st


def allocate_constants():
    pass


def substitute_labels(instructions):
    for ins in instructions:
        yield ins


def write(instructions, fp):
    """
    Write instructions to file.
    """
    for ins in instructions:
        fp.write(pprint.pformat(ins) + '\n')


def main(fp_in, fp_out):
    lex.lex()
    lex.input(fp_in.read())
    tokens = iter(lex.token, None)
    statements = parse(tokens)
    partial_instructions = assemble(statements)
    allocate_constants()
    instructions = substitute_labels(partial_instructions)
    write(instructions, fp_out)


if __name__ == '__main__':
    global filename
    filename = sys.argv[1]
    with open(sys.argv[1], 'r') as fp_in:
        if len(sys.argv) > 2:
            with open(sys.argv[2], 'w') as fp_out:
                main(fp_in, fp_out)
        else:
            main(fp_in, sys.stdout)
