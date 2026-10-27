# 1549_B. Gregor and the Pawn Game (incorrect submission, CC BY 4.0 (deepmind/code_contests))
##
#    author:  kostya
#    created: 2021-08-01 17:28:01
#    modified 2021-08-01 17:46:37
##

for t in range(int(input())):
	n = int(input())
	p = list(input())
	p = list(map(int, p))
	m = list(input())
	m = list(map(int, m))
	for i in range(n):
		if m[0] == 0:
			continue
		if i == 0:
			if p[0] == 0:
				p[0] = 2
		if i != 0 and p[i - 1] == 1:
			p[i - 1] = 2
		elif p[i] == 0:
			p[i] = 2
		elif i + 1 < n and p[i + 1] == 1:
			p[i] = 2
	print(p.count(2))
