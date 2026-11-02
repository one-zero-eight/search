---
type: page
title: "Past exam papers: Theoretical Computer Science"
description: "Past exams and tests of Theoretical Computer Science at Innopolis University (8 papers, 2020–2024), collected by students: tasks, formats, points."
resource: "https://glebpopov.notion.site/4ef3de0c7e68495b89ef086301361603"
tags: ["past-papers", "exams", "bachelor", "theoretical-computer-science"]
audience: ["student"]
source_kind: community
language: en
section: "notion/past-papers"
subject: "Theoretical Computer Science"
sources:
  - resource: "https://glebpopov.notion.site/4ef3de0c7e68495b89ef086301361603"
    title: "IU B23 Academic Materials: Past Papers [EN programs]"
generated:
  by: "catix-wiki/0.1 past-papers (code only, no model)"
status: draft
---

# Past exam papers: Theoretical Computer Science

Exams and tests of **Theoretical Computer Science** from previous years, as the students collected them in [IU B23 Academic Materials: Past Papers [EN programs]](https://glebpopov.notion.site/4ef3de0c7e68495b89ef086301361603). Not an official source: a paper may be one variant of several, or written down from memory. Newest first.

## 2024: Midterm

Files: [TCS Midterm 2024.pdf](https://glebpopov.notion.site/ad7a3637bae3406797c880bdb6a96f8a)


Тест начат

Thursday, 7 March 2024, 11:26

Состояние Завершены
Завершен Thursday, 7 March 2024, 12:14
Прошло 48 мин. 7 сек.
времени
Оценка 16,00 из 20,00 (80%)
Вопрос 1
Частично правильный
Баллов: 0,67 из 1,00

Which of the following statements about FST is/are TRUE?

a. The translation may happen only to the accepted strings
b. The reading power of FST overcomes FSA’s power
c. It is an FSA with input and output tapes
d. The acceptance criteria does not differ from FSA
e. Input and output alphabets have to match
f.

FST stands for finite-state transgressor

Правильные ответы:
It is an FSA with input and output tapes,
The translation may happen only to the accepted strings,
The acceptance criteria does not differ from FSA

Вопрос 2
Верно
Баллов: 1,00 из 1,00

Suppose that language L is regular with critical value m. Is m+1 also a critical value? Which of the following proofs is valid?

a. No. Take string s ∈ L of length |s| ≥ m. According to condition (m is a critical value), there is a split s = x y z with |x y| ≤ m
and |y| ≥ 1. If we consider m+1 to be the critical value, it would also allow splits with |x y| ≤ m+1, in particular ─ |x y| =
m+1, which are not covered by the condition, q.e.d.

b. Yes. Take string s ∈ L of length |s| ≥ m+1 ≥ m. According to condition (m is a critical value), there is a split s = x y 
z with |x y| ≤ m ≤ m+1 and |y| ≥ 1, such that for all i, x yi z ∈ L, q.e.d.

c. Yes. Take string s ∈ L of length |s| ≥ m+1. Ignore the first symbol c of s and name the new string s’ (i.e. s = cs’). |s’|
= |s| - 1 ≤ m. According to condition (m is a critical value), there is a split s’ = x y z with |x y| ≤ m and |y| ≥ 1,
such that for all i, x yi z ∈ L. Thus, we can make a split s = cx y z, |cx y| = |x y| + 1 ≤ m+1, |y| ≤ 1, q.e.d.

d. No. The condition states that for all strings s ∈ L with length |s| ≥ m there is a split. However, if we take m+1 to be the critical
value, it will only consider strings s ∈ L with length |s| ≥ m+1, it will not cover strings s with length |s| = m, q.e.d.


Правильный ответ: Yes. Take string s ∈ L of length |s| ≥ m+1 ≥ m. According to condition (m is a critical value), there is a
split s = x y z with |x y| ≤ m ≤ m+1 and |y| ≥ 1, such that for all i, x yi z ∈ L, q.e.d.

Вопрос 3
Верно
Баллов: 1,00 из 1,00

Which of the following languages suits the drawn PDA

a. L = { anb2nan | n ∈ N \ {0} }
b. L = { a2nbnan | n ∈ N \ {0} }
c. L = { anb2na | n ∈ N \ {0} }
d. L = { a2nbna | n ∈ N \ {0} }

Правильный ответ:
L = { anb2na | n ∈ N \ {0} }

Вопрос 4
Верно
Баллов: 1,00 из 1,00

Find the rule transitions X and Y such that the following PDA recognizes the language L= {0n1n+1 | n ∈ N \ {0} }

a. X = “0, Z0 / AZ0”, Y = “1, A / A”
b. X = “0, Z0 / AZ0”, Y = “1, A / ϵ”
c. X = “0, Z0 / Z0”, Y = “1, A / ϵ”
d. X = “0, Z0 / Z0”, Y = “1, A / A”

Правильный ответ:
X = “0, Z0 / AZ0”, Y = “1, A / A”



Вопрос 5
Верно
Баллов: 1,00 из 1,00

Match the FSAs with the languages that may be accepted by them (Σ = {0, 1}).

L = {w ∈ Σ* | in w each 1 is preceded by double 0 ∧ w starts from 0}



L = {w ∈ Σ* | w starts from 0 ∧ w ends with 1 ∧ w does NOT contain substrings of the same symbols w



L = {w ∈ Σ* | w contains the substring 1001}



L = {w ∈ Σ* | w does NOT contain the substring 1001}



Правильный ответ:

→ L = {w ∈ Σ* | in w each 1 is preceded by double 0 ∧ w starts from 0},

→ L = {w ∈ Σ* | w starts from 0 ∧ w ends with 1 ∧ w does NOT contain substrings of

the same symbols with the length 2 ∧ |w| > 1},

→ L = {w ∈ Σ* | w contains the substring 1001},

→ L = {w ∈ Σ* | w does NOT contain the substring 1001}



Вопрос 6
Верно
Баллов: 1,00 из 1,00

While applying Pumping lemma over a language, we consider a string s that belongs to L and has the following property:

a. |s| ≤ |I| with I being the input alphabet of the FSA recognizing L
b. |s| ≥ 1
c. |s| > |Q| with Q being the set of states of the FSA recognizing L
d. |s| ≥ |Q| with Q being the set of states of the FSA recognizing L

Правильный ответ: |s| ≥ |Q| with Q being the set of states of the FSA recognizing L

Вопрос 7
Частично правильный
Баллов: 0,67 из 1,00

Which of the following languages require(s) unbounded memory to be recognized?

a. L = {ww | w ∈ {a, b}∗ ∧ |w| > 0}
b. anbm (n, m ∈ N)
c. anbn (n ∈ N)
d. an! (n ∈ N)

Правильные ответы:
anbn (n ∈ N),
an! (n ∈ N),
L = {ww | w ∈ {a, b}∗ ∧ |w| > 0}

Вопрос 8
Частично правильный
Баллов: 0,67 из 1,00

Which of the following statements about FSA is/are TRUE?

a. Each complete FSA is also deterministic
b. Reaching final state always means accepting the string 
c. The sets of initial and accepting states can never intersect
d. An FSA with a total transition function is called complete
e. In complete FSA the number of transitions from each state matches the number of symbols in the alphabet (assume no 
ε-moves)

Правильные ответы:
An FSA with a total transition function is called complete,
In complete FSA the number of transitions from each state matches the number of symbols in the alphabet (assume no ε-moves)



Вопрос 9
Неверно
Баллов: 0,00 из 1,00

Consider the union of 2 DFSTs. Given language L1 = {w ∈ Σ∗ | w is a binary string representing integer powers of 2, not starting with
0s ∧ |w|>0 } with Σ = {0, 1}. Accepted L1 string has to be translated into the binary string divided by 2 and still has to remain an
integer value using upper rounding, if needed. Given language L2 = {w ∈ Σ∗ | w is a binary string representing integers composed
of even number of 1s ∧ |w|>1 } with Σ = {0, 1}. Accepted L2 string has to be translated into the binary string replacing each second
1 with double 0.
Given the incomplete DFST type the missing transitions and translations with its input and output state indices, e.g. for missing
transition qy = (qx, 1) and translation into epsilon you should type x(1/eps)y. If multiple transitions are missing, use only comma as a
delimiter and use numerical order for initial states (0-5), transitions (0-1) and translations (eps, 0, 1).

Ответ:

3(0/00)4,3(1/01)1,5(0/eps)3,2(1/000)4



Правильный ответ: 2(1/eps)3,3(0/eps)3,3(1/eps)3,5(0/eps)3

Вопрос 10
Частично правильный
Баллов: 0,67 из 1,00

Which of the following is/are true?

a.

If language L is regular, there exists an FSA that accepts all and only s ∈ L.

b. If language L is regular, there is an FSA that accepts all s ∈ L and rejects all s ∉ L.
c. If language L is not regular, there is an FSA that accepts all s ∈ L and rejects all s ∉ L.
d. If language L is not regular, there is an FSA that accepts all s ∈ L.

Правильные ответы: If language L is regular, there exists an FSA that accepts all and only s ∈ L., If language L is not regular, there
is an FSA that accepts all s ∈ L.,
If language L is regular, there is an FSA that accepts all s ∈ L and rejects all s ∉ L.



Вопрос 11
Верно
Баллов: 1,00 из 1,00

What is a context-free language?

a. A language requiring an unbounded memory to be recognized 
b. A language that has no grammar rules
c. A language that can be spoken in any context
d. A language for which you can apply Pumping Lemma

Правильный ответ:
A language requiring an unbounded memory to be recognized

Вопрос 12
Верно
Баллов: 1,00 из 1,00

Relate the following statement: All sufficiently long words in a regular language can have a middle section of words repeated a
number of times to produce a new word which also lies within the same language. We know this statement as:

a. Myhill–Nerode theorem
b. Kleene's algorithm
c. Thompson's construction
d. None of the above

Правильный ответ:
None of the above



Вопрос 13
Верно
Баллов: 1,00 из 1,00

The following PDA recognizes L={ aibjck | i, j, k ∈ N \ {0} & RULL}. Find “RULL”.

a. RULL = “ k + j = i ”
b. RULL = “ j + i = k ”
c. RULL = “ i + i = k ”
d. RULL = “ i + k = j ”

Правильный ответ:
RULL = “ j + i = k ”

Вопрос 14
Верно
Баллов: 1,00 из 1,00

Which of the following languages suits the drawn PDA?

a. L = { (01)n1 | n>0 & n is odd }
b. L = { (01)n1 | n>0 & n is even 

(the rest is in the file)

## 2024: Pre Final

Files: [TCS Pre Final 2024.pdf](https://glebpopov.notion.site/48f3a29c6eca4749b4accc8f51620e2d)


Тест начат

Thursday, 2 May 2024

Вопрос 1
Верно
Баллов: 1,00 из 1,00

Complete the following statement with identification of what definition is it:
“Every_______ property of the recursively enumerable languages is undecidable”

a. nontrivial (this is the definition of Rice theorem)
b. nontrivial (this is the definition of Halting problem)
c. nontrivial (this is the definition of undecidable problem)
d. syntactic (this is the definition of Rice theorem)

Your answer is correct.
Правильный ответ:
nontrivial (this is the definition of Rice theorem)

Вопрос 2
Верно
Баллов: 1,00 из 1,00

Match NPDA with its description:

Выберите...

Выберите...

Выберите...

Выберите...

Your answer is correct.
Правильный ответ:

→ L = {wwR | w ∈ {a,b}*}, where wR is the reversed string w ∧ w starts

from a,

→ L = {wwR | w ∈ {a,b}*} where wR is the reversed string w,

→ L = {wwR | w ∈ {a,b}+} where wR is the reversed string w,

→ L = {wwR | w ∈ {a,b}*}, where wR is the reversed string w ∧ w starts

from a and ends with b

Вопрос 3
Верно
Баллов: 1,00 из 1,00

If L*= L , then which of the languages below could be L?
a. L = {0, 1}*
b. L = {w | w ∈ {0, 1}*, |w|≥ 1}
c. L = {0, 1, 00, 11, 000, 111, 0000, 1111 ...}
d. L = {w | w ∈ {0,1}* |w|= 2}

e. L = {w | w ∈ {0,1}*, |w|= 5}

Your answer is correct.
Правильный ответ:
L = {0, 1}*

Вопрос 4
Верно
Баллов: 1,00 из 1,00

What is the minimum number of states required by Turing Machine to accept strings which consist of an even
number of 1’s?

Ответ:

Правильный ответ: 2

Вопрос 5
Верно
Баллов: 1,00 из 1,00

The

problem, formulated by Alan Turing, demonstrates the existence of undecidable problems—

problems for which no algorithm can determine whether a given program ends or runs indefinitely on all
inputs.

Правильный ответ: halting

Вопрос 6
Верно
Баллов: 1,00 из 1,00

Select all that apply:
a. Deterministic PDA are NOT closed under union.
b. The complement of a NPDA can be gotten by swapping final and non-final states.
c. The class of languages recognized by deterministic PDAs is closed under complement.
d. Every PDA can be transformed into an equivalent acyclic PDA.

Your answer is correct.
Правильные ответы:
Deterministic PDA are NOT closed under union.,
The class of languages recognized by deterministic PDAs is closed under complement.,
Every PDA can be transformed into an equivalent acyclic PDA.

Вопрос 7
Верно
Баллов: 1,00 из 1,00

Match NTM with its description:

Выберите...

Выберите...

Выберите...

Выберите...

Your answer is correct.
Правильный ответ:

→ L = {ww | w ∈ {a,b}+},

→ L = {wwR | w ∈ {a,b}+}, where wR is the reversed string w ∧ w ends

with b and doesn't contain ‘aa’ substring,

→ L = {wwR | w ∈ {a,b}+}, where wR is the reversed string w,

→ L = {ww | w ∈ {a,b}+}, where w ends with b

Вопрос 8
Верно
Баллов: 1,00 из 1,00

How many states will be at least created after conversion of the following NFSA into DFSA?

Ответ:

Правильный ответ: 5

Вопрос 9
Верно
Баллов: 1,00 из 1,00

Suppose you apply Kleene’s algorithm on an FSA with states q0, q1, …, q5. The state q0 is initial, q3 and q5 are
accepting states. Which of the following part(s) belong(s) to the resulting Regular Expression union?
a. R60,5
b. R55,0
c. R63,0
d. R60,3
e. R50,3
f.

R50,5

g. R65,0
h. R53,0

Your answer is correct.
Правильные ответы:
R50,3,
R50,5

Вопрос 10
Верно
Баллов: 1,00 из 1,00

What is the primary purpose of Thompson's Construction Algorithm in automata theory?
a. To convert a NFSA into a regular expression
b. To convert a regular expression into a NFSA
c. To convert a regular grammar into a DFSA
d. To convert a DFSA into a regular expression

Your answer is correct.
Правильный ответ:
To convert a regular expression into a NFSA

Вопрос 11
Верно
Баллов: 1,00 из 1,00

Complete the following statement:
“Context-free grammars have played a central role in compiler technology since the 1960s. There is an
automaton-like notation, called the “

”, that also describes all and only the context-free

languages - John E. Hopcroft, Rajeev Motwani and Jeffrey D. Ullman”

Правильный ответ: pushdown automaton

Вопрос 12
Верно
Баллов: 1,00 из 1,00

Select all that apply for the given PDT over a language L:

a. This PDT is deterministic
b. L includes { a(n+1)b3n | n > 0 }
c. All of the above
d. All strings from L will be translated into strings with exactly 1 b
e. L includes { a(n+2)b4n | n > 0 }
f.

L includes { a(n+10)bn | n > 0 }

g. An input string aaabbbbbb will be translated into aab

Your answer is correct.
Правильные ответы:
L includes { a(n+1)b3n | n > 0 },
L includes { a(n+2)b4n | n > 0 },
All strings from L will be translated into strings with exactly 1 b,
An input string aaabbbbbb will be translated into aab

Вопрос 13
Верно
Баллов: 1,00 из 1,00

Let L = {a, ab}. Find L3
a. { aaa, aab, aba, abb, baa, bab, bba, bbb }
b. { aaa, aaab, aaba, aabab, abaa, abaab, ababa, ababab }
c. { aaa, ababab }
d. None of the above

Your answer is correct.
Правильный ответ:
{ aaa, aaab, aaba, aabab, abaa, abaab, ababa, ababab }

Вопрос 14
Верно
Баллов: 1,00 из 1,00

Give the most simplified regular expression that describes the language accepted by the following automata:

Ответ:

Правильный ответ: 1

Вопрос 15
Верно
Баллов: 1,00 из 1,00

Match table variables by states for the NFSA converted to DFSA:

Y

Выберите...

W

Выберите...

X

Выберите...

Z

Выберите...

Your answer is correct.
Правильный ответ:
Y → {q0,q1},
W → {q0},
X → {q0,q2},
Z → {q0,q3}

Вопрос 16
Верно
Баллов: 1,00 из 1,00

Which of the following is/are NOT a computational problem(s) solvable by a Turing machine?
a. Finding the largest element in a list of numbers
b. Halting Problem
c. Determining whether a given string is a palindrome
d. A brute-force search algorithm

Your answer is correct.
Правильный ответ:
Halting Problem

Вопрос 17
Верно
Баллов: 1,00 из 1,00

Select all that apply for the formal definition of a PDA < Q, ∑, Γ, δ, q0, Z0, F >
a. q0 ∈ ∑
b.
Z0 ∉ Γ

c.
F ⊆ Q

d.

∗

δ : Q × (Σ ∪ {ϵ}) × Γ → Q × Γ

Your answer is correct.
Правильные ответы:
F ⊆ Q

,
∗

δ : Q × (Σ ∪ {ϵ}) × Γ → Q × Γ

Вопрос 18
Верно
Баллов: 1,00 из 1,00

Which statements about FSA is/are FALSE?
a. FSA can recognize all the languages
b. There can be more than 1 initial state

c. Final states and accepting states have no intersection

d. The power of FSA is unlimited

e. Partial transition function may not define some transitions from all the states

Your answer is correct.
Правильные ответы:

The power of FSA is unlimited,

Final states and accepting states have no intersection,

There can be more than 1 initial state,
FSA can recognize all the languages

Вопрос 19
Верно
Баллов: 1,00 из 1,00

Apply Thompson’s Construction on the following regular expression: (a*|c). How many ε-transitions does the
resulting FSA have?
a. 4
b. 12
c. 2
d. 10
e. 14
f.

6

g. 8

Your answer is correct.
Правильный ответ:
8

Вопрос 20
Верно
Баллов: 1,00 из 1,00

A⊆B means that...
a. A and B have the same number of elements
b. Every element of B is an element of A
c. A = B
d. A and B have exactly the same elements
e. Every element of A is an element of B

Your answer is correct.
Правильный ответ:
Every element of A is an element of B

Вопрос 21
Верно
Баллов: 1,00 из 1,00

Which type(s) of grammar allow(s) a production rule with the form XY->XZ?
a. Unrestricted
b. Context-sensitive
c. Recursive
d. Context-free
e. Regular

Your answer is correct.
Правильные ответы:
Context-sensitive,
Unrestricted

Вопрос 22
Верно
Баллов: 1,00 из 1,00

Which of the following grammars does generate language L={a2nbn | n > 0}?
a. S -> bSaa | baa
b. S -> aaSb | ε
c. S -> aaSb | aab
d. S -> bSaa | ε

Your answer is correct.
Правильный ответ:
S -> aaSb | aab

Вопрос 23
Верно
Баллов: 1,00 из 1,00

are the most powerful formal grammars in the Chomsky hierarchy, capable of generating
recursively enumerable languages, reflecting the highest level of computational complexity.

Правильный ответ: Unrestricted grammars

Вопрос 24
Верно
Баллов: 1,00 из 1,00

W

(the rest is in the file)

## 2023: Midterm

Files: [TCS Midterm 2023.pdf](https://glebpopov.notion.site/a1306f8d89fc4d98a58035b3536a2d1b)


22.01.2024, 15:01

Midterm Exam.: Attempt review

Started on Wednesday, 15 March 2023, 12:52 PM
State Finished
Completed on

Wednesday, 15 March 2023, 1:32 PM

Time taken 40 mins
Grade

13.83 out of 20.00 (69.17%)

Question 1
Correct
Mark 1.00 out of 1.00

While applying Pumping lemma over a language, we consider a string w that belongs to L and fragment it into _________
parts.

a. 3
b. 5
c. 7
d. 9

Your answer is correct.
The correct answer is:
3

Question 2
Incorrect
Mark 0.00 out of 1.00

Which of the following statements about FST is/are TRUE?
a. It is an FSA with input and output tapes
b. The translation may happen only to the accepted strings
c. Input and output alphabets have to match 
d. Also called finite-state deceptor

Your answer is incorrect.
The correct answers are:
It is an FSA with input and output tapes,
The translation may happen only to the accepted strings



https://moodle.innopolis.university/mod/quiz/review.php?attempt=158773&cmid=91787

1/12

22.01.2024, 15:01

Midterm Exam.: Attempt review

Question 3
Partially correct
Mark 0.50 out of 1.00

Which of the following statements about FSA is/are TRUE?
a. An FSA with a total transition function is called complete
b. In complete FSA the number of transitions from each state matches the number of symbols in the alphabet



(assume no ε-moves)
c. Each complete FSA is also deterministic
d. The set of final states may be empty 
e. The sets of initial and accepting states may not intersect 

Your answer is partially correct.
You have selected too many options.
The correct answers are:
An FSA with a total transition function is called complete,
In complete FSA the number of transitions from each state matches the number of symbols in the alphabet (assume no εmoves)

Question 4
Correct
Mark 1.00 out of 1.00

What is a context-free language?
a. A language that can be spoken in any context
b. A language that has no grammar rules
c. A language for which you can apply Pumping Lemma
d. A language requiring an unbounded memory to be recognized

Your answer is correct.
The correct answer is:
A language requiring an unbounded memory to be recognized



https://moodle.innopolis.university/mod/quiz/review.php?attempt=158773&cmid=91787

2/12

22.01.2024, 15:01

Midterm Exam.: Attempt review

Question 5
Correct
Mark 1.00 out of 1.00

What is a regular language?
a. A formal language that can be defined by a regular expression
b. A formal language that can be recognized by a finite state machine
c. A formal language that can be generated by a regular grammar
d. All of the above

Your answer is correct.
The correct answer is:
All of the above

Question 6
Partially correct
Mark 0.33 out of 1.00

Which of the following languages require(s) unbounded memory to be recognized?
a. L = { anbn }
b. L = { an! }
c. L = { anbm |n ≠ m } 
d. L = { wcwR | w ∈ {a, b}∗ ∧ |w| > 0 }

Your answer is partially correct.
You have correctly selected 1.
The correct answers are:
L = { anbn },
L = { wcwR | w ∈ {a, b}∗ ∧ |w| > 0 },
L = { an! }



https://moodle.innopolis.university/mod/quiz/review.php?attempt=158773&cmid=91787

3/12

22.01.2024, 15:01

Midterm Exam.: Attempt review

Question 7
Correct
Mark 1.00 out of 1.00

Relate the following statement: All sufficiently long words in a regular language can have a middle section of words
repeated a number of times to produce a new word which also lies within the same language.
a. Pumping Lemma
b. Myhill–Nerode theorem
c. Rice Theorem
d. Halting Problem

Your answer is correct.
The correct answer is:
Pumping Lemma



https://moodle.innopolis.university/mod/quiz/review.php?attempt=158773&cmid=91787

4/12

22.01.2024, 15:01

Midterm Exam.: Attempt review

Question 8
Correct
Mark 1.00 out of 1.00

Match the FSAs with the languages that may be accepted by them (Σ = {0, 1})

L = {w ∈ Σ∗ | w contains the substring 1001}



L = {w ∈ Σ∗ | in w each 1 is preceded by double 0 ∧ w starts from 0}



L = {w ∈ Σ∗ | w does NOT contain the substring 1001}



L = {w ∈ Σ∗ | w starts from 0 ∧ w ends with 1 ∧ w does NOT contain substrings containing the same



Your answer is correct.
The correct answer is:
→ L = {w ∈ Σ∗ | w contains the substring 1001},

→ L = {w ∈ Σ∗ | in w each 1 is preceded by double 0 ∧ w starts from 0},

→ L = {w ∈ Σ∗ | w does NOT contain the substring 1001},

→ L = {w ∈ Σ∗ | w starts from 0 ∧ w ends with 1 ∧ w does NOT contain substrings

containing the same symbol with the length 2 ∧ |w| > 1}

https://moodle.innopolis.university/mod/quiz/review.php?attempt=158773&cmid=91787



5/12

22.01.2024, 15:01

Midterm Exam.: Attempt review

Question 9
Incorrect
Mark 0.00 out of 1.00

Which of the following languages with Σ = {a, b, c} suits the drawn FSA?

a. L = {w ∈ Σ∗ | the substring abc in w occurs an odd number of times}
b. L = {w ∈ Σ∗ | the substring abc in w occurs an even number of times}
c. L = {w ∈ Σ∗ | the substring abc in w occurs an even number of times ∧ |w| > 0} 
d. L = {w ∈ Σ∗ | the substring abc in w occurs an odd number of times ∧ |w| > 0}
e. None of the above

Your answer is incorrect.
The correct answer is:
None of the above

Question 10
Incorrect
Mark 0.00 out of 1.00

Pumping lemma for context free grammar is used for:
a. Proving certain languages are not context free
b. Proving language is infinite 
c. Proving certain languages are not context free and that language is infinite
d. None of the above

Your answer is incorrect.
The correct answer is:
Proving certain languages are not context free



https://moodle.innopolis.university/mod/quiz/review.php?attempt=158773&cmid=91787

6/12

22.01.2024, 15:01

Midterm Exam.: Attempt review

Question 11
Correct
Mark 1.00 out of 1.00

Which of the following languages suits the drawn PDA?

a. L = {wcwR | w ∈ {a, b}∗ & |w| > 0}
b. L = {wcwR | w ∈ {a, b}* & |w| ≥ 0}
c. L = {wcwR | w ∈ {a, b} & |w| > 0}
d. L = {wcwR | w ∈ {a, b}∗ & |w| = 0}

Your answer is correct.
The correct answer is: L = {wcwR | w ∈ {a, b}∗ & |w| > 0}



https://moodle.innopolis.university/mod/quiz/review.php?attempt=158773&cmid=91787

7/12

22.01.2024, 15:01

Midterm Exam.: Attempt review

Question 12
Correct
Mark 1.00 out of 1.00

Which of the following languages suits the drawn PDA?

a. L = {(01)n1 | n>0 & n is even}
b. L = {(01)n0 | n>0 & n is odd}
c.

L = {(01)n0 | n>0 & n is even}

d. L = {(01)n1 | n>0 & n is odd}

Your answer is correct.
The correct answer is:
L = {(01)n0 | n>0 & n is odd}

Question 13
Incorrect
Mark 0.00 out of 1.00

Which of the following languages is/are NOT regular?
a. an!
b. anbm 
c. anbn
d. L = {wcwR | w ∈ {a, b}∗ ∧ |w| > 0}

Your answer is incorrect.
The correct answers are:
anbn,
L = {wcwR | w ∈ {a, b}∗ ∧ |w| > 0},
an!



https://moodle.innopolis.university/mod/quiz/review.php?attempt=158773&cmid=91787

8/12

22.01.2024, 15:01

Midterm Exam.: Attempt review

Question 14
Correct
Mark 1.00 out of 1.00

Find the rule transitions X and Y such that the following PDA recognizes the language L= {0n1n+1 | n ∈ N}

a. X = “0, Z0/AZ0”, Y = “1, A/ϵ”
b. X = “0, Z0/AZ0”, Y = “1, A/A”
c. X = “0, Z0/Z0”, Y = “1, A/ϵ”
d. X = “0, Z0/Z0”, Y = “1, A/A”

Your answer is correct.
The correct answer is:
X = “0, Z0/AZ0”, Y = “1, A/A”

Question 15
Correct
Mark 1.00 out of 1.00

Which of the following one can relate to the following statement: if n items are put in m containers with n>m, the at least
one container will contain more than one item?
a. Myhill–Nerode theorem
b. None of the mentioned
c. Pumping Lemma
d. Pigeonhole principle

Your answer is correct.
The correct answers are:
Pumping Lemma,
Pigeonhole principle



https://moodle.innopolis.university/mod/quiz/review.php?attempt=158773&cmid=91787

9/12

22.01.2024, 15:01

Midterm Exam.: Attempt review

Question 16
Correct
Mark 1.00 out of 1.00

The following PDA recognizes L={aibjck | RULL}. Find “RULL”.

a. RULL = “ i + k = j ”
b. RULL = “ k + j = i ”
c. RULL = “ i + i = k ”
d. RULL = “ j + i = k ”

Your answer is correct.
The correct answer is:
RULL = “ j

(the rest is in the file)

## 2023: Pre Final

Files: [TCS Pre Final 2023.pdf](https://glebpopov.notion.site/ee9c65e41bc344309fc9191283cad4b0)


22.01.2024, 15:00

Pre-Final: Attempt review

Started on Wednesday, 3 May 2023, 1:11 PM
State Finished
Completed on

Wednesday, 3 May 2023, 1:33 PM

Time taken 22 mins 30 secs
Grade 9.00 out of 10.00 (90%)
Question 1
Correct
Mark 1.00 out of 1.00

What was the name of the mathematical model that Alan Turing created and which is now known as the
theoretical basis for modern computers?
a. Turing machines
b. Boolean algebra
c. Quantum computing
d. Game theory

Your answer is correct.
The correct answer is:
Turing machines

https://moodle.innopolis.university/mod/quiz/review.php?attempt=165627&cmid=93144

1/9

22.01.2024, 15:00

Pre-Final: Attempt review

Question 2
Correct
Mark 1.00 out of 1.00

Please consider the following proof of the undecidability of the Halting Problem:

Assume that there exists an algorithm H that can decide whether any Turing machine M halts on a given input.
We will use this assumption to construct a new Turing machine D that solves the halting problem.
Let's define D as follows:

D = "On input x:
1. Use the algorithm H to determine whether Turing machine M_x halts on input x.
2. If H says that M_x halts on input x, halt and accept.
Otherwise, loop forever."
Now, let's consider what happens when we run D on some input x:
- If H says that M_x halts on input x, then D will halt and accept.
- If H says that M_x does not halt on input x, then D will loop forever.
Therefore, D correctly solves the halting problem for any input x.

Is this proof valid?

a. No, the proof is wrong because a TM cannot loop being TMs closed under complement
b. Yes, the proof is correct and follows logically consistent steps
c. No, the proof is wrong because it assumes that the algorithm H exists, which we know is not true due 
to the undecidability of the halting problem. This is a circular argument and does not prove
anything
d. It depends on circumstances

Your answer is correct.
The correct answer is:
No, the proof is wrong because it assumes that the algorithm H exists, which we know is not true due to the
undecidability of the halting problem. This is a circular argument and does not prove anything

https://moodle.innopolis.university/mod/quiz/review.php?attempt=165627&cmid=93144

2/9

22.01.2024, 15:00

Pre-Final: Attempt review

Question 3
Correct
Mark 1.00 out of 1.00

How can you determine whether a given language is regular or not?
a. You can determine whether a language is regular or not by flipping a coin and seeing if it lands heads
or tails. If it lands heads, the language is regular, and if it lands tails, the language is not regular
b. To determine whether a language is regular or not, we can use the pumping lemma for regular
languages. If a language does not satisfy the conditions of the pumping lemma, then it is not



regular. If it does satisfy the conditions, then it may be regular, but further analysis is needed
c. You can determine whether a language is regular or not by counting the number of vowels in each
word. If the majority of words have an odd number of vowels, the language is regular. If the majority
have an even number of vowels, the language is not regular
d. One way to determine whether a language is regular or not is by counting the number of characters in
each string and comparing it to a predetermined threshold. If the number of characters exceeds the
threshold, then the language is not regular. This method is reliable and always produces accurate
results

Your answer is correct.
The correct answer is:
To determine whether a language is regular or not, we can use the pumping lemma for regular languages. If a
language does not satisfy the conditions of the pumping lemma, then it is not regular. If it does satisfy the
conditions, then it may be regular, but further analysis is needed

https://moodle.innopolis.university/mod/quiz/review.php?attempt=165627&cmid=93144

3/9

22.01.2024, 15:00

Pre-Final: Attempt review

Question 4
Correct
Mark 1.00 out of 1.00

Why is the alphabet in FSA finite?
a. The alphabet in FSA is finite because it is based on the limitations of human cognition and perception.
Our brains can only process a limited amount of information at a time, and so the alphabet must be
limited to a manageable number of symbols that we can recognize and remember
b. No, the alphabet in FSA is infinite because it includes all the possible letters and symbols that can be
used in any language or communication system. In fact, the more letters and symbols there are, the
better the FSA will be at recognizing patterns and sequences
c. The alphabet in FSA is finite because it is a conspiracy by the world's linguists to limit the number of
letters and symbols that people can use in their languages. This is done to maintain the power of the
linguistic elite and prevent the common people from expressing themselves fully. The linguists secretly
meet in underground bunkers to decide which letters and symbols to include in the alphabet, and
they use mind control techniques to force people to accept their decisions. The fewer letters and
symbols there are, the easier it is for the linguists to control people's thoughts and actions

d. The FSA has transitions from one state to another based on the current input symbol, and since it
can only recognize a finite set of symbols, the alphabet must also be finite. If the alphabet were
infinite, the FSA would not be able to operate on all possible input symbols, making it an impractical
model for pattern recognition

Your answer is correct.
The correct answer is:
The FSA has transitions from one state to another based on the current input symbol, and since it can only
recognize a finite set of symbols, the alphabet must also be finite. If the alphabet were infinite, the FSA would
not be able to operate on all possible input symbols, making it an impractical model for pattern recognition

Question 5
Incorrect
Mark 0.00 out of 1.00

Which of the following string(s) is/are NOT matched by the regular expression (B(AB|A)*D)*?
a. ε 
b. BAADBAABBDBAD
c. BABD 
d. BADABBA
e. BD 
f.

BAADBAABDBAD 

Your answer is incorrect.
The correct answers are:
BADABBA,
BAADBAABBDBAD

https://moodle.innopolis.university/mod/quiz/review.php?attempt=165627&cmid=93144

4/9

22.01.2024, 15:00

Pre-Final: Attempt review

Question 6
Correct
Mark 1.00 out of 1.00

Which of the following languages over the Σ = {a, b} fully describes the represented FSA?

a. L = {x ∈ Σ* | x does not end with aa}
b. L = {x ∈ Σ* | every a in x (if there are any) is followed immediately by bb}
c. L = {x ∈ Σ* | x accepts only strings with b's}
d. L = {x ∈ Σ* | x does not end with a}

Your answer is correct.
The correct answer is:
L = {x ∈ Σ* | every a in x (if there are any) is followed immediately by bb}

https://moodle.innopolis.university/mod/quiz/review.php?attempt=165627&cmid=93144

5/9

22.01.2024, 15:00

Pre-Final: Attempt review

Question 7
Correct
Mark 1.00 out of 1.00

Which of the following languages suits the drawn PDA?

a. L = {(01)n1 | n>0 & n is odd}
b. L = {(01)n0 | n>0 & n is odd}
c. L = {(01)n1 | n>0 & n is even}
d. L = {(01)n0 | n>0 & n is even}

Your answer is correct.
The correct answer is:
L = {(01)n0 | n>0 & n is odd}

https://moodle.innopolis.university/mod/quiz/review.php?attempt=165627&cmid=93144

6/9

22.01.2024, 15:00

Pre-Final: Attempt review

Question 8
Correct
Mark 1.00 out of 1.00

Which of the following FSAs could have been used for receiving the next Regular Expressions in the k=-1 step of
Kleene’s Algorithm?

a.

b.

c.

d. All of the above

https://moodle.innopolis.university/mod/quiz/review.php?attempt=165627&cmid=93144

7/9

22.01.2024, 15:00

Pre-Final: Attempt review

e. None of the above

Your answer is correct.
The correct answer is:
All of the above

Question 9
Correct
Mark 1.00 out of 1.00

What is Theoretical Computer Science?

a. Theoretical Computer Science is a type of computer game that involves solving puzzles and
challenges
b. Theoretical Computer Science is a branch of com

(the rest is in the file)

## 2022: Midterm

Files: [TCS Midterm 2022.pdf](https://glebpopov.notion.site/9a2d7a780c074eaf9e7d3dfefa4847f3)


Name CIOIRIRIE|cI] [LlolL|ulTTiTolIN
Group

Course Name: Theoretical Computer Science Year: 2021-2022 (Spring Semester)

Midterm exam '«ﬂ Time allowed: 80 minutes
Instructor: Manuel Mazzara ‘

Max grade: 20 points
ropolis
ONiversity

Task 1 (4 points). Construct in a graphical form a DFSA which corresponds to M; U Mp:

(NDFSA solutions will get 0 points)

Name CORPRECT SOLUTYON

Group |

Task 2 (3 points). Complete the Pumping Lemma (multiple options are correct in (3)):

Let L be a regular language. Then Cl) integer m > 1 such that (2)
string w in L of length at least m can be written as w = xyz, satisfying the following conditions:
3)
(I@there exists
b) for every
(2) a) there exists

every

G a)ly=0

® =1

c) |xyz| <m
@yl <m
€)3i>0xyize¢ L
HVi>0xyizgL
g 3i>0xyiz€L
@ViEOxyizeL

Task 3 (2 points). Construct a complement of M1 over the alphabet {0, 1}:

oA

Name

COoRRECT S OLUT I ON

Group

Task 4 (4 points). Construct a complete DFSA over the alphabet {0,1} that accepts the
words including a substring 00101.

Task 5 (1 point). Which of the following statements are true about PDA:
a) It has an external memory with an initial start symbol
b) It has an external memory that follows First in First Out Policy (FIFO)
g It can manipulate the external memory as part of performing a transition
d

) It uses the external memory to decide which transition has to be made

(©) It can be used for parsing programming languages
@ Regular languages are recognized by PDAs

Task 6 (1 point). Is L = {a™b"| n > 0,m > 0} a regular language?

a) Yes, which can be proved using pumping lemma
@ Yes, but we cannot prove it using pumping lemma
¢) No, but we cannot prove it using pumping lemma

