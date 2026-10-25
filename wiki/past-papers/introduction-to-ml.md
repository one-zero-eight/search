---
type: page
title: "Past exam papers: Introduction to ML"
description: "Past exams and tests of Introduction to ML at Innopolis University (3 papers, 2021–2025), collected by students: tasks, formats, points."
resource: "https://glebpopov.notion.site/4ef3de0c7e68495b89ef086301361603"
tags: ["past-papers", "exams", "bachelor", "introduction-to-ml"]
audience: ["student"]
source_kind: community
language: en
section: "notion/past-papers"
subject: "Introduction to ML"
sources:
  - resource: "https://glebpopov.notion.site/4ef3de0c7e68495b89ef086301361603"
    title: "IU B23 Academic Materials: Past Papers [EN programs]"
generated:
  by: "catix-wiki/0.1 past-papers (code only, no model)"
status: draft
---

# Past exam papers: Introduction to ML

Exams and tests of **Introduction to ML** from previous years, as the students collected them in [IU B23 Academic Materials: Past Papers [EN programs]](https://glebpopov.notion.site/4ef3de0c7e68495b89ef086301361603). Not an official source: a paper may be one variant of several, or written down from memory. Newest first.

## 2025: Bonus Assignment

Files: [Intro to ML Bonus Assignment 2025.pdf](https://glebpopov.notion.site/1e3e746cceef801a93ccef99cc95a7f7)


[S25] Introduction to Machine Learning
Bonus Assignment
April 28, 2025

Name:
Surname:
Group:
Email:

Points per task (for teacher assistant)

Task

Points

1

1

2

1

3

1

4

1

5

1

6

3

7

3

8

1

9

3

10

2

11

3

12

2

13

3

Result

1.​ Could you benefit from building a Boosting ensemble of Linear Regression?​
​
Answer with justification:​
​
​

2.​ Can we expect high performance from a CNN without nonlinear activation
functions?​
​
Answer with justification:​
​
​
​
3.​ Can you have model quality gains by shuffling…​
​
(a) training set?
(b) test set?​
Justification:
Justification:​
​
​
​
4.​ Can you use a larger batch size during inference (test-time evaluation) than
you used during the training?​
​
Answer with justification:​
​
​
​
5.​ What happens to a specified metric for a positive class if you increase the
classification threshold in Logistic Regression?​
​
(a) Precision:
(b) Recall:​
( ) Increase ( ) Decrease
( ) Increase ( ) Decrease​
​
Justification:​
​
​
​
​

6.​ Fill a table for a given CNN architecture and input 32x32 pixels RGB image
with alpha-channel (4 channels, batch size is 1):
Layer

Output dimensions

Trainable parameters

Conv2d (f=3, s=1, p=1, k=16)
Sigmoid
MaxPool2d (f=2, s=2)
BatchNorm2d
Conv2d (f=3, s=2, p=0, k=16)
ReLU

Note: you may write a formula without calculations for the Trainable parameters.​
7.​ Fill in right characteristics of Machine Learning algorithms in a table below:​
Algorithm

Requires training (yes / no)

ML Problem solved

Supervised (yes / no)

KNN
K-means
PCA

Hint: some options for the second column: classification, regression, clustering,
outliers detection, dimensionality reduction.​
8.​ Fill in the comparison table for Bagging and Boosting algorithms:​

Algorithm

Weak Learner Problem addressed
(high bias / variance)

Support parallel training​
of weak learners (yes / no)

Example of model

Bagging
Boosting

9.​ Fill in the comparison table for different gradient descent optimizations:​

Optimizer

Memory consumption
relative to SGD (e.g., 30%
less or 2 times more)

SGD

1

SGD with Momentum
Adam

Tracks gradient
direction (yes / no)

Tracks gradient
magnitude (yes / no)

10.​Fill in the comparison table for clustering algorithms using YES or NO for all
columns:​

Algorithm

Requires the number
of clusters in advance

Sensitive to
initialization

Handles non-spherical
clusters

Sensitive to
outliers

K-means
K-means++
DBSCAN
Agglomerative
Clustering

11.​Consider the following two-dimensional dataset, consisting of points from
two different classes (+1 and -1):
●​ positive class (+1): (2, 2), (3, 3), (3, 0)
●​ negative class (-1): (0, 0), (1, 1), (0, 3)
Suppose you train a linear SVM on this dataset. Answer the following
clearly:​
a.​ Would it be possible for a linear SVM to classify points with zero errors?​
Answer with justification:​
​
​
​
​
b.​ Identify at least one point in the dataset that will definitely not become
a support vector and briefly explain why.​
Answer with justification:​
​
​
​
​
c.​ New instance of negative class (2, 1) is added to the dataset. Are
classes still linearly separable? Briefly justify whether the new point
changes the margin and support vectors.​
Answer with justification:​
​

12.​You have performed PCA on a dataset with 3 original features and obtained
the following eigenvalues from the covariance matrix:​
​
λ1 = 4. 0, λ2 = 3. 0, λ3 = 1. 0​
a.​ What percentage of the variance is explained by the first two principal
components?​
Answer with justification:​
​
​
​
​
​
b.​ If we reconstruct the original data using only the first two principal
components, what fraction of variance (information) is lost?​
Answer with justification:​
​
​
​
​
​
13.​Suppose you apply K-means++ initialization on the following 1D data points:
{1, 2, 3, 10, 11, 12}
You want to form two clusters (K=2). Assume the first randomly selected
centroid is the point x=2. Compute clearly, step-by-step, the probability
that the next centroid selected (according to the K-means++ initialization
algorithm, which uses squared Euclidean distances) is the point x=10?​
​
Solution:​
​
​
​
​
​
​
​
Answer:

## 2025: Midterm

Files: [Intro to ML Midterm 2025.pdf](https://glebpopov.notion.site/1b4e746cceef805bb0fbeba3fd61ccb1)


Variant 0
Question 1: (1 point) As the number of training examples tends to infinity,
your model trained on that data will have:
(a) Lower bias
(b) Higher bias
(c) The same bias
(d) Bias equal to the variance
Answer: (c) The same bias
Explanation:
Bias refers to the error introduced by approximating a real-world problem
with a simplified model. It is an inherent property of the chosen model’s architecture and does not depend on the size of the training data.
Total Error = Bias2 + Variance + Irreducible Error
Increasing the number of training examples primarily reduces the model’s
variance (i.e., the error due to fluctuations in the training data). However,
bias remains unchanged because it depends on the model’s assumptions and
complexity.
For example: - A linear model trained to approximate a nonlinear function
will maintain the same level of bias, no matter how much data you provide. More
data may improve the model’s stability and reduce variance, but the underlying
linear approximation still introduces the same systematic error.
Thus, the correct answer is (c) — the model will have the same bias as the
number of training examples tends to infinity.

Question 2: (1 point) Which kernel function would be most appropriate
for a dataset where the decision boundary is circular?
(a) Linear kernel
(b) Polynomial kernel with degree = 1
(c) Radial Basis Function (RBF) kernel
(d) Sigmoid kernel
Answer: (c) Radial Basis Function (RBF) kernel
Explanation:
The Radial Basis Function (RBF) kernel is the most appropriate choice for
datasets where the decision boundary is circular or exhibits complex, non-linear
patterns. The RBF kernel is defined as:

1

Variant 0

K(x, x′ ) = exp −γ∥x − x′ ∥2



Where: - x and x′ are input feature vectors. - γ is a hyperparameter that
controls the influence of each training example.
Why the RBF Kernel is Suitable:
- The RBF kernel effectively maps data points into a higher-dimensional space
where circular (or more complex) decision boundaries can be learned as linear
boundaries in that transformed space. - The exponential term ensures that
points closer to each other have a stronger similarity score, which is ideal for
circular decision regions. - Unlike linear or low-degree polynomial kernels, the
RBF kernel is highly flexible and can capture intricate, non-linear patterns.
Why Other Options Are Less Suitable:
- (a) Linear kernel:Suitable for linearly separable data but fails to model circular decision boundaries. - (b) Polynomial kernel with degree = 1:This is effectively a linear kernel and behaves similarly. - (d) Sigmoid kernel:Typically
used in neural networks but less effective for well-defined circular boundaries
compared to RBF.
Hence, the correct answer is (c) — the Radial Basis Function (RBF) kernel.

Question 3: (1 point) Consider a linear regression model with weight matrix
W and a single training example (x, y). The model’s prediction is given by
ŷ = W x,
and the loss function is defined as
1
(ŷ − y)2 .
2
Which of the following correctly describes one iteration of the stochastic gradient
descent update for W with learning rate α?
L(W ) =

(a) W ← W − α(ŷ − y)xT
(b) W ← W + α(ŷ − y)xT
(c) W ← W − αx(ŷ − y)
(d) W ← W − α(ŷ − y)
Answer: (a) W ← W − α(ŷ − y)xT
Explanation:
To derive the correct stochastic gradient descent (SGD) update rule for W ,
we need to compute the gradient of the loss function with respect to W .
2

Variant 0
Step 1: Compute the Loss Function Gradient
The given loss function is:
1
(ŷ − y)2
2
Since the model’s prediction is ŷ = W x, we can substitute this into the loss
function:
L(W ) =

1
(W x − y)2
2
Now compute the gradient of L(W ) with respect to W :
L(W ) =

∂L(W )
∂ 1
=
(W x − y)2
∂W
∂W 2
By the chain rule:
∂L(W )
∂(W x)
= (W x − y)
∂W
∂W
x)
T
Since ∂(W
∂W = x (differentiating each element individually), we have:

∂L(W )
= (W x − y)xT = (ŷ − y)xT
∂W
Step 2: Perform the Gradient Descent Update
The SGD update rule is:
W ←W −α

∂L(W )
∂W

Substituting the computed gradient:
W ← W − α(ŷ − y)xT
Step 3: Identify the Correct Answer
This matches option (a):
W ← W − α(ŷ − y)xT
Why Other Options Are Incorrect:
- (b)Incorrect because it adds the gradient instead of subtracting it. - (c) Incorrect because the term x should be transposed to match the correct dimensions
for matrix operations. - (d) Incorrect because it omits the crucial xT term
required to align the gradient’s dimensions with W .
Thus, the correct answer is (a).

3

Variant 0
Question 4: (2 points) After applying a regularization penalty in linear
regression, you find that some of the coefficients of w are zeroed out. Which of
the following penalties might have been used? Note: The L0 norm is defined
as:
X
∥w∥0 =
I(wi ̸= 0)
i

(a) L0 norm
(b) L1 norm
(c) L2 norm
(d) either (a) or (b)
Answer: (d) either (a) or (b)
Explanation:
In linear regression with regularization, the choice of regularization penalty
directly affects the behavior of the model’s coefficients. Let’s analyze each option
to understand why the correct answer is (d).
—
(a) L0 Norm
The L0 norm is defined as:
∥w∥0 =

X

I(wi ̸= 0)

i

The L0 norm directly counts the number of non-zero elements in the weight
vector w. Minimizing the L0 norm explicitly encourages sparsity by forcing as
many coefficients as possible to be zero. While this approach effectively zeroes
out some coefficients, it is computationally challenging to optimize due to its
combinatorial nature.
—
(b) L1 Norm (Lasso Regularization)
The L1 norm is defined as:
∥w∥1 =

X

|wi |

i

L1 regularization introduces a sharp corner at zero in its loss gradient. This
property creates a strong tendency to shrink some coefficients exactly to zero,
effectively performing feature selection. L1 regularization is often preferred due
to its convex nature, making it computationally efficient.
—
4

Variant 0
(c) L2 Norm (Ridge Regularization)
The L2 norm is defined as:
∥w∥22 =

X

wi2

i

L2 regularization penalizes large coefficients but does not enforce exact zeros.
Instead, it tends to shrink coefficients continuously without forcing any of them
to be zero. Therefore, L2 regularization alone does not produce sparse models.
—
Conclusion:
- Both the L0 and L1 norms are known to enforce sparsity by zeroing out some
coefficients. - The L2 norm does not exhibit this property. - Since the question
asks for penalties that might have caused some coefficients to be zeroed out, the
correct answer is:
(d) either (a) or (b)

Question 5: (1 point) In building a linear regression model for a particular
data set, you observe the coefficient of one of the features having a relatively
high negative value. This suggests that
(a) This feature has a strong effect on the model
(b) This feature does not have a strong effect on the model (should be ignored)
(c) It is not possible to comment on the importance of this feature without
additional information, such as feature scaling and correlation with other
predictors.
(d) Removing this feature will not affect the model performance
Answer: (c) It is not possible to comment on the importance of this feature
without additional information

Question 6: (1 point) Consider a binary classification problem in which
the label +1 is rare. You have learned a binary classifier h : X → {±1} from
some training data. On a test set of 100 data points, the classifier’s predictions
and the true labels are as follows:
ActualLabels
−1
+1

P redictedLabels
−1
+1
75
15
3
7
5

Variant 0
What is the true positive rate (TPR) of the classifier h on the above test
set?
3
(a) 10
7
(b) 10
3
(c) 78
7
(d) 22
7
Answer: (b) 10

Explanation:
The True Positive Rate (TPR) also known as recall or sensitivity is
defined as the proportion of actual positive examples that are correctly classified
as positive. Mathematically, it is given by:
TPR =

True Positives (TP)
True Positives (TP) + False Negatives (FN)

Step 1: Identify the Values from the Confusion Matrix
From the given confusion matrix:
- True Positives (TP) = 7 (P

(the rest is in the file)

## 2021: Midterm

Files: [Intro to ML Midterm 2021.pdf](https://glebpopov.notion.site/14ee746cceef80779d41d8435c90792c)


Fall 2021
Introduction to Machine Learning · Midterm Exam
Innopolis University

Full Name:
General Instructions: Read carefully each exercise and circle the correct answer
on paper. Scratch paper is not allowed under any circumstances. All your work must
be done in these pages.

• You have up to 60 minutes.
• Each question is worth a minimum one point (up to 2 points), for a maximum
possible score of 35 points.
• When multiple choices is applied, points will be deducted for wrong answers.
• Calculators and smart devices are prohibited.
• Mere suspicion of cheating, sharing papers or using any unfair means of aid is
enough to get your test withdrawn.

Introduction to Machine Learning · Fall 2021 · Midterm Exam · V1
1. In regression analysis, the variable that is being predicted is called (1 pt)
A. the independent variable
B. the dependent variable
C. the predictor
D. none of the above
2. Which of the following are correct about regression? (1 pt)
A. The intercept/constant (w0 ) is the mean-Y when X = 0
B. The intercept is the the amount of change in mean-Y when X = 0
C. The coefficient is the mean-Y at a certain value of X
D. The coefficient (w1 ) is the amount of change in mean-Y for every unit increase
in X
3. The logistic model is estimated by way of? (1 pt)
A. Ordinary least squares
B. Maximum likelihood estimation
C. Poisson distribution
D. Negative binomial distribution
4. Suppose, You applied a Logistic Regression model on a given data and got a training
accuracy X and testing accuracy Y. Now, you want to add a few new features in the
same data. Select the option(s) which is/are correct in such a case. Note: Consider
remaining parameters are the same. (1,5 pts)
A. Training accuracy increases
B. Training accuracy decreases or remains the same
C. Testing accuracy increases, decreases, or remains the same
5. Below are the three scatter plots (A,B,C left to right) and hand drawn decision boundaries for logistic regression. What can you conclude from them? (1 pt)

1. The training error in first plot is maximum as compare to second and third plot.
2. The best model for this regression problem is the last (third) plot because it has
minimum training error (zero).
3. The second model is more robust than first and third because it will perform best
on unseen data.
4. The third model is overfitting more as compare to first and second.
5. All will perform same because we have not seen the testing data.
A. 1 and 3
B. 1 and 2
C. 1, 3 and 4
D. 5

Page 1 of 5

Introduction to Machine Learning · Fall 2021 · Midterm Exam · V1
6. Which of the following image is showing the logistic regression cost function for y = 1.
(1 pt)

A. A

B. B

7. Is it possible to apply a logistic regression algorithm on a 3-class Classification problem?
(1 pt)
A. TRUE

B. FALSE

8. Applying the chain rule of partial derivatives to the following equation (2 pts)
N
1 X X
(i)
ε=
wj xj + b − t(i)
2N i=1
j

!2

we will get:
N
∂E
1 X (i) X
(i)
x
wj 0 xj 0 + b − t(i)
=
∂wj
N i=1 j
j0
N
∂E
1 X X
(i)
=
w j 0 xj 0 + b
∂b
N i=1
j0

A. TRUE

!

!

B. FALSE

9. Assume you fit a regression model to predict house prices from squared feet based on
training data set consisting of houses with square feet in the range of 1000 and 2000. In
which interval would we expect predictions to do best? (1 pt)
A. [0, 1000]
B. [1000, 2000]
C. [2000, 3000]
10. Choose all those which can fix “high bias” (1,5 pts)
A. Adding features
B. Trying smaller set of features
C. Getting more training examples
D. Increasing λ (regularization)
E. Decreasing λ (regularization)
11. Suppose a binary classifier produced the following confusion matrix. Find recall and
precision for this classifier, and choose True or False for C. (2 pts)

Actual Positive
Actual Negative

Predicted Positive Predicted Negative
5600
40
1900
2460
Page 2 of 5

Introduction to Machine Learning · Fall 2021 · Midterm Exam · V1
Recall = 0.99
Precision = 0,74
Is this classifier better than the majority classifier? (True or False)
12. Suppose we want to compute 10-Fold Cross-Validation error on 100 training examples.
We need to compute error N1 times, and the Cross-Validation error is the average of the
errors. To compute each error, we need to build a model with data of size N2, and test
the model on the data of size N3. What are the appropriate numbers for N1, N2, N3?
(1 pt)
A. N1 = 10, N2 = 90, N3 = 10
B. N1 = 10, N2 = 80, N3 = 20
C. N1 = 7, N2 = 70, N3 = 30
D. N1 = 9, N2 = 90, N3 = 10
13. Lasso can be interpreted as least-squares linear regression where (1 pt)
A. Weights are regularized with l2 norm
B. Weights have a Gaussian prior
C. Weights are regularized with l1 norm
D. Solution is linear
14. How does the bias-variance decomposition of a ridge regression estimator compare with
that of ordinary least squares regression? (Select one.) (1 pt)
A. Ridge has larger bias and larger variance
B. Ridge has smaller bias and larger variance
C. Ridge has larger bias and smaller variance
D. Ridge has smaller bias and smaller variance
15. In terms of the bias-variance decomposition, a 1-nearest neighbor classifier has
than a 3-nearest neighbor classifier. (Select all correct options) (1,5 pts)
A. Higher variance
B. Higher bias
C. Lower variance
D. Lower bias
16. In a linearly separable case, an SVM with linear kernel will return the same parameters
(w) regardless of the chosen values of C. (1 pt)
A. TRUE

B. FALSE

17. Given the following two networks A and B, answer the following questions (1,5 pts)
100 units

100 units

10 units

100 units

100 units

Network A

Network B

A. Which one has fewer connections? B
B. Which is more prone to overfit? A
C. Which one requires few operations in backprop? B
Page 3 of 5

Introduction to Machine Learning · Fall 2021 · Midterm Exam · V1
18. You want to solve a classification task. You first train your network on 20 samples.
Training converges, but the training loss is very high. You then decide to train this
network on 10,000 examples. Is your approach to fixing the problem correct? (1 pt)
A. Yes
B. No
C. No clear answer
19. Which of the following is/are true about PCA? (1 pt)
1. PCA is supervised method
2. It searches for the directions along which the data has the largest variance
3. Maximum number of principal components ≤ number of features
4. All principal components are orthogonal to each other.
A. 1 and 2
B. 1 and 3
C. 2, 3 and 4
D. All of the above
20. What will be the dimensions of the covariance matrix of the following vectors: (1 pt)


1
6

     


2
3
4
5
,
,
and
7
8
9
10

Ans: 2x2
21. What do you mean by Hard Margin? (1 pt)
A. The SVM allows very low test error in classification
B. The SVM allows very high test error in classification
C. None of the above
22. In SVM, the dimension of the hyperplane depends upon (1 pt)
A. The number of samples
B. The number of features
C. The number of target variables
D. All of the above
23. Which option is true for SVM? (1 pt)
A. The distance of the vectors from the margin is called the hyperplane
B. The loss function that helps maximize the margin is called cross-entropy
C. SVM can solve non-linear classification problems.
D. None of the above
24. In Feedforward ANNs, loops are allowed. (1 pt)
A. TRUE

B. FALSE

25. Provide the correct order of the following steps that we perform when training ANNs.
(1,5 pts)
1. Calculate error between the actual value and the predicted values
2. Reiterate until we have found the optimum parameters
3. Pass an input through the network and get the output
4. Initialize parameters
5. Go to each neuron, which contributes to the error, and update its parameters to
reduce the error
Page 4 of 5

Introduction to Machine Learning · Fall 2021 · Midterm Exam · V1
Ans: 4, 3, 1, 5, 2 or Ans: 4, 2, 3, 1, 5
26. The Naı̈ve Bayes classifier is said to be naı̈ve because: (1 pt)
A. The training is very easy and fast; Just requiring considering each attribute in
each class separately.
B. The test is very straightforward;
C. The assumption that attributes a

(the rest is in the file)

# Citations

1. [IU B23 Academic Materials: Past Papers [EN programs]](https://glebpopov.notion.site/4ef3de0c7e68495b89ef086301361603)
