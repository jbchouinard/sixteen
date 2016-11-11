store 32768 @SP  // set up stack pointer
load 0xcaca @A
push A
pop D  // expected: D = 0xcaca
