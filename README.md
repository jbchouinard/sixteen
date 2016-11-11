# A simulated 16-bit computer

##Table of Contents

* [Overview](#overview)
* [Installation](#installation)
* [Hardware Specification](#hardware-specification)
    * [Overview](#overview)
    * [Registers](#registers)
    * [ALU](#alu)
    * [CPU](#cpu)
        * [Codes](#codes)
        * [Read/Write Location](#readwrite-location)
        * [ALU Control](#alu-control)
        * [Jump Conditions](#jump-conditions)
* [Changelog](#changelog)
* [Todo](#todo)

## Overview

This is an educational project, with the goal of learning how computers work at a low level
by implementing a complete, functional 16 bit computer in Logisim, and an assembler for its machine language.

The ALU interface is largely inspired by http://www.nand2tetris.org/ - though the implementation is my own.

The CPU builds on the Hack architecture from nand2tetris, but is a bit more sophisticated.
 * hardware stack operations
 * combined program and data memory
 * separate accumulator and address registers
 * 32 bit op codes combining instruction and address
 * carry bit latch (for arithmetic and conditional jumps)

Their machine codes are entirely different.

## Installation

Install Logisim, following instructions at http://www.cburch.com/logisim/. 

The entire computer is contained in sixteen.circ.

## Hardware Specification

### Overview

16 bit ALU

32KiB memory

Memory-mapped keyboard and display

3 usable registers

16 - 32 bit op codes (16 bit instruction, optional 16 bit address)

### Registers

*List of registers (all 16-bit)*

| Name   | Details             |
|--------|---------------------|
| A      | accumulator         |
| D      | data                |
| X      | index (address)     |
| PC     | program counter     |
| SP     | stack pointer       |
| INS0   | instruction         |
| INS1   | instruction address |

### ALU

16-bit, uses 6 bit control code. Uses same control codes as ALU from the nand2tetris course -
the truth table for its most useful functions is reproduced below.

Unlike the n2t ALU, this one has carry in and carry out bits.

*ALU Truth Table*

| zx  | nx   | zy  | ny   | f     | no       | out     |
|-----|------|-----|------|-------|----------|---------|
| x=0 | x=!x | y=0 | y=!y | & / + | out=!out | f(x,y)= |
| 1   | 0    | 1   | 0    | 1     | 0        | 0       |
| 1   | 1    | 1   | 1    | 1     | 1        | 1       |
| 1   | 1    | 1   | 0    | 1     | 0        | -1      |
| 0   | 0    | 1   | 1    | 0     | 0        | x       |
| 1   | 1    | 0   | 0    | 0     | 0        | y       |
| 0   | 0    | 1   | 1    | 0     | 1        | !x      |
| 1   | 1    | 0   | 0    | 0     | 1        | !y      |
| 0   | 0    | 1   | 1    | 1     | 1        | -x      |
| 1   | 1    | 0   | 0    | 1     | 1        | -y      |
| 0   | 1    | 1   | 1    | 1     | 1        | x+1     |
| 1   | 1    | 0   | 1    | 1     | 1        | y+1     |
| 0   | 0    | 1   | 1    | 1     | 0        | x-1     |
| 1   | 1    | 0   | 0    | 1     | 0        | y-1     |
| 0   | 0    | 0   | 0    | 1     | 0        | x+y     |
| 0   | 1    | 0   | 0    | 1     | 1        | x-y     |
| 0   | 0    | 0   | 1    | 1     | 1        | y-x     |
| 0   | 0    | 0   | 0    | 0     | 0        | x&y     |
| 0   | 1    | 0   | 1    | 0     | 1        | x\|y    |

### CPU

#### Codes

*Meaning of bits in machine code instructions*

| Bit #           | Name | Details                |
|-----------------|------|------------------------|
| 15 (high order) | R0   | Read location          |
| 14              | R1   |    *                   |
| 13              | R2   |    *                   |
| 12              | W0   | Write location         |
| 11              | W1   |    *                   |
| 10              | W2   |    *                   |
| 9               | ZX   | ALU control            |
| 8               | NX   |    *                   |
| 7               | ZY   |    *                   |
| 6               | NY   |    *                   |
| 5               | F    |    *                   |
| 4               | NO   |    *                   |
| 3               | UC   | Use carry?             |
| 2               | J0   | Jump control           |
| 1               | J1   |    *                   |
| 0 (low order)   | J2   |    *                   |

##### Read/Write Location

The R0-R2 bits select the location to read from.
Technically, they determine the second (y) input to the ALU.

The next 3 bits, W0-W2, select where to write the output of the ALU.

*Meaning of location bits*

| Bits | Location | Details                          |
|------|----------|----------------------------------|
| 000  | A        | Register A                       |
| 001  | *A       | Memory at address in register A  |
| 010  | SP       | Register SP                      |
| 011  | *SP      | Top of stack                     |
| 100  | X        | Register X                       |
| 101  | *X       | Memory at address in register X  |
| 110  | D        | Register D                       |
| 111  | *INS1    | Memory at address in instruction |

Data always passes through the ALU.
Store and load instructions are implemented by using the identity functions of the ALU.

##### ALU Control

These bits correspond directly to the ALU control bits (see the [ALU specification](#alu)).

##### Jump Conditions

Jumps can be performed unconditionally, or conditionally based on the result of
the last instruction.

*Meaning of jump condition bits*

| Bits | Condition         |
|------|-------------------|
| 000  | No jump           |
| 001  | Jump if zero      |
| 010  | Jump if negative  |
| 011  | Jump if carry     |
| 100  | Jump              |
| 101  | Jump if not zero  |
| 110  | Jump if positive  |
| 111  | Jump if not carry |

## Changelog

* 2016-11-07: Finished writing assembler. Functions for simple programs, need to test more thoroughly.
* 2016-11-06: Wrote parser for assembler
* 2016-10-25: Jump logic done, most of write location logic done.
* 2016-10-24: The CPU control logic for read location and ALU is done. Memory chip w/out devices is done.
* 2016-10-23: The ALU is done, most of the basic CPU layout is done, but the CPU control logic is missing.

## Todo

* Write assembly specification
* Add constant literals to assembler
* Add macro processor to assembler
* Add macros: push, pop, call
* Build CPU chip tester
* Finish and test write location logic
* Finish and test jump logic
* Keyboard control chip
* Screen control chip
* Memory chip with memory-mapped screen and keyboard

*Maybe?*

* Load program constants directly from INS1
* Variable # of cycles per instruction (skip INS1/FD fetchs for opcodes that don't need them)
* OR: switch to a more RISC-y architecture, go back to 16 bit instructions only
* Hardware bit shift op
* Keyboard interrupts