d) No, which can be proved using pumping lemma

Name CORRECT SO L UT Il ON

Group

Task 7 (5 points). Solve ONE of the exercises:

a) Construct a DPDA that recognizes the language:
L={a™p"cPd(mn, p, ¢ 2 1) A(m+q =n+p))

b,® /66 B/od
o, AJAA b2 /P2, gi%;bzo
a2e/A2, bA/s CAs dbjs

‘ , | <. 2%/P2, ;

b) Construct a DPDA that recognizes the language:
L={a™b"a™|(m=0) A (n=0)}

## 2021: Final

Files: [TCS Final 2021.pdf](https://glebpopov.notion.site/8921fef44f4f46a1b94fc4152e981156)


Name
Group
Course Name: Theoretical Computer Science
Final exam
Instructor: Manuel Mazzara

Year: 2020-2021 (Spring Semester)
Time allowed: 90 minutes
Max grade: 25 points

LAPTOPS ARE NOT ALLOWED, BOOKS MUST BE CLOSED!
Please, write your solutions in the provided space. You may use the reverse side for drafts.

EXERCISE 1 (5 points)
Construct pushdown automaton that recognizes the following language:

𝐿 = {𝑎𝑖 𝑏 𝑗 𝑐 𝑘 | 𝑖, 𝑗, 𝑘 ≥ 0, 𝑎𝑛𝑑 𝑖 + 𝑗 = 𝑘 𝑜𝑟 𝑖 = 𝑘}
EXERCISE 2 (5 points)
Construct a deterministic 2-tape (1 Input, 1 Memory) Turing machine over Σ = {a, b}:

𝐿 = {𝑎2𝑛 𝑏𝑛 |𝑛 ≥ 0} ∪ {𝑎𝑛 𝑏2𝑛 |𝑛 ≥ 0}
EXERCISE 3 (5 points)
A. List the types of grammars of Chomsky hierarchy. What are the automata that correspond to these
grammar types? (1 points)
B. Let L be the language over Σ = {a, b} denoted by the regular expression 𝑎(𝑎|𝑏)∗. Is it possible to
express this language with a CFG? If yes, provide the grammar, if no, provide the explanation. (2 points)
C. What is the type of the least expressive grammar in the Chomsky hierarchy that could define the given
language? Provide the grammar that defines this language (2 points)

𝐿 = {𝑎𝑖 𝑏 𝑗 𝑐 𝑘 | 𝑖, 𝑗, 𝑘 ≥ 0, 𝑎𝑛𝑑 𝑖 = 𝑗 𝑜𝑟 𝑖 = 𝑘}
EXERCISE 4 (5 points)
Are two-tape Turing Machines more expressive than the one-tape Turing Machines? Explain.

EXERCISE 5 (5 points)
A decision problem (posed as a yes-no question) which can be solved by an algorithm is called decidable.
Consider the following problems and state for each of them whether it is decidable or not. Explain. (5 points)
A. Writing a static analyser that, for any given input pair consisting of (program, input) can decide whether
the program gives an output with the specific input.
B. Writing a program that for a given regular expression has to decide whether the complement of the
language of the given RegExp is regular.
C. Writing a program that for a given triple of integers has to decide whether the third integer is a greatest
common divisor of the first two integers.

## 2021: Midterm

Files: [TCS Midterm 2021 (paper part).pdf, TCS Midterm 2021 (moodle part).pdf](https://glebpopov.notion.site/17fc40f2721d4572a4bc3762acb26fc3)

### TCS Midterm 2021 (paper part).pdf
Name
Group
Course Name: Theoretical Computer Science
Midterm exam: paper-based part
Instructor: Manuel Mazzara

Year: 2020-2021 (Spring Semester)
Time allowed: 20 minutes
Max grade: 15 points

Exam Instructions
1. The exam consists of 3 parts:
1) Paper – based (15 points) - 20 minutes + 5 min for submission
2) Moodle test (10 points) – 10 minutes
3) JFLAP implementation – 20 minutes.
2. During the paper-based part you will have to construct several FSAs on a paper in the provided space. Use of
any device is prohibited at this stage. Further you will have to take a picture of your solution and submit it to
Moodle in a single .pdf file (you have 5 mins for the submission process). Afterwards you leave the paper with
the solution on the edge of the desk (it will be collected by the exam proctors).
Make sure to sign all your papers (name, last name and your group)
3. During the Moodle-based part you will have to answer several theoretical multiple-choice questions. Use of
any applications, apart from Moodle, is prohibited at this stage.
4. During the JFLAP implementation you will have to implement in JFLAP7.1 the solutions that you submitted
in pdf in the paper-based stage. The implemented solutions should be exactly the same as in the submitted
paper version (if the difference is detected, the task will be evaluated to 0). Please follow the naming pattern and
submit 3 separate files in *.jff format (no archives etc.)
5. You are not allowed to go to leave the room during the exam.

