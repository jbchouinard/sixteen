## Tentative Specs

### Overview

32k16RAM (64kiB)

16 bit ALU with 6-bit control code (from the nand2tetris course)

1 index register

1 accumulator register

1 data register

Memory mapped keyboard and display

16-32 bit op codes (16 bit instruction, optional 16 bit address)

### Instruction Code Format

| **Bit** | **Name** | **Details**    |
|-----|------|------------------------|
| 0   | OP   | Op                     |
| 1   | O0   | Extra Op               |
| 2   | O1   |                        |
| 3   | O2   |                        |
| 4   | O3   |                        |
| 5   | ZX   | ALU Control            |
| 6   | ZY   |                        |
| 7   | NX   |                        |
| 8   | NY   |                        |
| 9   | F    |                        |
| 10  | NO   |                        |
| 11  | UC   | Use carry?             |
| 12  | JP   | Jump?                  |
| 13  | J0   | Jump condition         |
| 14  | J1   |                        |
| 15  | JN   | Negate jump condition? |

### Registers
| **Name**  | **Details**         |
|-----------|---------------------|
| A         | accumulator         |
| D         | data                |
| X         | index               |
| PC        | program counter     |
| SP        | stack pointer       |
| INS0      | instruction         |
| INS1      | instruction address |
| CAR       | carry               |
