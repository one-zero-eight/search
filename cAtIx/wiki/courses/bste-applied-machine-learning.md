---
type: course
title: "BSTE: Applied Machine Learning"
description: "Course CSE807 covering object detection, adversarial learning, Bayesian inference, model evaluation, and deployment on edge devices using Python and PyTorch."
resource: "https://eduwiki.innopolis.university/index.php/BSTE%3A_Applied_Machine_Learning"
tags: ["machine-learning", "deep-learning", "computer-vision", "deployment", "pytorch"]
sources:
  - resource: "https://eduwiki.innopolis.university/index.php/BSTE%3A_Applied_Machine_Learning"
    id: "8054"
    title: "BSTE: Applied Machine Learning"
    last_modified: "2023-02-08T12:15:48Z"
generated:
  by: "catix-wiki/0.1 (local)"
  at: "2026-10-22T02:06:05+00:00"
status: draft
stale_after: "2025-02-07T12:15:48+00:00"
prerequisites: [{"as_written": "CSE104"}, {"course": "/courses/bsc-introduction-to-machine-learning.md", "as_written": "CSE302"}]
relations_by: "process:catix-wiki-graph/0.1"
---

# BSTE: Applied Machine Learning

## Applied Machine Learning
- **Course name**: Applied Machine Learning
- **Code discipline**: CSE807
- **Subject area**: Data Science and AI

### Short Description
This course has three major parts: 1) Building and training models for Object detection, Adversarial Learning and Baysian inference (Kalman Filters) and 2) the evaluation and interpretation of deep learning models (black box and open box) and 3) Deploying such models for use on edge devices or on a server

### Prerequisites

#### Prerequisite subjects
- CSE104
- CSE302

#### Prerequisite topics
- Basic programming skills.
- Introduction to machine learning.
- Familiarity with some development framework or technology (web or mobile)
- Python

### Course Topics
**Course Sections and Topics**

| Section | Topics within the section |
| --- | --- |
| Practical ML models | # Object Detectors and Instance segmentation: RCNN/YOLO <br> # Transfer Learning and Adversarial Training <br> # Kalman Filters and state estimators |
| Evaluation and Interpretability | # Evaluation of Regressions, Classification and Object detection models. <br> # Interpretation of basic models. <br> # LIME for deep networks interpretation. |
| Deployment | # Rest APIs for ML. <br> # Deployment on the edge. |
### Intended Learning Outcomes (ILOs)

#### What is the main purpose of this course?
What is the main goal of this course  formulated in one sentence?
The course is about the applied aspects of a machine learning engineer's job. In addition to lectures, lab sessions and a student project will be organized. During lab sessions the working language is Python. The primary framework for deep learning is PyTorch. Usage of TensorFlow and Keras is possible, usage of Docker is highly appreciated.

#### ILOs defined at three levels

##### Level 1: What concepts should a student know/remember/explain?
By the end of the course, the students should be able to ...
- Describe the adversarial learning process and how it relates to transfer learning.
- List the different object detectors and explain their differences.
- Explain what are the main usages of State Estimator models.
- Understand the effect of evaluation metrics on the performance of the models.

##### Level 2: What basic practical skills should a student be able to perform?
By the end of the course, the students should be able to ...
- Train a model for object detection from data labeling to deployment
- Evaluate different types of models.
- Read research papers in the field of deep learning effectively.
- Deploy a deep learning model to be used in a real world environment.

##### Level 3: What complex comprehensive skills should a student be able to apply in real-life scenarios?
By the end of the course, the students should be able to ...
- Plan a data science project to answer business questions.
- Understand how to use Adversarial learning for tasks other than image generation.
- Estimating the state of a system.
- Deploy trained models with confidence in their performance 
### Grading

#### Course grading range
| Grade | Range | Description of performance |
| --- | --- | --- |
| A. Excellent | 90-100 | - |
| B. Good | 75-89 | - |
| C. Satisfactory | 60-74 | - |
| D. Fail | 0-59 | - |

#### Course activities and grading breakdown
| Activity Type | Percentage of the overall course grade |
| --- | --- |
| Assignment | 25 |
| Quizzes | 25 |
| Final Exam | 25 |
| Project | 25 |

#### Recommendations for students on how to succeed in the course
Participation is important. Showing up is the key to success in this course.
You will work in teams, so coordinating teamwork will be an important factor for success. This is also reflected in the peer review being a graded item.
Review lecture materials before classes to do well in quizzes.
Reading the recommended literature is optional, and will give you a deeper understanding of the material.

### Resources, literature and reference materials