Name
Group
Consider an FSA M1 over the alphabet {0, 1}:

Task 1 (5 points). Construct a complement of M1

Task 2 (5 points). Construct a complete FSA M2 over the alphabet {0,1} that accepts the
strings ending with 01. The FSA should have not more than 3 states.

Task 3 (5 points). Construct an intersection of M1 and M2

### TCS Midterm 2021 (moodle part).pdf
22/02/2024, 08:37 Midterm submission 2 ('Moodle Test": Tasks 4-6): Attempt review

Started on Thursday, 4 March 2021, 10:16 AM
State Finished
Completed on Thursday, 4 March 2021, 10:30 AM
Time taken 13 mins 7 secs
Grade 9.0 out of 10.0 (90%)

Question 1
Complete

Mark 6.0 out of 6.0

[multiple choice question, +1 point for each correct answer -1 for each incorrect answer, minimum 0 points
total]

Which of the following statements are frue about PDA:

1. It has an external memory with an initial start symbol

2. It has an external memory that follows First in First Out Policy (FIFO)

3. It can manipulate the external memory as part of performing a transition
4. It uses the external memory to decide which transition has to be made
5. It can be used for parsing programming languages

6. Regular languages are not recognized by PDA’s

https://moodle.innopolis.university/mod/quiz/review.php?attempt=65075&cmid=60787 12

22/02/2024, 08:37 Midterm submission 2 ('Moodle Test": Tasks 4-6): Attempt review
Question 2
Complete

Mark 3.0 out of 3.0

[multiple choice question, +1 point for each correct answer -1 for each incorrect answer, minimum 0 points
total]

Mark the conditions needed to complete the Pumping lemma:

Let L be aregular language. Then there exists an integer m 2 1 such that every string w in L of length at least m
can be written as w = xyz, satisfying the following conditions:

1. |xy|<m
2. |yl 21
3. |yl 20

4. |xyz|<m
5 Vi20xyzel
6. 3i20xy'zel

7. 3i20xy'z¢l

Viz0xy'z¢l

Question 3
Complete

Mark 0.0 out of 1.0

IsL ={a" | nis even} aregularlanguage?

1. Yes, which can be proved using pumping lemma
2. No, which can be proved using pumping lemma
3. Yes, but we cannot prove it using pumping lemma

4. No, but we cannot prove it using pumping lemma

https://moodle.innopolis.university/mod/quiz/review.php?attempt=65075&cmid=60787 2/2

## 2020: Midterm

Files: [TCS Midterm 2020.pdf](https://glebpopov.notion.site/ac642fa6286444f0844ba137fa8f75ba)


Name
Group
Institute of Software Development and Engineering
Course Name: Theoretical Computer Science
Course Code: TCS
Instructor: Manuel Mazzara

Year: 2019-2020 (Spring Semester)
Midterm

Time allowed: 50 minutes
Marks: 100 points

Exam Instructions

Инструкция к экзамену

1. This is a closed book exam.
2. Use of any device is forbidden.
3. Fill in every page your identifying information
in English block letters. You must do it at the
beginning of the exam.
4. Answer all questions, following the same order
and in the provided space.
5. Use ballpoint or fountain pens with black or blue
ink.
6. If students are caught communicating during the
exam, they will be expelled from the exam hall
and will receive Fail grade.
7. Please note that the questions are related to the
material as presented in the course.

1. Экзамен
не
допускает
использования
вспомогательных материалов (печатных или
электронных).
2. Запрещено использование любых электронных
устройств.
3. На каждой странице укажите свои имя, фамилию,
группу и персональный идентификатор студента
печатными латинскими буквами. Сделайте это
перед тем как приступить к решению задач
экзамена.
4. Ответьте на все вопросы, сохраняя порядок их
следования, а также не выходя за пределы
отведенной для ответа области на бумаге.
5. Используйте шариковые или гелевые ручки с
синими или черными чернилами.
6. Общение во время экзамена с другими
студентами повлечет удаление с экзамена и
автоматическое присвоение оценки Fail.
7. Вопросы касаются материала, представленного в
лекциях и на практических занятиях

Part #1

40

Part #2

28

Part #3

32

1

Part #1 GENERAL CONCEPTS – 40 Points (2 points each)
One or more answers can be marked. The question will be considered correct only when all the right answers are
marked.
NOTE: Only answers written in the answer table (see page 4) will be considered for grading.
1) Which statement about the expressive power of different computational models is true?
a) FSA ⊂ NPDA ⊂ DPDA ⊂ TM
b) FSA ⊂ DPDA ⊂ NPDA ⊂ TM
c) NPDA ⊂ DPDA ⊂ FSA ⊂ TM
d) NPDA ⊂ FSA ⊂ DPDA ⊂ TM
e) TM ⊂ NDPA ⊂ DPDA ⊂ FSA
2) Choose true statements:
a) {𝜖}=∅
b) {∅}=∅

