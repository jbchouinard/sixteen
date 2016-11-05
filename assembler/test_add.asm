:begin 
	one A
	inc A
	inc A
	add A,A @D  // D = 2*A
	add D,D @A  // A = 2*D = 4*A
	store A @$result  // result = A
	load $result @D   // D = result
:end