#### Open access resources
- Mask R-CNN Kaiming He, Georgia Gkioxari, Piotr Dollár, Ross Girshick https://arxiv.org/abs/1703.06870
- YOLOv7: Trainable bag-of-freebies sets new state-of-the-art for real-time object detectors  https://arxiv.org/abs/2207.02696

#### Closed access resources
- Practical Machine Learning with Python: A Problem-Solver's Guide to Building Real-World Intelligent Systems
- Practical Machine Learning for Computer Vision: End-to-End Machine Learning for Images
- Hands-On Machine Learning with Scikit-Learn, Keras, and Tensorflow: Concepts, Tools, and Techniques to Build Intelligent Systems

#### Software and tools used within the course
- Colab, https://colab.research.google.com/drive/
- Streamlit, https://streamlit.io/ 
## Teaching Methodology: Methods, techniques, & activities

### Activities and Teaching Methods
**Teaching and Learning Methods within each section**

| Teaching Techniques | Section 1 | Section 2 | Section 3 |
| --- | --- | --- | --- |
| Problem-based learning (students learn by solving open-ended problems without a strictly-defined solution) | 1 | 1 | 1 |
| Project-based learning (students work on a project) | 1 | 1 | 1 |
| Differentiated learning (provide tasks and activities at several levels of difficulty to fit students needs and level) | 1 | 1 | 1 |
| развивающего обучения (задания и материал "прокачивают" ещё нераскрытые возможности студентов); | 1 | 1 | 1 |
| концентрированного обучения (занятия по одной большой теме логически объединяются); | 1 | 1 | 1 |
| inquiry-based learning | 1 | 1 | 1 |
**Activities within each section**

| Learning Activities | Section 1 | Section 2 | Section 3 |
| --- | --- | --- | --- |
| Lectures | 1 | 1 | 1 |
| Interactive Lectures | 1 | 1 | 1 |
| Lab exercises | 1 | 1 | 1 |
| Development of individual parts of software product code | 1 | 1 | 1 |
| Group projects | 1 | 1 | 1 |
| Quizzes (written or computer based) | 1 | 1 | 1 |
| Peer Review | 1 | 1 | 1 |
| Discussions | 1 | 1 | 1 |
| Presentations by students | 1 | 1 | 1 |
| Written reports | 1 | 1 | 1 |
| Experiments | 0 | 0 | 1 |
### Formative Assessment and Course Activities

#### Ongoing performance assessment