c) Both: a and b
d) None of the mentioned

3) Which of the following languages is regular?
a) {𝑎𝑖 𝑏 𝑖 | 𝑖 ≥ 0}
b) {𝑎𝑖 𝑏 𝑖 | 0 < 𝑖 < 5}

c) {𝑎𝑖 𝑏 𝑖 | 𝑖 ≥ 1}
d) None of the mentione

4) Given that a string x is accepted by an FSA M, which of the following statements is true:
a) any string containing substring x can be accepted by M
b) all final states were visited at least once while x is read
c) a final state is reached when the string x is read completely
d) M is complete
5) Given a PDA M=<Q, I, Γ, δ, q0, Z0, F> which of the following conditions makes it non-deterministic?
a) For every q ∈ Q, every x ∈ I ∪ {ɛ}, and every γ ∈ Γ, the set δ(q, x, γ) has at most one element
b) For every q ∈ Q, every x ∈ I, and every γ ∈ Γ, the sets δ(q, x, γ) and δ(q, ɛ, γ) are both empty
c) For some q ∈ Q, every x ∈ I, and every γ ∈ Γ, the sets δ(q, x, γ) and δ(q, ɛ, γ) are both non-empty
d) For some q ∈ Q, every x, y ∈ I, where x≠y and every γ ∈ Γ, the sets δ(q, x, γ) and δ(q, y, γ) are both nonempty
6) Are FSA able to recognize palindromes?
a) Yes, they are because palindromes are a paradigmatic example of regular languages
b) Yes, they are because they can memorize the midpoint using states
c) No, they cannot since FSA cannot deterministically find the midpoint
d) No, they cannot because the memory model is not powerful enough
7) Relate the following statement:
“All sufficiently long words in a regular language can have a middle section of words repeated a number of
times to produce a new word which also lies within the same language”
a) Turing Machine
b) Pumping Lemma
c) Arden’s theorem
d) None of the mentioned

