---
type: page
title: "Past exam papers: Databases"
description: "Past exams and tests of Databases at Innopolis University (6 papers, 2021–2025), collected by students: tasks, formats, points."
resource: "https://glebpopov.notion.site/4ef3de0c7e68495b89ef086301361603"
tags: ["past-papers", "exams", "bachelor", "databases"]
audience: ["student"]
source_kind: community
language: en
section: "notion/past-papers"
subject: "Databases"
sources:
  - resource: "https://glebpopov.notion.site/4ef3de0c7e68495b89ef086301361603"
    title: "IU B23 Academic Materials: Past Papers [EN programs]"
generated:
  by: "catix-wiki/0.1 past-papers (code only, no model)"
status: draft
---

# Past exam papers: Databases

Exams and tests of **Databases** from previous years, as the students collected them in [IU B23 Academic Materials: Past Papers [EN programs]](https://glebpopov.notion.site/4ef3de0c7e68495b89ef086301361603). Not an official source: a paper may be one variant of several, or written down from memory. Newest first.

## 2025: Midterm

Files: [Databases Midterm 2025.pdf](https://glebpopov.notion.site/1ade746cceef80a2b3ccfcfb88e82f95)


Databases Midterm Exam
March 5, 2025
Innopolis University

Database Schema A
CREATE TABLE Department (
departmentName VARCHAR(50),
budget INTEGER,
PRIMARY KEY (departmentName)
);
CREATE TABLE Location (
locationId VARCHAR(3),
city VARCHAR(10),
country VARCHAR (10),
PRIMARY KEY (locationId)
);
CREATE TABLE Employee (
employeeId INTEGER,
name VARCHAR(30),
jobTitle VARCHAR(15),
departmentName VARCHAR (50)
NOT NULL,
PRIMARY KEY (employeeId),
FOREIGN KEY (departmentName)
REFERENCES Department
);
CREATE TABLE Project (
projectCode VARCHAR(5),
projectType VARCHAR(10),
teamSize INTEGER,
PRIMARY KEY (projectCode)
);
CREATE TABLE Resource (
resourceId INTEGER,
resourceName VARCHAR(50),
locationId VARCHAR(3),
PRIMARY KEY(resourceId),
FOREIGN KEY (locationId)
REFERENCES Location
);
CREATE TABLE Assignment (
assignmentId INTEGER,
startDate TIMESTAMP,
endDate TIMESTAMP,
PRIMARY KEY (assignmentId)
);
CREATE TABLE Skill (
skillId INTEGER,
skillName VARCHAR(20),
PRIMARY KEY (skillId)
);

CREATE TABLE​
ResourceAllocation (
resourceId INTEGER,
projectCode VARCHAR(5),
assignmentId INTEGER,
allocationPercentage INTEGER,
PRIMARY KEY (resourceId,
projectCode, assignmentId),
FOREIGN KEY (resourceId)
REFERENCES Resource,
FOREIGN KEY (projectCode)
REFERENCES Project,
FOREIGN KEY (assignmentId)
REFERENCES Assignment
);
CREATE TABLE ProjectLocation (
projectCode VARCHAR(5),
locationId VARCHAR(3),
PRIMARY KEY (projectCode,
locationId),
FOREIGN KEY (projectCode)
REFERENCES Project,
FOREIGN KEY (locationId)
REFERENCES Location
);
CREATE TABLE WorksOn (
employeeId INTEGER,
projectCode VARCHAR(5),
assignmentId INTEGER,
hoursWorked INTEGER,
PRIMARY KEY (employeeId,
projectCode, assignmentId),
FOREIGN KEY (employeeId)
REFERENCES Employee,
FOREIGN KEY (projectCode)
REFERENCES Project,
FOREIGN KEY (assignmentId)
REFERENCES Assignment
);
CREATE TABLE TaskAssignment (
employeeId INTEGER,
taskId INTEGER,
assignmentId INTEGER,
role VARCHAR(20),
PRIMARY KEY (employeeId,
taskId, assignmentId),
FOREIGN KEY (employeeId)
REFERENCES Employee,
FOREIGN KEY (taskId)
REFERENCES Task,
FOREIGN KEY (assignmentId)
REFERENCES Assignment
);

CREATE TABLE EmployeeSkill (
employeeId INTEGER,
skillId INTEGER,
proficiencyLevel VARCHAR(10),
PRIMARY KEY (employeeId,
skillId),
FOREIGN KEY (employeeId)
REFERENCES Employee,
FOREIGN KEY (skillId)
REFERENCES Skill
);
CREATE TABLE Task (
taskId INTEGER,
taskDescription VARCHAR(100),
projectCode VARCHAR(5),
PRIMARY KEY (taskId),
FOREIGN KEY (projectCode)
REFERENCES Project
);
CREATE TABLE Manager (
employeeId INTEGER,
bonus DECIMAL (10, 2), -Additional attribute specific to
Managers
PRIMARY KEY (employeeId),
FOREIGN KEY (employeeId)
REFERENCES Employee (employeeId)
);
CREATE TABLE Engineer (
employeeId INTEGER,
specialization VARCHAR(50),
-- Additional attribute specific
to Engineers
PRIMARY KEY (employeeId),
FOREIGN KEY (employeeId)
REFERENCES Employee (employeeId)
);
CREATE TABLE SoftwareEngineer (
employeeId INTEGER,
programmingLanguage
VARCHAR(20), -- Additional
attribute specific to Software
Engineers
PRIMARY KEY (employeeId),
FOREIGN KEY (employeeId)
REFERENCES Engineer (employeeId)
);

Task 1. 3 points.
Part 1. ER diagram
Draw ER diagram using Chen notation according to the Database Schema A. You are
NOT required to include attributes to your diagram [3 pts]

Part 2. Queries
a.​ Write an SQL query to find employees who worked on project with a team size
greater than 5 [2 pts]

b.​ Describe the following SQL queries in a human-friendly way [4 pts]
SELECT e.employeeId, e.name
FROM Employee e
WHERE EXISTS (
SELECT 1
FROM ResourceAllocation ra
WHERE ra.resourceId = e.employeeId​
AND ra.allocationPercentage > 50
);
SELECT e.employeeId, e.name
FROM Employee e
WHERE EXISTS (
SELECT 1 FROM WorksOn w
JOIN ProjectLocation pl ON w.projectCode =
pl.projectCode
JOIN Location l ON pl.locationId = l.locationId
WHERE w.employeeId = e.employeeId​
AND l.country = 'USA'
)
AND EXISTS (
SELECT 1
FROM EmployeeSkill es
WHERE es.employeeId = e.employeeId​
AND es.skillId = (
SELECT skillId FROM Skill​
WHERE skillName = 'Java'
)
);

Task 2. 8 points.
Part 1. True or False [5 pts]
a. Database Schema A does not allow a software engineer to be a manager.

T

F

b. In Database Schema A, the ResourceAllocation table ensures that a
resource can only be allocated to one project at a time.

T

F

c. When we map multivalued attributes from an ER model to a Relational
model, we store the values of the multivalued attribute in a single column
separated by commas.

T

F

d. In the ER model, weak relationships are used to connect two weak
entities.

T

F

e. When mapping an ER model to Relational model, One-to-One and
One-to-Many relationships can be mapped using a foreign key, while
Many-to-Many relationships require an additional table.

T

F

Part 2. Queries [3 pts]
a.​ Write an SQL query to update the projectType column to “Group project” for all
projects where the projectCode starts with “GP” and the teamSize is greater
than or equal to 3 [1 pt]

b.​ Write an SQL query to delete all employees whose name has “b” as the second
letter and who belong to a department with a budget lower than 2000 [2 pts]

Task 3. 8 points.
a.​ Write an SQL query to find the total number of projects which were located in
“Russia” and the city name starts with one of the following letters: “M”, “N’, or “K”
[2 pts]​
​
​
​
​
​
​
​
b.​ Write an SQL query to list projectCode of all projects that employees with the
name equal to <your name> work on [3 pts]
​
​
​
​
​
​
​
​
c.​ Write an SQL query to list name of the departments whose budget is greater than
the average budget of all departments, sort them by budget (from higher to
lower), and if two or more departments have the same budget, sort them by name
of the department [3 pts]

Task 4. 7 points.
Consider the following Relational Schema:
Students (sid: integer, sname: string, age: integer, major: string)
Enrollments (sid: integer, cid: integer, grade: real)
Courses (cid: integer, cname: string, credits: integer, instructor: string)
Convert the following SQL query into Relational Algebra notation:
SELECT S.sname
FROM Students S
JOIN Enrollments E ON S.sid = E.sid
JOIN Courses C ON E.cid = C.cid
WHERE C.cname = 'Database Systems' AND E.grade > 3.0
Step-by-step Solution. Specify the sequence of operations used and Relational Algebra
form of it.

Final Answer. Write the final answer in Relational Algebra format.

Task 5. 8 points.
You are given the following database table:
EmpId

EmpName

Address

Dept

Skills

ProjId

ProjName

MgrName

MgrOffice

Rating

201

John

12A

IT

Python, Java

P101

Web App Dev

Mr. Wilson

M301

87

202

Lisa

34B

AI

Python, C++

P202

AI Research

Dr. Adams

M102

98

203

Mike

34C

Design

Figma, Sketch

P303

UI/UX Design

Mr. Leo

M205

78

204

Sarah

54C

IT

Java, Kotlin

P404

Software Dev

Dr. Brown

M401

85

205

Alex

75D

Finance

Excel, SQL

P505

Data Analysis

Prof. Clark

M207

92

206

Robert

38E

IT

C++, Rust

P101

Web App Dev

Mr. Wilson

M301

89

207

Emma

71F

AI

Python, R

P202

AI Research

Dr. Adams

M102

95

208

Daniel

33G

Design

Photoshop,
Illustrator

P303

UI/UX Design

Mr. Leo

M205

86

209

Olivia

43M

IT

Java, Swift

P404

Software Dev

Dr. Brown

M401

89

210

Jake

88A

Finance

Python, Excel

P505

Data Analysis

Prof. Clark

M207

76

Normalize the given table to the 3NF step by step (Original → 1NF → 2NF → 3NF) by
designing a set of relations. In each stage you need to list only tables that are changed.
If a table isn’t changed in particular stage, you don’t need to mention it.
For each relation you should provive:
a)​ The list of attributes, underlining the primary key(s)
b)​ Foreign key relationship (if any)
Answer Example:
Table1 (col-1-name, col-2-name, col-3-name…)
Foreign keys:
col-x-name references Table2(col-y-name)​
…

