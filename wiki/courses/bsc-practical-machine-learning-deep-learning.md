---
type: course
title: "Practical Machine Learning and Deep Learning"
description: "A course covering practical aspects of deep learning, including NLP, Computer Vision, and generation, using PyTorch and Python."
resource: "https://eduwiki.innopolis.university/index.php/BSc%3A_Practical_Machine_Learning_Deep_Learning"
tags: ["deep-learning", "machine-learning", "course", "pytorch", "computer-vision", "nlp"]
aliases: ["BSc:PracticalMachineLearningDeepLearning"]
sources:
  - resource: "https://eduwiki.innopolis.university/index.php/BSc%3A_Practical_Machine_Learning_Deep_Learning"
    id: "7217"
    title: "BSc: Practical Machine Learning Deep Learning"
    last_modified: "2022-07-12T09:58:27Z"
generated:
  by: "catix-wiki/0.1 (local)"
  at: "2026-10-22T01:45:51+00:00"
status: draft
stale_after: "2024-07-11T09:58:27+00:00"
prerequisites: [{"course": "/courses/bsc-analyticalgeometryandlinearalgebrai-cs.md", "as_written": "CSE202 — Analytical Geometry and Linear Algebra I / []: Manifolds \"Linear Alg./Calculus: Manifolds", "via": "model"}, {"course": "/courses/bsc-analytic-geometry-and-linear-algebra-i.md", "as_written": "CSE202 — Analytical Geometry and Linear Algebra I / []: Manifolds \"Linear Alg./Calculus: Manifolds", "via": "model"}, {"course": "/courses/bsc-mathematicalanalysis-ii.md", "as_written": "CSE203 — Mathematical Analysis II: Basics of optimisation", "via": "model"}, {"course": "/courses/bsc-mathematicalanalysis-i.md", "as_written": "CSE201 — Mathematical Analysis I: integration and differentiation.", "via": "model"}, {"course": "/courses/bsc-theoretical-computer-science.md", "as_written": "CSE103 — Theoretical Computer Science: Graph theory basics, Spectral decomposition."}, {"course": "/courses/bsc-probability-and-statistics.md", "as_written": "CSE206 — Probability And Statistics: Multivariate normal dist.", "via": "model"}, {"course": "/courses/bsc-digitalsignalprocessing.md", "as_written": "CSE504 — Digital Signal Processing: convolution, cross-correlation\"", "via": "model"}, {"course": "/courses/bsc-digitalsignalprocessing-new.md", "as_written": "CSE504 — Digital Signal Processing: convolution, cross-correlation\"", "via": "model"}]
taught_by: ["/people/vladimirivanov.md"]
relations_by: "process:catix-wiki-graph/0.1"
---

# Practical Machine Learning and Deep Learning

## Practical Machine Learning and Deep Learning
- **Course name**: Practical Machine Learning and Deep Learning
- **Code discipline**: PMLDL-04
- **Subject area**: 

### Short Description
This course covers the following concepts: Practical aspects of deep learning (DL); Practical applications of DL in Natural Language Processing, Computer Vision and generation..

### Prerequisites

#### Prerequisite subjects
- CSE202 — Analytical Geometry and Linear Algebra I / []: Manifolds "Linear Alg./Calculus: Manifolds
- CSE203 — Mathematical Analysis II: Basics of optimisation
- CSE201 — Mathematical Analysis I: integration and differentiation.
- CSE103 — Theoretical Computer Science: Graph theory basics, Spectral decomposition.
- CSE206 — Probability And Statistics: Multivariate normal dist.
- CSE504 — Digital Signal Processing: convolution, cross-correlation"

#### Prerequisite topics


### Course Topics
**Course Sections and Topics**

| Section | Topics within the section |
| --- | --- |
| Review. CNNs and RNNs | # Image processing, FFNs, CNNs <br> # Training Deep NNs <br> # RNNs, LSTM, GRU, Embeddings <br> # Bidirectional RNNs <br> # Seq2seq <br> # Encoder-Decoder Networks <br> # Attention <br> # Memory Networks |
| Team Data Science Processes | # Team Data Science Processes <br> # Team Data Science Roles <br> # Team Data Science Tools (MLFlow, KubeFlow) <br> # CRISP-DM <br> # Productionizing ML systems |
| VAEs, GANs | # Autoencoders <br> # Variational Autoencoders <br> # GANs, DCGAN |
### Intended Learning Outcomes (ILOs)