2

Name
Group
8) While applying Pumping lemma to a string x of a language L, we need x = ywz to satisfy following conditions
(where p – critical length):
a) |yw|≤ p
b) |yw|≥p
c) |x|≤p
d) |x|≥p
e) |w|≥p
f) |w|≥1
9) Choose computation model(s) for which termination is undecidable?
a) DPDA
b) NDPDA
c) FSA
d) TM
10) Choose true statement about operations on the set of regular languages:
a) It is closed only by intersection
b) It is closed only by union
c) It is closed only by complement
d) It is closed by any of these operations
11) Let L1 be a language recognized by M1; L2 - by M2. Which of the following languages is L1 ∪ L2?

a)
b)
c)
d)

Ø
{ɛ}
{0, 1}*
{0, 1}*\{ɛ}

12) Given complete FSA’s M1 and M2. Which of the following FSA’s is M1 ∩ M2?

a.

b.

c.

3

d.

13) Given complete FSA’s M1 and M2. Which of the following languages is recognized by M1\ M2?

a)
b)
c)
d)

{0, 01, 010, ...}
{1, 101, 1010, ...}
{1}*\{ɛ}
Ø

14) Which of the following strings is accepted by the PDA?

a)
b)
c)
d)
e)
f)
g)

baaccc
aabbcc
ababcc
aabbccc
aababccc
aabbbccc
None of the mentioned

