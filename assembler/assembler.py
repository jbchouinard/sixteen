#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function
from collections import namedtuple
import itertools
import sys

from ply import lex

import codes


tokens = [
    'SEP', 'AT', 'COMMA',               # Delimiters
    'DREG', 'IREG',                     # Direct/Indirect Addressing
    'ADDR', 'LABEL', 'IDENT', 'CONST',  # Immediate Addressing
    'OP00', 'OP10', 'OP11', 'OP21',     # Operations
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
def t_OP10(t):
    r'one|zero|inc|dec|jmp(nc|z|nz|pos|neg)?'
    return t

# Operation with 1 arg, dest
def t_OP11(t):
    r'not|load|store|copy'
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
    r'&((0x[0-9a-fA-F])|([0-9]+))'
    num = t.value.strip('&')
    base = 16 if num.startswith('0x') else 10
    t.value = int(num, base)
    return t

# Numerical constant: store in mem, replace with address
def t_CONST(t):
    r'(0x[0-9a-fA-F])|([0-9]+)'
    base = 16 if t.value.startswith('0x') else 10
    t.value = int(t.value, base)
    return t

# Identifier: replace with immediate address
def t_IDENT(t):
    r'[a-zA-Z][a-zA-Z0-9_]+'
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
    parser_error(filename, t, 'Invalid syntax near "%s"' % t.value)


labels = {}
constants = []
mc = 0  # memory counter

SRC_TYPES = ('ADDR', 'IREG', 'DREG', 'IDENT', 'CONST')
DEST_TYPES = ('ADDR', 'IREG', 'DREG', 'IDENT')


Statement = namedtuple('Statement', ('op', 'arg1', 'arg2', 'dest'))
Instruction = namedtuple('Instruction', ('ins', 'addr'))


def parse(tokens):
    """
    Parse a stream of tokens into a stream of statements.
    """
    global debug, mc
    stmt_toks = []
    for tok in tokens:
        if tok.type == 'SEP':
            if stmt_toks:
                stmt = parse_statement(stmt_toks)
                if stmt:
                    if debug:
                        print(stmt)
                    mc += 2
                    yield stmt
            stmt_toks = []
        else:
            stmt_toks.append(tok)


def check_type(token, types):
    if not isinstance(types, list) and not isinstance(types, tuple):
        types = [types]
    if token.type not in types:
        msg = ('Invalid token type "%s"; expected one of: %s'
               % (token.type, types))
        parser_error(filename, token, msg)


def parse_statement(toks):
    """
    Parses and type-checks a group of tokens representing a
    single statement. Returns a statement object.
    """
    op = arg1 = arg2 = dest = None
    if toks and toks[0].type == 'LABEL':
        label = toks.pop(0)
        labels[label.value] = mc
    if not toks:
        return False
    op = toks.pop(0)
    expected_ntok = {'OP00': 0, 'OP10': 1, 'OP11': 3, 'OP21': 5}
    check_type(op, expected_ntok.keys())
    if len(toks) != expected_ntok[op.type]:
        msg = ('Got %i tokens for op "%s", expected %i'
               % (len(toks), op.value, expected_ntok[op.type]))
        parser_error(filename, op, msg)
    if op.type in ('OP10', 'OP11', 'OP21'):
        arg1 = toks.pop(0)
        check_type(arg1, SRC_TYPES)
    if op.type == 'OP21':
        comma = toks.pop(0)
        check_type(comma, 'COMMA')
        arg2 = toks.pop(0)
        check_type(arg2, SRC_TYPES)
    if op.type in ('OP11', 'OP21'):
        at = toks.pop(0)
        check_type(at, 'AT')
        dest = toks.pop(0)
        check_type(dest, DEST_TYPES)
    return Statement(op, arg1, arg2, dest)


def assemble(statements):
    """
    Assemble stream of statements into machine code instructions.
    """
    for st in statements:
        ins_bits = [0] * 16
        mem_bits = [0] * 16
        # halt, noop
        if st.op.type == 'OP00':
            if st.op.value == 'halt':
                ins_bits = [1] * 16
            elif st.op.value == 'noop':
                pass
            yield Instruction(ins_bits, mem_bits)
            continue

        # figure out read and write locations
        elif st.op.type == 'OP10':
            rdloc = st.arg1
            wrloc = st.arg1
        elif st.op.type == 'OP11':
            rdloc = st.arg1
            wrloc = st.dest
        elif st.op.type == 'OP21':
            wrloc = st.dest
            if st.arg1.type == 'DREG' and st.arg1.value == 'A':
                rdloc = st.arg2
                if st.op.value.startswith('sub'):
                    st.op.value += 'xy'
            elif st.arg2.type == 'DREG' and st.arg2.value == 'A':
                rdloc = st.arg1
                if st.op.value.startswith('sub'):
                    st.op.value += 'yx'
            else:
                msg = 'One of the operands for op "%s" must be A' % st.op.value
                parser_error(filename, st.op, msg)

        # check that read and write locations are compatible
        if rdloc.type not in ('DREG', 'IREG'):
            if wrloc.type not in ('DREG', 'IREG'):
                if rdloc.type != wrloc.type or rdloc.value != wrloc.value:
                    msg = ('Cannot use immediate addressing for both operand'
                           ' and dest: %s, %s') % (rdloc.value, wrloc.value)
                    parser_error(filename, rdloc, msg)

        # write alu and jump bits
        ins_bits[6:13] = codes.ops.get(st.op.value, [0, 0, 0, 0, 0, 0, 0])
        ins_bits[13:16] = codes.jumps.get(st.op.value, [0, 0, 0])

        # write readloc bits
        if rdloc.type in ('DREG', 'IREG'):
            ins_bits[0:3] = codes.locations[rdloc.type][rdloc.value]
        else:
            ins_bits[0:3] = codes.locations['IREG']['INS1']

        if rdloc.type == 'IDENT':
            mem_bits = rdloc.value
        elif rdloc.type == 'CONST':
            mem_bits = 'const_%i' % len(constants)
            constants.append(rdloc.value)
        elif rdloc.type == 'ADDR':
            mem_bits = num2bits(rdloc.value, 16)

        # write writeloc bits
        if wrloc.type in ('DREG', 'IREG'):
            ins_bits[3:6] = codes.locations[wrloc.type][wrloc.value]
        else:
            ins_bits[3:6] = codes.locations['IREG']['INS1']

        if wrloc.type == 'IDENT':
            mem_bits = wrloc.value
        elif wrloc.type == 'ADDR':
            mem_bits = num2bits(wrloc.value, 16)

        yield Instruction(ins_bits, mem_bits)


def num2bits(num, length=0):
    """
    Convert a number to an array of bits of the give length
    """
    if length and num.bit_length() > length:
        raise ValueError('Number does not fit in bits')
    bits = []
    while num:
        bits.insert(0, num & 1)
        num = num >> 1
    return [0] * (length - len(bits)) + bits


def bits2num(bits):
    """
    Convert an array of bits to an integer
    """
    k = 1
    s = 0
    while bits:
        s += k * bits.pop(-1)
        k *= 2
    return s


def bits2hex(bits, length=0):
    hexnum = hex(bits2num(bits))[2:]
    if length:
        if len(hexnum) > length:
            raise ValueError('Number does not fit in bits')
        hexnum = '0' * (length - len(hexnum)) + hexnum
    return hexnum


def allocate_constants():
    global constants, debug, mc
    if debug:
        print(constants)
    for n, cons in enumerate(constants):
        labels['const_%i' % n] = mc
        mc += 1


def substitute_labels(instructions):
    for ins in instructions:
        if isinstance(ins.addr, str):
            yield Instruction(ins.ins, num2bits(labels[ins.addr], 16))
        else:
            yield ins


def emit_inst_bytes(instructions):
    """
    Emit instructions bytes, as bit arrays
    """
    for ins in instructions:
        yield ins.ins[:8]
        yield ins.ins[8:]
        yield ins.addr[:8]
        yield ins.addr[8:]


def emit_data_bytes():
    """
    Emit data bytes, as bit arrays
    (Data are program constants)
    """
    global constants
    for c in constants:
        bits = num2bits(c, 16)
        yield bits[:8]
        yield bits[8:]


def write(byte_stream, fp):
    """
    Write bytes to file.

    Depending on the extension of the global filename_out,
    either write as binary (.bin), logisim memory file format (.ram),
    or human-readable binary (any other format, including stdout).
    """
    global filename, filename_out
    # RAM here refers to a Logisim ram file
    if filename_out.split('.')[-1] == 'ram':
        ram_header = 'v2.0 raw\n'
        fp.write(ram_header)
        seps = [' '] * 8 + ['\n']
        sn = 0
        for bit_array in byte_stream:
            next_bits = next(byte_stream) or [0] * 8
            fp.write(bits2hex(bit_array + next_bits, 4) + seps[sn])
            sn = (sn + 1) % len(seps)
        fp.write('\n')
    elif filename_out.split('.')[-1] == 'bin':
        for bit_array in byte_stream:
            fp.write(chr(bits2num(bit_array)))
    else:  # write in text format
        fmt = '%i' * 8
        seps = ('', ' ', '', '\n')
        sn = 0
        for bit_array in byte_stream:
            fp.write(fmt % tuple(bit_array) + seps[sn])
            sn = (sn + 1) % len(seps)
        fp.write('\n')


def main(fp_in, fp_out):
    lex.lex()
    lex.input(fp_in.read())
    tokens = iter(lex.token, None)
    instructions = list(assemble(parse(tokens)))
    allocate_constants()
    inst_stream = emit_inst_bytes(substitute_labels(instructions))
    data_stream = emit_data_bytes()
    byte_stream = itertools.chain(inst_stream, data_stream)
    write(byte_stream, fp_out)


def parser_error(fn, token, text):
    msg = 'file %s, line %i - %s'
    msg = msg % (fn, token.lineno, text)
    print(msg, file=sys.stderr)
    sys.exit(1)


if __name__ == '__main__':
    global debug, filename, filename_out
    debug = True

    if len(sys.argv) > 1:
        filename = sys.argv[1]
        fp_in = open(filename, 'r')
    else:
        fp_in = sys.stdin
        filename = 'stdin'
    if len(sys.argv) > 2:
        filename_out = sys.argv[2]
        if filename_out.split('.')[-1] == 'bin':
            mode = 'wb'
        else:
            mode = 'w'
        fp_out = open(filename_out, mode)
    else:
        fp_out = sys.stdout
        filename_out = 'stdout'

    main(fp_in, fp_out)
    if fp_in is not sys.stdin:
        fp_in.close()
    if fp_out is not sys.stdout:
        fp_out.close()
    sys.exit(0)