#### What is the main purpose of this course?
The course is about the practical aspects of deep learning. In addition to frontal lectures, the flipped classes and student project presentations will be organized. During lab sessions the working language is Python. The primary framework for deep learning is PyTorch. Usage of TensorFlow and Keras is possible, usage of Docker is highly appreciated.

#### ILOs defined at three levels

##### Level 1: What concepts should a student know/remember/explain?
By the end of the course, the students should be able to ...
- to apply deep learning methods to effectively solve practical (real-world) problems;
- to work in data science team;
- to understand of principles and a lifecycle of data science projects.

##### Level 2: What basic practical skills should a student be able to perform?
By the end of the course, the students should be able to ...
- to understand modern deep NN architectures;
- to compare modern deep NN architectures;
- to create a prototype of a data-driven product.

##### Level 3: What complex comprehensive skills should a student be able to apply in real-life scenarios?
By the end of the course, the students should be able to ...
- to apply techniques for efficient training of deep NNs;
- to apply methods for data science team organisation;
- to apply deep NNs in NLP and computer vision. 
### Grading

#### Course grading range
| Grade | Range | Description of performance |
| --- | --- | --- |
| A. Excellent | 90-100 | - |
| B. Good | 75-89 | - |
| C. Satisfactory | 60-74 | - |
| D. Poor | 0-59 | - |

#### Course activities and grading breakdown
| Activity Type | Percentage of the overall course grade |
| --- | --- |
| Labs/seminar classes | 20 |
| Interim performance assessment | 30 |
| Exams | 50 |

#### Recommendations for students on how to succeed in the course


### Resources, literature and reference materials

#### Open access resources
- Goodfellow et al. Deep Learning, MIT Press. 2017
- Géron, Aurélien. Hands-On Machine Learning with Scikit-Learn and TensorFlow: Concepts, Tools, and Techniques to Build Intelligent Systems. 2017.
- Osinga, Douwe. Deep Learning Cookbook: Practical Recipes to Get Started Quickly. O’Reilly Media, 2018.

#### Closed access resources


#### Software and tools used within the course
 
## Teaching Methodology: Methods, techniques, & activities

### Activities and Teaching Methods
**Activities within each section**

| Learning Activities | Section 1 | Section 2 | Section 3 |
| --- | --- | --- | --- |
| Development of individual parts of software product code | 1 | 1 | 1 |
| Homework and group projects | 1 | 1 | 1 |
| Midterm evaluation | 1 | 1 | 1 |
| Testing (written or computer based) | 1 | 1 | 1 |
| Discussions | 1 | 1 | 1 |
### Formative Assessment and Course Activities

#### Ongoing performance assessment

