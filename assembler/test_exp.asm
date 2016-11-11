begin:
	// If exponent is 0, A=1, jump to end
	load expnt @X
	load 1 @A
	jmpz end
	load 1 @D
	load base @X
mult:  // A = X * D
	zero A
	add A,X @A
	dec D
	jmpnz mult
pow:
	dec expnt
	jmpz end
	load base @D
	copy A @X
	jmp mult
end:
	halt  // expected: A = 189 (0xbd)
base:	3
expnt:	5
