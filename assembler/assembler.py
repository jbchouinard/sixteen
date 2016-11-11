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
    r'one|zero|inc|dec|jmp(nc|z|nz|pos|neg)?|push|pop|call'
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
    r'(0x[0-9a-fA-F]+)|([0-9]+)'
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
    parser_error(filename, t.lineno, 'Invalid syntax near "%s"' % t.value)


names = {}  # map of names to memory addresses
constants = []  # unallocated constants
identifiers = []  # unallocated identifiers
mc = 0  # memory counter

SRC_TYPES = ('ADDR', 'IREG', 'DREG', 'IDENT', 'CONST')
DEST_TYPES = ('ADDR', 'IREG', 'DREG', 'IDENT')


Statement = namedtuple('Statement', ('op', 'arg1', 'arg2', 'dest', 'lineno'))
Word = namedtuple('Word', ('type', 'value'))
Instruction = namedtuple('Instruction', ('ins', 'addr'))


def macro_push(stmt):
    return [
        Statement(
            Word('OP10', 'dec'),
            Word('DREG', 'SP'), None, None,
            stmt.lineno
        ),
        Statement(
            Word('OP11', 'store'),
            stmt.arg1, None,
            Word('IREG', 'SP'),
            stmt.lineno
        ),
    ]


def macro_pop(stmt):
    return [
        Statement(
            Word('OP11', 'load'),
            stmt.arg1, None,
            Word('IREG', 'SP'),
            stmt.lineno
        ),
        Statement(
            Word('OP10', 'inc'),
            Word('DREG', 'SP'), None, None,
            stmt.lineno
        ),
    ]


def macro_call(statement):
    return [statement]


macros = {
    'push': macro_push,
    'pop': macro_pop,
    'call': macro_call,
}


def parse(tokens):
    """
    Parse a stream of tokens into a stream of statements.
    """
    global debug, mc
    stmt_toks = []
    for tok in tokens:
        if tok.type == 'SEP':
            if stmt_toks:
                stmts = parse_statement(stmt_toks)
                for stmt in stmts:
                    if debug:
                        print(stmt)
                    mc += 2
                    yield stmt
            stmt_toks = []
        else:
            stmt_toks.append(tok)


def check_type(word, types, lineno):
    if not isinstance(types, list) and not isinstance(types, tuple):
        types = [types]
    if word.type not in types:
        msg = ('Invalid word type "%s"; expected one of: %s'
               % (word.type, types))
        parser_error(filename, lineno, msg)


def parse_statement(toks):
    """
    Parses, type-checks and apply macros on a group of tokens representing a
    single statement. Returns a list of statement objects.
    """
    global names
    op = arg1 = arg2 = dest = label = None
    if toks and toks[0].type == 'LABEL':
        label = toks.pop(0).value
        names[label] = mc
    if not toks:
        return []
    op = toks.pop(0)
    lineno = op.lineno
    op = Word(op.type, op.value)
    expected_ntok = {'OP00': 0, 'OP10': 1, 'OP11': 3, 'OP21': 5, 'CONST': 0}
    if op.type not in expected_ntok:
        msg = ('Expected an operation keyword, not "%s"' % op.value)
        parser_error(filename, lineno, msg)
    if len(toks) != expected_ntok[op.type]:
        msg = ('Got %i tokens for op "%s", expected %i'
               % (len(toks), op.value, expected_ntok[op.type]))
        parser_error(filename, lineno, msg)
    if op.type in ('OP10', 'OP11', 'OP21'):
        arg1 = toks.pop(0)
        arg1 = Word(arg1.type, arg1.value)
        check_type(arg1, SRC_TYPES, lineno)
    if op.type == 'OP21':
        comma = toks.pop(0)
        check_type(comma, 'COMMA', lineno)
        arg2 = toks.pop(0)
        arg2 = Word(arg2.type, arg2.value)
        check_type(arg2, SRC_TYPES, lineno)
    if op.type in ('OP11', 'OP21'):
        at = toks.pop(0)
        check_type(at, 'AT', lineno)
        dest = toks.pop(0)
        dest = Word(dest.type, dest.value)
        check_type(dest, DEST_TYPES, lineno)
    statement = Statement(op, arg1, arg2, dest, lineno)
    if op.value in macros:
        statements = macros[op.value](statement)
    else:
        statements = [statement]
    return statements