##### Section 1
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | Suppose you use Batch Gradient Descent and you plot the validation error at every epoch. If you notice that the validation error consistently goes up, what is likely going on? How can you fix this? | 1 |
| Question | Is it a good idea to stop Mini-batch Gradient Descent immediately when the validation error goes up? | 1 |
| Question | List the optimizers that you know (except SGD) and explain one of them | 1 |
| Question | Describe Xavier (or Glorot) initialization. Why do you need it? | 1 |
| Question | Name advantages of the ELU activation function over ReLU. | 0 |
| Question | Can you name the main innovations in AlexNet, compared to LeNet-5? What about the main innovations in GoogLeNet and ResNet? | 0 |
| Question | What is the difference between LSTM and GRU cells? | 0 |
##### Section 2
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | What is CRISP-DM? | 1 |
| Question | What is TDSP? | 1 |
| Question | How to use MLflow? | 1 |
| Question | What is TensorBoard? | 1 |
| Question | How to apply Kubeflow in practice? | 1 |
| Question | Explain issues in distributed learning of deep NNs. | 0 |
| Question | How do you organize your data science project? | 0 |
| Question | Recall a checklist for organization of a typical data science project. | 0 |
##### Section 3
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | What is an Autoencoder? Can you list the structure and types of Autoencoders? | 1 |
| Question | Can you describe ways to train Stacked AEs? | 1 |
| Question | What is Denoising AE? Can you describe what is sparsity loss and why it can be useful? | 1 |
| Question | Can you make a distinction between AE and VAE? | 1 |
| Question | If an autoencoder perfectly reconstructs the inputs, is it necessarily a good autoencoder? How can you evaluate the performance of an autoencoder? | 0 |
| Question | How do you tie weights in a stacked autoencoder? What is the point of doing so? | 0 |
| Question | What about the main risk of an overcomplete autoencoder? | 0 |
| Question | How the loss function for VAE is defined? What is ELBO? | 0 |
| Question | Can you list the structure and types of a GAN? | 0 |
| Question | How would you train a GAN? | 0 |
| Question | How would you estimate the quality of a GAN? | 0 |
| Question | Can you describe cost function of a Discriminator? | 0 |
#### Final assessment
**Section 1**
1. Explain what the Teacher Forcing is.
1. Why do people use encoder–decoder RNNs rather than plain sequence-to-sequence RNNs for automatic translation?
1. How could you combine a convolutional neural network with an RNN to classify videos?
**Section 2**
1. Can you explain what it means for a company to be ML-ready?
1. What a company can do to become ML-ready / Data driven?
1. Can you list approaches to structure DS-teams? Discuss their advantages and disadvantages.
1. Can you list and define typical roles in a DS team?
1. What do you think about practical aspects of processes and roles in Data Science projects/teams?
**Section 3**
1. Can you make a distinction between Variational approximation of density and MCMC methods for density estimation?
1. What is DCGAN? What is its purpose? What are main features of DCGAN?
1. What is your opinion about Word Embeddings? What types do you know? Why are they useful?
1. How would you classify different CNN architectures?
1. How would you classify different RNN architectures?
1. Explain attention mechanism. What is self-attention?
1. Explain the Transformer architecture. What is BERT?

#### The retake exam
**Section 1**

**Section 2**

**Section 3**

<!-- catix:relations -->
## Relations

- Prerequisites: [Analytical Geometry and Linear Algebra I (CS)](/courses/bsc-analyticalgeometryandlinearalgebrai-cs.md) (CSE202 — Analytical Geometry and Linear Algebra I / []: Manifolds "Linear Alg./Calculus: Manifolds, matched by the model); [BSc: Analytic Geometry And Linear Algebra I](/courses/bsc-analytic-geometry-and-linear-algebra-i.md) (CSE202 — Analytical Geometry and Linear Algebra I / []: Manifolds "Linear Alg./Calculus: Manifolds, matched by the model); [BSc: Mathematical Analysis II](/courses/bsc-mathematicalanalysis-ii.md) (CSE203 — Mathematical Analysis II: Basics of optimisation, matched by the model); [BSc: Mathematical Analysis I](/courses/bsc-mathematicalanalysis-i.md) (CSE201 — Mathematical Analysis I: integration and differentiation., matched by the model); [Theoretical Computer Science](/courses/bsc-theoretical-computer-science.md) (CSE103 — Theoretical Computer Science: Graph theory basics, Spectral decomposition.); [BSc: Probability And Statistics](/courses/bsc-probability-and-statistics.md) (CSE206 — Probability And Statistics: Multivariate normal dist., matched by the model); [Digital Signal Processing](/courses/bsc-digitalsignalprocessing.md) (CSE504 — Digital Signal Processing: convolution, cross-correlation", matched by the model); [Digital Signal Processing](/courses/bsc-digitalsignalprocessing-new.md) (CSE504 — Digital Signal Processing: convolution, cross-correlation", matched by the model)
- Taught by: [Vladimir Ivanov](/people/vladimirivanov.md)
<!-- /catix:relations -->

# Citations

1. [BSc: Practical Machine Learning Deep Learning](https://eduwiki.innopolis.university/index.php/BSc%3A_Practical_Machine_Learning_Deep_Learning), revision 7217
