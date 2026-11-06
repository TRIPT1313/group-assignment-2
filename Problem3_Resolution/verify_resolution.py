"""Independent Python checker for the ground resolution chain; does not replace Prolog execution."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
clauses={
 'c1':{('-','archivist(mira)'),('-','verifies(mira,scroll_7)'),('+','trusted(mira)')},
 'c3':{('-','inspects(mira,scroll_7)'),('-','finds_mark(mira,scroll_7)'),('+','verifies(mira,scroll_7)')},
 'c7':{('+','inspects(mira,scroll_7)')},
 'c8':{('+','finds_mark(mira,scroll_7)')},
 'c9':{('+','archivist(mira)')},
 'c10':{('-','trusted(mira)')},
}
def resolve(a,b,pivot):
 pa=('+',pivot);na=('-',pivot)
 assert (pa in a and na in b) or (na in a and pa in b)
 return (a|b)-{pa,na}
def fmt(s):return '['+', '.join(sorted(('~' if sign=='-' else '')+atom for sign,atom in s))+']'
steps=[('r1','c1','c10','trusted(mira)'),('r2','r1','c9','archivist(mira)'),('r3','r2','c3','verifies(mira,scroll_7)'),('r4','r3','c7','inspects(mira,scroll_7)'),('r5','r4','c8','finds_mark(mira,scroll_7)')]
lines=['ROYAL ARCHIVE - VERIFIED RESOLUTION REFUTATION','Negated goal: ~trusted(mira)']
for label,a,b,pivot in steps:
 clauses[label]=resolve(clauses[a],clauses[b],pivot)
 lines.append(f'{label} from {a} + {b} => {fmt(clauses[label])}')
assert clauses['r5']==set()
lines.extend(['EMPTY CLAUSE [] DERIVED.','CONCLUSION: trusted(mira) is entailed.'])
( ROOT/'outputs'/'screenshots'/'resolution_python_verified_output.txt').write_text('\n'.join(lines)+'\n')
print('\n'.join(lines))