def assemble(statements):
    """
    Assemble stream of statements into machine code instructions.
    """
    global constants, identifiers
    for st in statements:
        ins_bits = [0] * 16
        mem_bits = [0] * 16
        if st.op.type == 'CONST':
            ins_bits = num2bits(st.op.value, 16)
            mem_bits = None
            yield Instruction(ins_bits, mem_bits)
            continue
        # halt, noop
        elif st.op.type == 'OP00':
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
                parser_error(filename, st.lineno, msg)

        # check that read and write locations are compatible
        if rdloc.type not in ('DREG', 'IREG'):
            if wrloc.type not in ('DREG', 'IREG'):
                if rdloc.type != wrloc.type or rdloc.value != wrloc.value:
                    msg = ('Cannot use immediate addressing for both operand'
                           ' and dest: %s, %s') % (rdloc.value, wrloc.value)
                    parser_error(filename, st.lineno, msg)

        # write alu and jump bits
        ins_bits[6:13] = codes.ops.get(st.op.value, [0, 0, 0, 0, 0, 0, 0])
        ins_bits[13:16] = codes.jumps.get(st.op.value, [0, 0, 0])

        # write readloc bits
        if rdloc.type in ('DREG', 'IREG'):
            ins_bits[0:3] = codes.locations[rdloc.type][rdloc.value]
        else:
            ins_bits[0:3] = codes.locations['IREG']['INS1']

        if rdloc.type == 'IDENT':
            identifiers.append(rdloc.value)
            mem_bits = rdloc.value
        elif rdloc.type == 'CONST':
            if rdloc.value in constants:
                ii = constants.index(rdloc.value)
            else:
                ii = len(constants)
                constants.append(rdloc.value)
            mem_bits = 'const_%i' % ii
        elif rdloc.type == 'ADDR':
            mem_bits = num2bits(rdloc.value, 16)

        # write writeloc bits
        if wrloc.type in ('DREG', 'IREG'):
            ins_bits[3:6] = codes.locations[wrloc.type][wrloc.value]
        else:
            ins_bits[3:6] = codes.locations['IREG']['INS1']

        if wrloc.type == 'IDENT':
            identifiers.append(wrloc.value)
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


def allocate_names():
    """
    Set up memory addresses for constants and variables
    """
    global constants, identifiers, names,  mc
    for ident in identifiers:
        if ident not in names:
            names[ident] = mc
            mc += 1
    for n, cons in enumerate(constants):
        names['const_%i' % n] = mc
        mc += 1


def substitute_names(instructions):
    for ins in instructions:
        if isinstance(ins.addr, str):
            yield Instruction(ins.ins, num2bits(names[ins.addr], 16))
        else:
            yield ins


def emit_inst_bytes(instructions):
    """
    Emit instructions bytes, as bit arrays
    """
    for ins in instructions:
        yield ins.ins[:8]
        yield ins.ins[8:]
        if ins.addr:
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
    allocate_names()
    inst_stream = emit_inst_bytes(substitute_names(instructions))
    data_stream = emit_data_bytes()
    byte_stream = itertools.chain(inst_stream, data_stream)
    write(byte_stream, fp_out)


def parser_error(fn, lineno, text):
    msg = 'file %s, line %i - %s'
    msg = msg % (fn, lineno, text)
    print(msg, file=sys.stderr)
    sys.exit(1)


if __name__ == '__main__':
    global debug, filename, filename_out
    debug = False

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
