begin:  zero A
	load 12 @D
	load 14 @X
mult:	add A,D @A
	dec X
	jmpnz mult
end:	halt  // Expected: A = 168