1.​ First Normal Form [2 pts]​
​
​
​
​
​
​
​
​
​
​
​
2.​ Second Normal Form [3 pts]​
​
​
​
​
​
​
​
​
​
​
​
3.​ Third Normal Form [3 pts]

## 2024: Final

Files: [Databases Final 2024.pdf](https://glebpopov.notion.site/904f62776a2f4d878c0d0a2f7d018e78)


Innopolis University
Final Exam
Databases S24

Date: May 6, 2024

Duration: 90 minutes

Total Marks: 40

Instructions
• Do not open the question paper until instructed.
• Make sure to write your full name and group on every page.
• The use of external materials, electronic devices, and communication during the exam is
prohibited. Any violation of this rule will result in a grade of 0 (zero) for the exam.
• Each question should be answered on paper assigned for this question.
• Write your answers clearly and concisely.

Good luck!

Full Name:

Group:

Task 1. SQL & Relational Algebra [7 points]
We have a hospital database that contains information about their doctors, the medicine they
have at hand, and information about the patients they treat represented by the following schema:
Patients (SSN, Name, Address, City, BirthDate)
Doctors (DoctorID, Name, Speciality, Salary)
Medicine (MedicineName, Description, Main-Ingredient)
Prescription (DoctorID*, SSN*, MedicineName*, Date, Description, Cost)
Note: Bold and underlined text represents primary keys, while asterisk symbol (*) represents foreign keys.

Part A [4 points]:
Write SQL queries for the following statements:

1. Retrieve the number of doctors in the hospital for each speciality. Your output should
have two columns: speciality and number of doctors with this speciality.

2. Retrieve names of all doctors who have not given any prescriptions (had 0 consultations).

3. Retrieve the names of all doctors who have salaries lower than the average.

1

Full Name:

Group:

4. Retrieve the number of consultations for each speciality (each consultation should result
in a final prescription). Your output should have two columns: speciality and number
consultations for this speciality.

Part B [3 points]:
Write Relational Algebra expressions for the following statements:

1. Retrieve the name and description for all medicines that have penicillin as a main ingredient and have been prescribed by a doctor with DoctorID = 234.

2. Retrieve name, date, description, and cost for all prescriptions which doctor John has
written to a patient with SSN = 1234.

3. Retrieve the list of doctors specializing in cardiology who have prescribed medicine more
expensive than 100 rubles. Your output should have four columns: doctor name, speciality,
medicine name, and prescription cost.

2

Full Name:

Group:

Task 2. Functions & Procedures [7 points]

In this task, you need to consider the following relation called company.

id

name

age

country

salary

1

Paul

24

Russia

2000

2

Allen

26

USA

1400

3

John

31

Canada

3000

4

Mark

45

Australia

4500

5

Nick

18

Germany

1100

6

Kim

22

China

3100

7

James

25

USA

2800

Part A [4 points]:
Complete a function which returns the total number of employees in company relation that
have salary above (>) average.

CREATE OR REPLACE FUNCTION aboveAverageRows()
AS $$

RETURNS
DECLARE

BEGIN

END;
$$ LANGUAGE plpgsql;
3

Full Name:

Group:

Part B [3 points]:
Your task is to complete a procedure which inserts a new employee with the given parameters
to the company relation.

CREATE OR REPLACE PROCEDURE insert employee(
e id INTEGER,
e name VARCHAR(50),
e age INTEGER,
e country VARCHAR(50),
e salary INTEGER)
LANGUAGE plpgsql
AS $$
BEGIN

END;
$$;

Write a command to call the procedure that you completed in the previous step.

4

Full Name: _________________________

Group: __________________

Task 3. Transactions [10 points]
Consider the given table called grade.
id

name

grade rank letter

penalty

1

John

90

1 A

0.00

2

Alice

80

2 B

2.50

3

Bob

70

3 C

5.00

4

Emily

60

4 D

7.50

5

David

50

5 F

10.00

Your task is to fill the table on the next page with the outputs of the queries which are marked by letters (A,
B, C, D…). The code sessions should be executed from left to right.

Session 1

Session 2

BEGIN;
UPDATE grade SET grade = grade 200 WHERE id = 1;
UPDATE grade SET penalty =
penalty - 200 WHERE id > 3 or
rank<2;

SELECT name,
CASE
WHEN grade >= 1000 THEN 'High'
WHEN grade >= 500 THEN 'Medium'
ELSE 'Low'
END AS counter_category
FROM grade
WHERE grade= '70' AND id >= 3;

SELECT name,grade*2 FROM grade
WHERE penalty < '0';

Output A

Output B

COMMIT;

COMMIT;

UPDATE grade SET rank = rank + 200 WHERE
id = 2;
SELECT rank/2 FROM grade WHERE id = 3;

UPDATE grade SET rank = rank +
200 WHERE id = 3;
UPDATE grade SET rank = rank 100 WHERE name= 'David';
SELECT name FROM grade WHERE
letter LIKE 'D%';

Output C

Output D

COMMIT;

5

Full Name: _________________________

Group: __________________

SELECT name FROM grade WHERE id
% 2 = 1 and rank < 800;

SELECT rank*3 FROM grade WHERE name=
'David';

Output E

Output F

BEGIN ISOLATION LEVEL REPEATABLE
READ;
UPDATE grade SET rank = 800
WHERE id = 3;

BEGIN;
UPDATE grade SET rank = 200 WHERE id =
3;
INSERT INTO grade VALUES
(6, 'Top G', 100, 800, 'G', 100);
SELECT ROUND(rank, -2) FROM grade WHERE
name = 'Emily';
COMMIT;

SELECT 'The grade of student
Emily is $' || rank*0.1 FROM
grade WHERE name = 'Emily';
COMMIT;

Output G

Output H

SELECT rank+100 FROM grade WHERE name=
'John';

COMMIT;

Output I

BEGIN ISOLATION LEVEL
SERIALIZABLE;
UPDATE grade SET grade = 1000
WHERE id = 2;
SELECT sum(grade) FROM grade;

BEGIN;
UPDATE grade SET grade = 600 WHERE id =
2;
SELECT grade FROM grade WHERE name=
'David';

Output J

Output K

Outputs:
A

B

C

D

E

G

H

I

J

K

6

F

Full Name:

Group:

Task 4. Normalization [3 points]

Part A [1 point]:
List at least two requirements that the relation schema must meet to satisfy the conditions
for the First Normal Form (1NF).

Part B [2 points]:
Consider the following relation R:
R (CarID, CarName, CarBrand, CarColor, OwnerID, OwnerName, OwnerDateOfBirth,
ServiceID[], ServiceName[], ServiceAddress[])
The relation R has a composite primary key consisting of two attributes: CarID and
OwnerID. The relation represents information about a car, its owner, and the list of services
where the car can be maintained. A single owner could have multiple cars, but a car can have
only one owner. Each service can maintain multiple cars, and each car can be maintained in
several services.
Task: Normalize the relation R to the Third Normal Form (3NF) and specify its database
schema. Underline the primary key(s) in each relation.

7

Full Name:

Group:

Task 5. MongoDB [4 points]

Assume the database of games (called games) in the following format:
{
title: "Half-Life",
developer: "Valve",
publisher: {
name: "Valve",
location: "Bellevue, WA"
},
releaseYear: 1998,
genre: "First-person shooter",
rating: 9.3,
tags: ["Sci-Fi", "Aliens", "Action"]
}

Part 1. [2 points] Describe the given MongoDB query in plain text:
db.games.find(
{
releaseYear: { $gt: 2000 },
tags: "Action"
},
{
title: 1,
developer: 1,
}
)

Part 2. [2 points] Write MongoDB query that increments the rating of all games released
before the year 2000 by 0.1.

8

Full Name:

Group:

Task 6. Neo4j [9 points]
You are given the following CREATE statements:
CREATE (alice:Student {name: ’Alice’, age: 22})
CREATE (bob:Student {name: ’Bob’, age: 21})
CREATE (cs:Department {name: ’Computer Science’})
CREATE (datasci:Course {name: ’Data Science’, code: ’CS101’})
CREATE (ml:Course {name: ’Machine Learning’, code: ’CS102’})
CREATE (drSmith:Professor {name: ’Dr. Smith’})
CREATE (drJones:Professor {name: ’Dr. Jones’})
CREATE (alice)-[:ENROLLED IN]->(datasci)
CREATE (bob)-[:ENROLLED IN]->(ml)
CREATE (drSmith)-[:TEACHES]->(datasci)
CREATE (drJones)-[:TEACHES]->(ml)
CREATE (datasci)-[:BELONGS TO]->(cs)
CREATE (ml)-[:BELONGS TO]->(cs)

Part A [3 points]:
Draw a graph based on the CREATE statements that represents all nodes and relationships.

9

Full Name:

Group:

Part B [6 points]:
Write the output of the following Neo4j queries:
1. MATCH (p:Professor)-[:TEACHES]->(c:Course)<-[:ENROLLED IN]-(s:Student)
WITH p, MIN(s.age) AS minAge
MATCH (p)-[:TEACHES]->()<-[:ENROLLED IN]-(s)
WHERE s.age = minAge
RETURN p.name

2. MATCH (c:Course)-[:BELONGS 

(the rest is in the file)

## 2024: Midterm

Files: [Databases Midterm 2024.pdf](https://glebpopov.notion.site/b8ecb143739a48b98654f5f8c3a75c20)


Started on Wednesday, 6 March 2024
Question 1

In the Entity-Relationship (ER) model weak relationships are used to connect two weak entities. True or false?
a. False
b. True

The correct answer is:
False

Question 2

Match the given terms with the corresponding statements.
Primary
key

Choose...

Candidate
key

Choose...

Super key

Choose...

The correct answer is:
Primary key → a set of one or more attributes chosen by the database designer to uniquely identify an entity in
an entity set,
Candidate key → a minimal set of attributes that can uniquely identify an entity in an entity set,
Super key → a set of one or more attributes that can uniquely identify an entity in an entity set



Question 3

Which of the following statements correctly describe the total participation in the ER model?
a. An entity with total participation can exist independently of the relationship.
b. Total participation is indicated in ER diagrams by a double line connecting the entity to the
relationship.
c. Total participation is a scenario where only some instances of an entity are involved in a relationship.
d. Total participation means that every entity in a relationship must participate in at least one relationship
instance.

The correct answers are:
Total participation means that every entity in a relationship must participate in at least one relationship
instance.,
Total participation is indicated in ER diagrams by a double line connecting the entity to the relationship.

Question 4

How many tables will be created after mapping the following ER diagram to the relational schema?

a. 4
b. 3
c. 5
d. 1
e. 2

The correct answer is:
4



Question 5

Consider tables created by the following script and the given query:
CREATE TABLE Employees (
EmployeeID INT PRIMARY KEY,
FullName VARCHAR(100),
DepartmentID INT,
Salary DECIMAL(10, 2)
);
CREATE TABLE Departments (
DepartmentID INT PRIMARY KEY,
DepartmentName VARCHAR(100)
);

Query:
SELECT DepartmentId, AVG(Salary)
FROM Employees
GROUP BY DepartmentId
HAVING AVG(Salary) < 60000;

This query returns the average salary for each department where the average salary is less than 60000,
including departments with no employees. True or false?
a. True
b. False

The correct answer is:
False



Question 6

Considering given relations, what is the output of the query?

Query:
SELECT Product.name, Purchase.store
FROM Product
LEFT OUTER JOIN Purchase
ON Product.name = Purchase.prodName;

a.



b.

c.

The correct answer is:



Question 7

How is a weak entity characterized in an ER diagram using Chen notation? Select everything that is correct.
a. It is identifying relationship is a weak relationship.
b. It always has a total participation constraint in at least one relationship.
c. It has a unique primary key independent of other entities.
d. It is specified with a rectangular with a dotted border.

The correct answers are:
It always has a total participation constraint in at least one relationship.,
It is identifying relationship is a weak relationship.

Question 8

Which of the following approaches is correct when we map multivalued attributes from an Entity-Relationship
(ER) model to a Relational model?
a. Duplicate the row for each value of the multivalued attribute, changing only the value of the
multivalued attribute in each duplicate.
b. Store all values of the multivalued attribute in a single column separated by commas.
c. Create a new relation (table) that includes a foreign key to the original entity and a column for each
value of the multivalued attribute.

The correct answer is:
Create a new relation (table) that includes a foreign key to the original entity and a column for each value of
the multivalued attribute.



Question 9

Which of the following queries is monotonic?
a. SELECT CustomerID, SUM(TotalAmount) FROM Orders
GROUP BY CustomerID
HAVING SUM(TotalAmount) > 1000;

b. SELECT EmployeeID, FirstName, LastName
FROM Employees
WHERE Salary > ALL (
SELECT Salary
FROM Employees
WHERE Department = 'Marketing'
);

c. SELECT DISTINCT ProductName
FROM Products WHERE CategoryID NOT IN
(SELECT CategoryID FROM Categories WHERE CategoryName = 'Electronics');

The correct answer is:
SELECT CustomerID, SUM(TotalAmount) FROM Orders
GROUP BY CustomerID
HAVING SUM(TotalAmount) > 1000;



Question 10

We have the following schema:
Product (name, category)
Purchase (prodName, month, store)

Which expression(s) provides an SQL statement that computes, for each product, the total number of sales in
'March'?

a. SELECT Product.name, count(*)
FROM Product LEFT OUTER JOIN Purchase
ON Product.name = Purchase.prodName
WHERE Purchase.month = 'March'
GROUP BY Product.name;

b. SELECT Product.name, count(*)
FROM Product INNER JOIN Purchase ON Product.name = Purchase.prodName
WHERE Purchase.month = 'March'
GROUP BY Product.name;

c. SELECT p.name, (
SELECT COUNT(*)
FROM Purchase
WHERE Product.name = Purchase.prodName AND Purchase.month = 'March'
) AS total_sales_in_march
FROM Product p;

The correct answer is:
SELECT Product.name, count(*)
FROM Product LEFT OUTER JOIN Purchase
ON Product.name = Purchase.prodName
WHERE Purchase.month = 'March'
GROUP BY Product.name;



Question 11

Which operations in relational algebra form a complete set from which all other operations can be expressed?
Select all that apply.
a. Cartesian Product
b. Join
c. Minus (Difference)
d. Renaming
e. Projection
f.

Union

g. Intersection
h. Selection

The correct answers are:
Selection,
Projection,
Union,
Renaming,
Minus (Difference),
Cartesian Product

Question 12

In an EERD for a company's organizational structure, the 'Employee' entity is specialized into 'Full-Time' and
'Part-Time' subclasses. This specialization ensures that an employee cannot be both full-time and part-time
simultaneously. How is this specialization best classified?

a. Disjoint, Total
b. Overlapping, Total
c. Overlapping, Partial
d. Disjoint, Partial

The correct answer is:
Disjoint, Total



Question 13

Consider the following tables in a database:
Suppliers (sid: integer, sname: string, address: string)
Parts (pid: integer, pname: string, color: string)
Catalog (sid: integer, pid: integer, cost: real)

Which of the following statements best describes the result of the inner join operation between Suppliers and
Catalog?

a. It includes all suppliers, whether they have parts in the catalog or not.
b. It includes only suppliers who have parts in the catalog, along with the corresponding parts.
c. It includes all parts, whether they are supplied by a supplier or not.
d. It includes all suppliers and parts, with null values for suppliers without parts in the catalog.

The correct answer is:
It includes only suppliers who have parts in the catalog, along with the corresponding parts.

Question 14

Which of these is not a basic relational algebra operator?
a. Cartesian product
b. Set difference
c. Join
d. Rename

The correct answer is: Join



Question 15

Given the tables:
Worker (WORKER_ID: integer, FIRST_NAME: string, LAST_NAME: string, SALARY: real)
Title (TITLE_ID: integer, WORKER_REF_ID: integer, WORKER_TITLE: string)

What would be the result of the following query?
SELECT DISTINCT W.FIRST_NAME, T.WORKER_TITLE
FROM Worker W
INNER JOIN Title T
ON W.WORKER_ID = T.WORKER_REF_ID
AND T.WORKER_TITLE IN ('Manager', 'Supervisor');

a. All workers with titles 'Manager' and 'Supervisor'
b. Workers with title 'Supervisor' and their corresponding titles
c. Workers with title 'Manager' and 'Supervisor' in any order
d. Workers with title 'Manager' and their corresponding titles

The correct answers are:
Workers with title 'Manager' and their corresponding titles,
Workers with title 'Supervisor' and their corresponding titles

Question 16

According to the given relations, answer to the following query by relational algebra. (Pid is the foreign key of
Person relation in Parent relation).
Person(Pid, Pname, Age)
Parent(Pid, PPid, Gender)
Find the name of the 'grandmother' of 'Robert'.

a.

b.

c.

The

(the rest is in the file)

## 2023: Final

Files: [Databases Final 2023.pdf](https://glebpopov.notion.site/14ae746cceef805da55affa0233ab77c)


FINAL EXAM
DATABASES 2023

POINTS
Name and Surname

Task 1

Task 2

Task 3

Task 4

Task 5

Total

Task 1. For the given relations turn the statements into relational algebra queries and into SQL
queries. Consider ClubHead as a foreign key to StudentID
STUDENT(StudentID, Name, Surname, AdmissionYear)
CLUB(ClubID, ClubName, ClubHead)
CLUB_ROLE(StudentID, ClubID, RoleInClub)
COURSE(CourseID, CourseName)
GRADE(StudentID, CourseID, LetterGrade)
GRADE_INFO(LetterGrade, GradeTranscript)
a. Find student IDs which have only ‘A’ grades and which are heads of at least 1 club
RA query/queries:
(ΠStudentID (σLetterGrade=’A’(STUDENT⋈STUDENT.StudentID=GRADE.StudentIDGRADE))) ∩
(ΠStudentID (σClubRole=’Head’(STUDENT⋈STUDENT.StudentID=CLUB_ROLE.StudentIDCLUB_ROLE)))
SQL query/queries:
SELECT studentID
FROM student AS s INNER JOIN grade AS g
WHERE s.studentID = g.studentID
INTERSECT
SELECT studentID
FROM student AS s INNER JOIN club_role AS cr
WHERE s.studentID = cr.studentID
b. Find all names and surnames of the ‘Programmers’ club members except its ‘Head’
RA query/queries:
ρ(R1, (ΠStudentID (σClubName=’Programmers’(CLUB⋈CLUB.ClubID=CLUB_ROLE.ClubIDCLUB_ROLE)) \
ΠClubHead→StudentId (σClubName=’Programmers’(CLUB))))
ρ(R2, (ΠName,Surname(R1⋈R1.StudentID=STUDENT.StudentIDSTUDENT)))
SQL query/queries:
SELECT s.name, s.surname
FROM student AS s INNER JOIN
(SELECT studentID

FROM club AS c INNER JOIN club_role AS cr
WHERE c.clubName = ‘Programmers’) AS r1
WHERE s.studentID = r1.studentID
c. Find student IDs which are studying since 2021 and got NOT less than ‘B’ grade for
‘Databases’ course being NOT involved into any clubs
RA query/queries:
ρ(R1, (ΠStudentID(σAdmissionYear=2021(STUDENT))))
ρ(R2, (ΠCourseID(σCourseName=’Databases’(COURSE))))
ρ(R3, (R1⋈R1.StudentID=GRADE.StudentIDGRADE))
ρ(R4, (ΠStudentID(σLetterGrade=’A’ OR LetterGrade=’B’(R2⋈R2.CourseID=R3.CourseIDR3)))) \
ΠStudentID(CLUB_ROLE)
SQL query/queries:

Task 2. SQL Stored procedure. Write a SQL Stored Procedure for an International Money
Transfer System
Given the diagram below, your task is to create a stored procedure called
sp_ProcessInternationalTransfer that will help the bank staff process international transfers
effectively while ensuring compliance with various regulations. The stored procedure should
include input parameters such as IDs of the sender and recipient accounts, the transfer amount,
currency, date, and the reason for the transfer. The procedure must first verify that the sender’s
account has a sufficient balance in the specified currency. For transfers exceeding 10,000 USD
(or equivalent in the transfer currency), the procedure must also verify that the necessary
compliance checks were completed over the sender’s account as indicated in the Customers
table. If the sender's and recipient's accounts have different currencies, the procedure must apply
a conversion rate between the sender's currency and the recipient's currency, using the
ExchangeRates table. Once all conditions have been met, the procedure must deduct the transfer
amount from the sender's account and credit the recipient's account in their respective currencies.
The transfer details must then be logged in the Transfers table. If any of the conditions are not
met, the procedure must return an appropriate error message.

Grading creteria:
1. Check for account existence: The stored procedure should check that both the sender
and recipient accounts exist in the Accounts table.
Check for sender account balance: The stored procedure should check that the sender
account has sufficient balance in the specified currency to cover the transfer amount.
2. Compliance check: For transfers exceeding 10,000 USD (or equivalent), the stored
procedure should check the compliance status of the sender account.
3. Currency conversion: If the sender and recipient accounts have different currencies, the
stored procedure should apply currency conversion using the exchange rates in the
ExchangeRates table.
4. Deduct transfer amount and update accounts: The stored procedure should deduct the
transfer amount from the sender account and credit the recipient account, and update the
Accounts table accordingly.
5. Insert transfer record: The stored procedure should insert a record into the Transfers
table with the transfer details.
6. Exception handling: The stored procedure should handle exceptions and throw
appropriate error messages if any of the checks or operations fail.
7. Transaction handling: The stored procedure should group the necessary database
operations into a transaction to ensure data consistency and atomicity.

Task 3. Transactions :
You have the following table:

You need to write what is the values
Fill the output in the table, Execute from left to right →
Session 1

Session 2

BEGIN;
UPDATE accounts SET counter = counter
- 200 WHERE id = 1;
UPDATE accounts SET counter = counter
- 200 WHERE id = 3;

SELECT name,
CASE
WHEN counter >= 1000 THEN 'High'
WHEN counter >= 500 THEN 'Medium'
ELSE 'Low'
END AS counter_category
FROM accounts
WHERE zoom_id = '1001' AND id >= 1;

SELECT counter*2 FROM accounts
WHERE zoom_id ~ '^10';

Output = alice,High; A

Output =1600;B

COMMIT;

UPDATE accounts SET counter = counter
+ 200 WHERE id = 2;
SELECT counter/2 FROM accounts
WHERE zoom_id LIKE '10%';

COMMIT;

Output= 400 ; C

Output: there is no transaction in progress.; D

UPDATE accounts SET counter = counter
+ 200 WHERE id = 3;
UPDATE accounts SET counter = counter
- 100 WHERE zoom_id= '2001';
SELECT name FROM accounts WHERE
zoom_id LIKE '20%';
COMMIT;

UPDATE accounts SET counter = counter*2 + 200
WHERE id = 3;

Output =bob,bob; E

COMMIT;

SELECT counter FROM accounts
WHERE id % 2 = 1 and counter = 800;

SELECT counter FROM accounts WHERE zoom_id=
'2001';

Output =800; F

Output =200; G

BEGIN;
UPDATE accounts SET counter = 200
WHERE id = 3;
INSERT INTO accounts VALUES
(4, '3001', 'Top G', 100);
SELECT ROUND(counter, -2) FROM
accounts WHERE zoom_id = '2002';
COMMIT;

BEGIN ISOLATION LEVEL REPEATABLE
READ;
UPDATE accounts SET counter = 800 WHERE id =
3;

SELECT 'The balance of account 2002 is
not $' || counter*0.1 FROM accounts
WHERE zoom_id = '2002';
COMMIT;

COMMIT;

Output= The balance of account 2002 is
not 20; H

SELECT counter+100 FROM accounts WHERE
zoom_id= '1001';

COMMIT;

Output= 900; I

BEGIN;
UPDATE accounts SET counter =600
WHERE id = 2;
SELECT counter FROM accounts
WHERE zoom_id= '2001';

BEGIN ISOLATION LEVEL SERIALIZABLE;
UPDATE accounts SET counter =1000 WHERE id
= 2;
SELECT sum(counter) FROM accounts;

output= 600; J

COMMIT;
SELECT sum(counter) FROM accounts;

-----

output=1300; K

A

B

C

alice,High

1600

400

D
there is no
transaction in

E
bob,bob

progress.
F

G

H

I

J

K

800

200

The balance
of account
2002 is not
20

900

600

1300

Code for Session 1
-- BEGIN;
-- UPDATE accounts SET counter = counter - 200 WHERE id = 1;
-- UPDATE accounts SET counter = counter - 200 WHERE id = 3;
-- SELECT counter*2 FROM accounts WHERE zoom_id ~ '^10';
-- UPDATE accounts SET counter = counter + 200 WHERE id = 2;
-- SELECT counter/2 FROM accounts WHERE zoom_id LIKE '10%';
-- UPDATE accounts SET counter = counter + 200 WHERE id = 3;
-- UPDATE accounts SET counter = counter - 100 WHERE zoom_id= '2001';
-- SELECT name FROM accounts WHERE zoom_id LIKE '20%';
-- COMMIT;
-- SELECT counter FROM accounts WHERE id % 2 = 1 and counter = 800;
-- SELECT counter FROM accounts WHERE id % 2 = 1 and counter = 800;
-- BEGIN;
-- UPDATE accounts SET counter = 200 WHERE id = 3;
-- INSERT INTO accounts VALUES
-- (4, '3001', 'Top G', 100);
-- SELECT ROUND(counter, -2) FROM accounts WHERE zoom_id = '2002';
-- COMMIT;
-- -- SELECT 'The balance of account 2002 is ' || counter*0.1 FROM accounts WHERE zoom_id
= '2002';
-- -- COMMIT;
-- COMMIT;
-- BEGIN;
-- UPDATE accounts SET counter =600 WHERE id = 2;
-- SELECT counter FROM accounts WHERE zoom_id= '2001';
Code for Session 2

-- SELECT name,
-CASE
-WHEN counter >= 1000 THEN 'High'
-WHEN counter >= 500 THEN 'Mediu

(the rest is in the file)

## 2021: Final

Files: [the row](https://glebpopov.notion.site/14ee746cceef80c8b646cd5d4948021d)

## 2021: Midterm

Files: [Databases Midterm 2021.pdf](https://glebpopov.notion.site/14ee746cceef80c99467e99ad24bb419)


Database Systems 2021 - Midterm Exam
12/03/2021
Instructions:
1. This exam contains 13 questions (a total of 20 points) to be answered in 35
minutes.
2. Do not forget to write your name on the answer sheet.
3. If you have doubts about a question, ask the instructors.
4. Any communication with another person besides your instructors is considered
cheating.
5. Some questions are worth 2 points. Manage your time wisely.

Q1. (2 points) Assume the following banking system:
branch (branch-name, branch-city, assets)
customer (customer-name, customer-street, customer-only)
account (account-number, branch-name, balance)
loan (loan-number, branch-name, amount)
depositor (customer-name, account-number)
borrower (customer-name, loan-number)
Find the names of all customers who have a loan at the “Kazan” branch. Select one or
more options:

a.∏​customer-name​(σ​loan.loan-number = borrower.loan-number​((σ​branch-name = “Kazan”​(loan)) x
borrower))
B. ∏​customer-name​(σ​branch-name​ ​= “Kazan”​(σ​borrower.loan-number = loan.loan-number​(borrower​ x​
loan)))
C. ∏​customer-name​(σ​branch-name​ ​= “Kazan”​(σ​borrower.loan-number =
loan.loan-number​(borrower))x loan)
D. ∏​customer-name​(σ​branch-name​ ​= “Kazan”(​σ​borrower.loan-number = loan.loan-number​(borrower​ x​
loan)))

E. ∏​customer-name​(σ​branch-name = “Kazan”​(σ​borrower.loan-number​ ​= loan.loan-number​(borrower​ x​
loan))) – ∏​customer-name​(depositor)
Q2: (1 point) Define what the following relational algebra means

given the following relations:
Student (​sid​, name, surname, birthday)
Course (​cid​, year. semester)
Mark (​cid, sid​, mark)
Select the correct option:
A. Find names and birthdays of all students who had courses in the first semester in
2014
B. Find names and birthdays of all students who had each course in the first semester
in 2014
C. Find names and birthdays of all students who had courses in the first semester or in
2014
D. This expression is incorrect

Q3: (1 point) For the following table
users (userId, Name, age, Address)
And the query below
SELECT * from users WHERE Name LIKE ‘R%’ and
age<=40 ;

age>20 or

What are the best indexes to apply for minimum cost? Select all the options which are
correct.
a. Btree on Name
b. Btree on age
c. Hash on Name

d. Hash on Age
e. GIN on Age
f. GIN on Name

Q4: (2 points) Explain what cost is. What is the difference between the ‘estimated
startup cost’ and the ‘estimated total cost’?

Q5: (2 points) Answer the following questions on query optimization:
A. Replace the EXISTS in the SQL query below by an equivalent JOIN
B. Draw the starting query tree using the join of item (a)
C. Optimize the query tree:
a. Assume that the number of records in EMPLOYEE is smaller than
DEPENDENTS
b. Apply the heuristics of pushing projection and selection down the tree
D. Draw the resultant equivalent query tree after (c)
SELECT E.Fname, E.Lname
FROM EMPLOYEE AS E
WHERE EXISTS ( SELECT *
FROM DEPENDENT AS D
WHERE E.Ssn = D.Essn AND E.Sex = D.Sex
AND E.Fname = D.Dependent_name);

Q6: (1 point) Select the incorrect statements:
A. Materialized views are virtual tables that do not exist in the physical form
B. Triggers are used to monitor activities on the database such as the insertion and
deletion of record but not update operations
C. Correlated and uncorrelated nested queries always incur in similar query
overhead
D. A NATURAL JOIN between two tables can always be rewritten as an INNER
JOIN on the attributes with different names

Q7. (1 point) Regarding file organizations, answer:
A. In which conditions a sorted file is more efficient than a hashed file?
B. Can a sorted file be applied to a view? Why?

Q8. (2 points) Explain the relationship between (i) the efficiency of B+-tree indexes and
(ii) seek time and latency in IO.

Q9. (1 point) Explain the relationship between the blocking factor of the data file and the
index file. Which one is bigger and why.

Q10. (2 points) In which cases would you recommend:
A. The creation and use of a view
B. The use of a B+-tree
C. A bitmap index
D. A hash index

Q11. (2 points) What is the expected number of block reads for searching an individual
record on the table STUDENTS using a primary index? Use the information below:
●
●
●
●
●

Number of records in STUDENTS: 1,000,000
Block size: 4,096 bytes
Ordering key field: 10 bytes
Block pointer: 6 bytes
Assume that the binary search will be used

Q12. (1 point) In which conditions would you NOT recommend to create indexes? Why?

Q13. (2 points) For the query ​A ⨝​a=b​ B​, the index-based nested-loop join algorithm is
used since there is an index on the attribute b of table B. Visualizing the query as a
nested for-loop (i.e. a for-loop within a for-loop), which table would be in the outer-loop
and why.

# Citations

1. [IU B23 Academic Materials: Past Papers [EN programs]](https://glebpopov.notion.site/4ef3de0c7e68495b89ef086301361603)
