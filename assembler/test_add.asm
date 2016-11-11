one A
add A,A @A  // A = 2
add A,A @A  // A = 4
add A,A @A  // etc.
add A,A @A
add A,A @A
add A,A @A
add A,A @A
add A,A @A
add A,A @A
add A,A @A
add A,A @A
copy A @D  // expected: D = 1024 (0x400)
halt
