// This file is part of www.nand2tetris.org
// and the book "The Elements of Computing Systems"
// by Nisan and Schocken, MIT Press.

// Multiplies R0 and R1 and stores the result in R2.
// (R0, R1, R2 refer to RAM[0], RAM[1], and RAM[2], respectively.)
// The algorithm is based on repetitive addition.

// Bitwise multiplication.
/*
    R2 = 0
    mask = 1
LOOP:
    if (mask == 0) goto END
    if (R1 & mask == 0) goto SKIP
    R2 = R2 + R0
SKIP:
    mask = 2 * mask
    R0 = 2 * R0
    goto LOOP
END:
*/

// R2 = 0
@R2
M=0
// mask = 1
@mask
M=1
(LOOP)
// if (mask == 0) goto END
@mask
D=M
@END
D;JEQ
// if (R1 & mask == 0) goto SKIP
@R1
D=M
@mask
D=D&M
@SKIP
D;JEQ
// R2 = R2 + R0
@R2
D=M
@R0
D=D+M
@R2
M=D
(SKIP)
// mask = 2 * mask
@mask
D=M
@mask
D=D+M
@mask
M=D
// R0 = 2 * R0
@R0
D=M
@R0
D=D+M
@R0
M=D
// goto LOOP
@LOOP
0;JMP
(END)
@END
0;JMP