Consider the below Problem statement and answer for question 15-20. For each of following languages choose the
least powerful automata that can recognize it, where:
a) DPDA

b)NDPDA

15) {anbn |n ∈ N}
16) {anbn |n = 7}*
17) {anbncn|n ∈ 𝑁}
18) {anbmambn|n, m ∈ 𝑁}
19) {anbmambn|n = 7,m ∈ 𝑁}
20) {anbn ∪ anb2n|n ∈ 𝑁}

c) FSA

d) TM

- _______
- _______
- _______
- _______
- _______
- _______

Answer table:
Question
Answer
Question
Answer

1

2

3

4

5

6

7

8

9

10

11

12

13

14

15

16

17

18

19

20

NOTE: Only answers written in the answer table will be considered for grading.
4

Name
Group
Part #2 FSA – 28 Points
a) Please consider the following FSAs and add missing transitions and labels (21 points)
Let 𝛴 = {0, 1}. Add missing labels and transitions, and mark the start and final states to construct FSAs, which
accept the following languages:
1) 𝐿 = {𝑥 ∊ 𝛴 ∗ | 𝑥 contains the substring 1010}

2) 𝐿 = {𝑥 ∊ 𝛴 ∗ | 𝑥 is a binary representation of an integer divisible by 4}

3) 𝐿 = {𝑥 ∊ 𝛴 ∗ | 𝑥 starts with 0 and has odd length, or starts with 1 and has even length}