##### Section 1
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Quiz | 1. What is a product? What are the techniques for describing a product idea in a clear concise manner? <br> 2. What user research techniques do you know? In what situations are they applied? <br> 3. What are the key customer conversation principles according to the Mom Test technique? Bring an example of bad and good questions to ask. <br> 4. What are the 4 phases of the requirements engineering process? <br> 5. How do we document requirements? What techniques do you know? | 1 |
| Presentation | Prepare a short 2-minutes pitch for your project idea (2-5 slides). <br> Suggested structure: <br> What problem you are solving: <br> - State the problem clearly in 2-3 short sentences. <br> Who are you solving it for: <br> - Who is your user/customer? <br> - Why will they be attracted to it? <br> What is your proposed solution to solve that problem: <br> - One sentence description <br> - What main feature(s) will it have? | 0 |
| Individual Assignments | A1: Product Ideation and Market Research <br> Formulate 3 project ideas in the following format: <br> X helps Y to do Z  – where X is your product’s name, Y is the target user, and Z is what user activity product help with. <br> Submit Link to Screenshot board and Feature Analysis Table: <br> - Pick and explore 5 apps similar to your idea <br> - Take screenshots along the way and collect them on a board. <br> - Make a qualitative analysis table for app features. <br> Prepare a short 2-minutes pitch for your project idea (2-5 slides). <br> Suggested structure: <br> What problem you are solving: <br> - State the problem clearly in 2-3 short sentences. <br> Who are you solving it for: <br> - Who is your user/customer? <br> - Why will they be attracted to it? <br> What is your proposed solution to solve that problem: <br> - One sentence description <br> - What main feature(s) will it have? | 1 |
| Group Project Work | A2: Forming Teams and Identifying Stakeholders <br> Students are distributed into teams. <br> Meet your team <br> Discuss the idea <br> Agree on the roles <br> Setup task tracker (Trello or similar) <br> Identify 3-5 stakeholders and how to approach them <br> Compose a set of 5 most important questions you would ask from each stakeholder when interviewing them <br> Submit <br> A pdf with the idea description, roles distribution among the team, identified stakeholders, ways to approach them, a set of questions for each stakeholder. <br> An invite link to join your task tracker <br> A3: Domain Exploration and Requirements <br> User Research Process: <br> Compose the questionnaire for each stakeholder type. <br> Talk to 5-7 stakeholders. <br> Keep updating the questionnaire throughout the process <br> Compose an interview results table <br> Produce personas <br> Summarize most important learning points <br> Describe features your MVP will have (use case diagram + user story mapping) <br> Submit a pdf report with: <br> Personas + corresponding questionnaires <br> Interview results table (can provide a link to spreadsheet, make sure to open access) <br> Learning points summary <br> MVP features. <br> Optional: <br> Start implementation of the functionality you are certain about. <br> Assignment 4. UI design, Prototyping, MVP, and Usability Testing <br> Break down MVP features into phases and cut down the specification to implement MVP V1 <br> Produce low and high fidelity designs for your product. <br> Review the phases breakdown. <br> Follow either the Prototyping or MVP path to complete the assignment. <br> Prototyping path: <br> Make a clickable prototype with Figma or a similar tool <br> Make 5-10 offline stakeholders use your prototype, observe them and gather feedback <br> Embed your prototype into an online usability testing tool (e.g. Maze). <br> Run an online usability test with 5-10 online stakeholders. <br> Summarize key learning points <br> MVP path: <br> Review your MVP phases. <br> Build MVP V1 <br> Make 5-10 offline stakeholders use your MVP, observe them and gather feedback <br> Integrate an online usability testing tool to observe user sessions (e.g. Smartlook). <br> Distribute the MVP to 5-10 online stakeholders and run an online usability test. <br> Summarize key learning points <br> Submit all of the below in one PDF: <br> Link to sketches and designs. <br> Link to your MVP/Clickable prototype. <br> Link to online usability test. <br> Names of people you conducted the tests with and which stakeholder type are they. <br> Key learning points summary. <br> Make sure all links are accessible/viewable. | 1 |
##### Section 2
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Quiz | 1. What does the acronym MVP stand for? What types of MVP do you know of? <br> 2. Define roles, activities, and artefacts of Scrum. What differentiates Scrum from other Agile frameworks, e.g. Kanban? <br> 3. What does DEEP criteria stand for when discussing Product Backlog? Explain each of the aspects with examples. <br> 4. Describe how Scrum activities are performed. Which of them are essential and which of them can vary depending on the product. | 1 |
| Presentation | Prepare a 5-mins presentation describing your: <br> product backlog <br> sprint results <br> MVP-launch plan <br> Each team will present at the class. The assessment will be based on the presentation delivery, reasoning for decision making and asking questions and providing suggestions for other teams. | 0 |
| Group Project Work | Assignment 5. Launching an MVP <br> 1. Populate and groom product backlog: <br> Comply with the DEEP criteria. <br> 2. Run two one-week sprints: <br> Conduct two Sprint plannings, i.e. pick the tasks for Sprint Backlog. <br> Conduct two Sprint reviews <br> Run one Sprint Retrospective <br> 3. Make a launch plan and release: <br> You need to launch in the following two weeks. <br> Decide what functionality will go into the release. <br> Release your first version in Google Play. <br> Hint: Focus on a small set of features solving a specific problem for a specific user, i.e. MVP. <br> 4. Prepare a 5-mins presentation describing your: <br> product backlog <br> sprint results <br> MVP-launch plan. <br> Demo for your launched MVP. <br> Each team will present at the class. The assessment will be based on the presentation delivery, reasoning for decision making and asking questions and providing suggestions for other teams. <br> 5. Submit a PDF with: <br> Backlogs and Launch plan <br> Link to the launched product <br> Assignment 6. AC, DoD and Midterm Presentation <br> 1. Produce acceptance criteria for 3-5 most important user stories in your product. <br> 2. Produce definition of done checklist <br> 3. Estimate the items in your product backlog <br> 4. Prepare a midterm presentation for 10-mins in which you cover: <br> The problem you are trying to solve <br> Your users and customers (personas) <br> Your solution and it's core value proposition <br> Current state of your product <br> Clear plan for the upcoming weeks <br> Your team and distribution of responsibilities <br> Demo <br> Retrospective and learning points <br> Link to your app <br> Submit a pdf with: <br> Items 1, 2, 3 <br> link to the presentation | 1 |
##### Section 3
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Quiz | 1. What are common product hypotheses present? How can we formulate them as questions about our UX? <br> 2. Explain what is hypothesis-driven development <br> 3. Describe the important aspects and elements of a controlled experiment | 1 |
| Presentation | Prepare a short 2-minutes pitch for your project idea (2-5 slides). <br> Suggested structure: <br> What problem you are solving: <br> - State the problem clearly in 2-3 short sentences. <br> Who are you solving it for: <br> - Who is your user/customer? <br> - Why will they be attracted to it? <br> What is your proposed solution to solve that problem: <br> - One sentence description <br> - What main feature(s) will it have? | 0 |
| Group project work | Assignment 7: Development, Observation, and Product Events. <br> 1. Continue with your development process: <br> - Hold sprint planning and reviews. <br> - Revisit estimations and keep track for velocity calculation. <br> - Host demos and release new versions to your users <br> 2. Observing users: <br> - Integrate a user sessions recording tool into your product <br> - As a team: watch 100 user sessions and outline common user behavior patterns. <br> - Each team member: give product to 3 new people and observe them use it. <br> 3. Product events: <br> Create a product events table. <br> Integrate a free analytics tool that supports events reporting (e.g. Amplitude, MixPanel). <br> Write and submit a report: <br> - describe user behavior patterns (main ways how people use your product). <br> - learning points from the observations <br> - add the events table. <br> - describe which analytics tool you chose and why <br> Assignment 8: GQM, Metrics, and Hypothesis-testing. <br> 1. GQM and Metrics Dashboard <br> - Compose a GQM for your product. <br> - Identify your  focus and L1 metrics <br> - Setup an Analytics Dashboard with the metrics you chose. <br> - Add the instructors to your Analytics Dashboard. <br> Hypothesis-testing: <br> - answer clarity and hypotheses: do users understand your product, is it easy for them to get started, and do they return? <br> - suggest product improvements to increase clarity, ease of starting and retention. <br> - based on the suggestions formulate 3 falsifiable hypotheses <br> - design a simple test to check each of them <br> - pick one test that could be conducted by observing your users <br> - conduct the test <br> Submit: <br> - GQM, Focus and L1 Metrics breakdown. <br> - Report on the hypothesis-testing activities <br> - Access link to the dashboard. <br> Assignment 9: Running an A/B test <br> Compose an A/B test: <br> - Design a change in your product <br> - Hypothesis: Clearly state what you expect to improve as the result of the change. <br> - Parameter and Variants: Describe both A and B variants (and other if you have more). <br> - Intended sample size. <br> - OEC: Determine the target metric to run the experiment against. <br> Then do one of the two options: <br> Option 1: Conduct the A/B test using a remote control and A/B testing tool (Firebase, Optimizely or like) <br> Option 2: Do the statistical math yourself <br> Conduct an A/B test and collect data. <br> Do the math manually using the standard Student T-test. <br> Submit a PDF with: <br> -  the A/B test description <br> - report on how the experiment went. <br> - either screenshots from the tool or math calculations. | 1 |
#### Final assessment
**Section 1**
1. Grading criteria for the final project presentation:
1. 1. Problem: short clear statement on what you are solving, and why it’s important.
1. 2. User: should be a specific user, can start from generic and then show how you narrowed it.
1. 3. Solution: how do you target the problem, what were the initial assumptions/hypotheses
1. 4. Elicitation process: interviews, how many people, what questions you asked, what you learnt.
**Section 2**
1. 5. Arriving at MVP: how you chose features, describe prototyping and learning from it, when did you launch, and how it went.
1. 6. Team and development process: how it evolved, what were the challenges, what fixes you made to keep progressing.
1. 7. Product demo: make it clear what your current product progress is.
**Section 3**
1. 7. Hypothesis-driven development: how did you verify value and understandability of your product, what were the main hypotheses you had to check through MVP.
1. 8. Measuring product: what metrics you chose, why, what funnels did you set for yourself, and what was the baseline for your MVP.
1. 9. Experimentation: What usability tests and experiments you conducted, what did you learn, how did it affect your funnels and metrics.

#### The retake exam
**Section 1**
1. For the retake, students have to implement a product and follow the guidelines of the course. The complexity of the product can be reduced, if it is one person working on it. The grading criteria for each section are the same as for the final project presentation. There has to be a meeting before the retake itself to plan and agree on the product ideas, and to answer questions.
1. P7. Activities and Teaching Methods by Sections
1. Mark what techniques and methods are used in each section (1 is used, 0 is not used).
1. Table A1: Teaching and Learning Methods within each section
1. Table A2: Activities within each section
**Section 2**

**Section 3**

<!-- catix:relations -->
## Relations

- Prerequisites: CSE104; [Introduction To Machine Learning](/courses/bsc-introduction-to-machine-learning.md) (CSE302)
<!-- /catix:relations -->

# Citations

1. [BSTE: Applied Machine Learning](https://eduwiki.innopolis.university/index.php/BSTE%3A_Applied_Machine_Learning), revision 8054
