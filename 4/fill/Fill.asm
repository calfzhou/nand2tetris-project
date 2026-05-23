// This file is part of www.nand2tetris.org
// and the book "The Elements of Computing Systems"
// by Nisan and Schocken, MIT Press.

// Runs an infinite loop that listens to the keyboard input.
// When a key is pressed (any key), the program blackens the screen,
// i.e. writes "black" in every pixel. When no key is pressed,
// the screen should be cleared.

/*
    previous = -1
LOOP:
    if (kbd == previous) goto LOOP
    previous = kbd
    color = white
    if (previous == 0) goto FILL
    color = black
FILL:
    pos = SCREEN + 8k
LOOP2:
    pos = pos - 1
    *pos = color
    if (pos == SCREEN) goto LOOP
    goto LOOP2
*/

// previous = -1
@previous
M=-1
(LOOP)
// if (kbd == previous) goto LOOP
@KBD
D=M
@previous
D=D-M
@LOOP
D;JEQ
// previous = kbd
@KBD
D=M
@previous
M=D
// color = white
@color
M=0
// if (previous == 0) goto FILL
@previous
D=M
@FILL
D;JEQ
// color = black
@color
M=!M
(FILL)
// pos = SCREEN + 8k
@SCREEN
D=A
@8192
D=D+A
@pos
M=D
(LOOP2)
// pos = pos - 1
@pos
M=M-1
// *pos = color
@color
D=M
@pos
A=M
M=D
// if (pos == SCREEN) goto LOOP
@pos
D=M
@SCREEN
D=D-A
@LOOP
D;JEQ
// goto LOOP2
@LOOP2
0;JMP