5

b) Consider the following automata operating on the binary digit alphabet (7 points)

Please determine whether the following statements are true or false (write TRUE or FALSE next to the
statement).
______ 1)

Automaton M1 recognizes all binary strings with at least one 0

______ 2)

Automaton M2 is complete

______ 3)

Automaton M2 recognizes all binary strings with at most one 0

______ 4)

Automaton M2 is not complete

______ 5)

Automaton M2 is the complement of Automaton number 1

______ 6)

Automaton M3 recognizes all binary strings starting and ending with 0 (and single-0 string does count)

______ 7)

Automaton M3 has a trap state

6

Name
Group
Part #3 PUSHDOWN AUTOMATA – 32 Points (16 Points each)
Please consider the following PDAs and add missing labels
a) Complete the following DPDA that recognises the following language:
𝐿 = {𝑎𝑚 𝑏𝑛 𝑐 𝑝 𝑑𝑞 | (𝑚, 𝑛, 𝑝, 𝑞 ≥ 1) ⋀ (𝑚 + 𝑝 = 𝑛 + 𝑞)}

7

b) Complete the following DPDA which recognizes the language of well-formed parentheses of the arithmetic
expressions (binary operations). Along with regular parentheses ’(’ and ’)’, there is also available bracket ’]’,
which has the effect of closing all open parentheses upto that point.
Consider the following alphabet 𝑰 = {𝒂, (, ), ], +}
Note: In the PDA the first parenthesis is "remembered" by the character ′𝐵′, whereas the subsequent ones
cause writing an ′𝐴′ on the stack.

8

# Citations

1. [IU B23 Academic Materials: Past Papers [EN programs]](https://glebpopov.notion.site/4ef3de0c7e68495b89ef086301361603)
