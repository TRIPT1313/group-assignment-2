% Royal Archive: resolution refutation of trusted(mira).
% Run: swipl -q -s royal_archive_access.pl -g main -t halt
%
% Step 1: Predicate logic representation
% Predicates: archivist/1, verifies/2, trusted/1, has_access/2,
% sealed/1, permitted/2, inspects/2, finds_mark/2, stored/1.
% Constants: mira, scroll_7. Variables: X, R.
% (1) forall X,R: (archivist(X) & verifies(X,R)) -> trusted(X).
% (2) forall X,R: (trusted(X) & has_access(X,R) & sealed(R)) -> permitted(X,R).
%     The sealed condition expresses that permission concerns sealed records.
% (3) forall X,R: (inspects(X,R) & finds_mark(X,R)) -> verifies(X,R).
% (4) forall R: stored(R) -> sealed(R).
% (5)-(8) stored(scroll_7), has_access(mira,scroll_7),
%            inspects(mira,scroll_7), finds_mark(mira,scroll_7), archivist(mira).
%
% Step 2: Negation of goal
% Negated goal: not(trusted(mira)).
%
% Step 3: Implication removal
% (1) ~archivist(X) v ~verifies(X,R) v trusted(X).
% (2) ~trusted(X) v ~has_access(X,R) v ~sealed(R) v permitted(X,R).
% (3) ~inspects(X,R) v ~finds_mark(X,R) v verifies(X,R).
% (4) ~stored(R) v sealed(R).
%
% Step 4: Negation movement
% All negations already apply only to atomic predicates (NNF).
%
% Step 5: Standardization
% Each clause has independent universally quantified variables X1,R1;
% X2,R2; X3,R3; R4. Prolog variables are renamed apart by copy_term/2.
%
% Step 6: Skolemization
% No existential quantifiers occur, so no Skolem constants/functions are needed.
%
% Step 7: CNF clauses
% A clause is a list of pos(Atom) or neg(Atom).
clause_kb(c1,[neg(archivist(X)),neg(verifies(X,R)),pos(trusted(X))]).
clause_kb(c2,[neg(trusted(X)),neg(has_access(X,R)),neg(sealed(R)),pos(permitted(X,R))]).
clause_kb(c3,[neg(inspects(X,R)),neg(finds_mark(X,R)),pos(verifies(X,R))]).
clause_kb(c4,[neg(stored(R)),pos(sealed(R))]).
clause_kb(c5,[pos(stored(scroll_7))]).
clause_kb(c6,[pos(has_access(mira,scroll_7))]).
clause_kb(c7,[pos(inspects(mira,scroll_7))]).
clause_kb(c8,[pos(finds_mark(mira,scroll_7))]).
clause_kb(c9,[pos(archivist(mira))]).
clause_kb(c10,[neg(trusted(mira))]). % Negated goal

% Step 8: Binary resolution with first-order unification
% Copies avoid shared variable bindings between source clauses.
complement(pos(T),neg(U)) :- unify_with_occurs_check(T,U).
complement(neg(T),pos(U)) :- unify_with_occurs_check(T,U).
resolve(ClauseA,ClauseB,Resolvent) :-
 copy_term((ClauseA,ClauseB),(A,B)),
 select(LA,A,RemainingA),
 select(LB,B,RemainingB),
 complement(LA,LB),
 append(RemainingA,RemainingB,Joined),
 sort(Joined,Resolvent).

print_step(Label,Parents,Result) :-
 format('~w from ~w => ~q~n',[Label,Parents,Result]).

% A sound goal-directed resolution-refutation chain, including each resolvent.
% Resolution of c1 with c10 initially leaves X=mira, R unbound.
% Resolving with archivist(mira) then with c3 and the two facts
% binds R to scroll_7.
proof :-
 clause_kb(c1,C1),clause_kb(c10,C10),
 resolve(C1,C10,R1),
 member(neg(archivist(mira)),R1),
 member(neg(verifies(mira,_)),R1),
 print_step(r1,'c1 + c10',R1),
 clause_kb(c9,C9),resolve(R1,C9,R2),
 member(neg(verifies(mira,_)),R2),
 print_step(r2,'r1 + c9',R2),
 clause_kb(c3,C3),resolve(R2,C3,R3),
 member(neg(inspects(mira,_)),R3),
 member(neg(finds_mark(mira,_)),R3),
 print_step(r3,'r2 + c3',R3),
 clause_kb(c7,C7),resolve(R3,C7,R4),
 R4=[neg(finds_mark(mira,scroll_7))],
 print_step(r4,'r3 + c7',R4),
 clause_kb(c8,C8),resolve(R4,C8,Empty),
 Empty=[],
 print_step(r5,'r4 + c8',Empty),
 writeln('EMPTY CLAUSE [] DERIVED.'),
 writeln('CONCLUSION: trusted(mira) is entailed.'), !.

main :-
 writeln('ROYAL ARCHIVE - FOL RESOLUTION REFUTATION'),
 writeln('Negated goal: ~trusted(mira)'),
 (proof -> halt(0) ; writeln('PROOF FAILED'), halt(1)).
