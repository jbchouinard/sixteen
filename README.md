# Sixteen - a simulated 16 bit computer

This is an educational project, with the goal of learning how computers work at a low level
by implementing a complete, functional 16 bit computer in Logisim, and an assembler for its machine language.

The design of the ALU is taken from http://www.nand2tetris.org/.

The CPU builds on the Hack architecture from nand2tetris but is a bit more sophisticated and has a 
mostly different machine language.

Compared to the Hack CPU, this one has:
 * hardware stack operations
 * combined program and data memory
 * separate accumulator and address registers, allowing:
 * 32 bit op codes combining instruction and address
 * carry bit register (for arithmetic and conditional jumps)
 
## Changelog

* 2016-10-24: The CPU control logic for read location and ALU is done. Memory chip w/out devices is done.
* 2016-10-23: The ALU is done, most of the basic CPU layout is done, but the CPU control logic is missing.

## Todo

* Write location logic
* Jump logic
* Keyboard control chip
* Screen control chip
* Memory chip with memory-mapped screen and keyboard
* Assembler

## Installation

Install Logisim, following instructions at http://www.cburch.com/logisim/. 

The entire computer is contained in sixteen.circ.

## Hardware Specification

### Overview

32k16RAM (64kiB)

16 bit ALU with 6-bit control code

1 index register

1 accumulator register

1 data register

Memory mapped keyboard and display

16 to 32 bit op codes (16 bit instruction, optional 16 bit address)

### Registers

*List of registers*

| Name   | Details             |
|--------|---------------------|
| A      | accumulator         |
| D      | data                |
| X      | index (address)     |
| PC     | program counter     |
| SP     | stack pointer       |
| INS0   | instruction         |
| INS1   | instruction address |
| CAR    | carry               |

### ALU

16-bit, uses 6 bit control code. Uses same control codes as ALU from the nand2tetris course -
the truth table for its most useful functions is reproduced below.

*ALU Truth Table (Non-exhaustive)*

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
| 8               | ZY   |    *                   |
| 7               | NX   |    *                   |
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
| 010  | Jump if positive  |
| 011  | Jump if carry     |
| 100  | Jump              |
| 101  | Jump if not zero  |
| 110  | Jump if negative  |
| 111  | Jump if not carry |
