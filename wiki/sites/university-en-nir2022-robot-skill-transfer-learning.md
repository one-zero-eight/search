---
type: page
title: "EMG- based Grasping force estimation for robot skill transfer learning"
description: "This page presents a research report on EMG-based grasping force estimation for robot skill transfer learning."
resource: "https://innopolis.university/en/nir2022/robot-skill-transfer-learning/"
tags: ["research", "machine-learning", "robotics", "electromyography", "innopolis-university"]
audience: ["teacher", "staff", "public"]
source_kind: website
language: en
section: "site/university"
sources:
  - resource: "https://innopolis.university/en/nir2022/robot-skill-transfer-learning/"
    id: "f54e4ae2c9db"
    title: "EMG- based Grasping force estimation for robot skill transfer learning"
    last_modified: "2026-10-24T23:30:22+00:00"
generated:
  by: "catix-wiki/0.1 sites (local: description, tags and audience only)"
  at: "2026-10-24T23:30:22+00:00"
status: draft
---

# EMG- based Grasping force estimation for robot skill transfer learning

## EMG- based Grasping force estimation for robot

skill transfer learning

In this report, we are discussing a new machine

learning architecture Multi-layer preceptron - random forest

regressors pipeline (MLP-RF model) that stacks two ML regressors of different kind to estimate the generated gripping forces from recorded surface electromyographic activity signals (EMG) during gripping task. The dataset we adopted to evaluate our approach consist of sEMG-Force data profile of 24 sEMG channels placed as 3 bracelets patterns each of 8 electrodes around the forearm muscles while the forces were measured by an ergonomic hand dynamometer was developed. For each finger, the dynamometer features 2 tensiometer sensor points and analogue linearization circuit. The sEMG signals were then filtered and preprocessed to formulate the data frame that will be used to train the proposed ML model. The proposed ML model is a pipeline of stacking 2 different nature ML models, a random forest regressor model (RF regressor) and a multiple layer perceptron artificial neural network (MLP regressor). The models were stacked together, and the outputs were penalized by a Ridge regressor to get the best estimation of both models.

The model was evaluated by different metrics, mean squared

error and coefficient of determination or r² score to improve the model prediction performance. We tuned the most significant hyper parameters of each of the MLP-RF model components using random search algorithm followed by grid search algorithm. Finally, we evaluated our MLP-RF model performance by comparing the prediction results with the state-of-art Recurrent Neural Network (RNN) model and the results shows that the MLP-RF outperforms the state-of-art model.

Read the article

Authors:

Waddah Ali (ITMO University; waddahkh.ali94@gmail.com)

Sergey Kolyubin (ITMO University; s.kolyubin@itmo.ru)

in Proceedings of the Third International Conference Nonlinearity,Information and Robotics 2022, August 24, 2022

- Admission

- For Partners

- About University

Контакты

- 1, Universitetskaya Str., Innopolis, 420500, Russia

- Student Affairs Office 319@innopolis.ru

Пресс-служба

- +7 (843) 203 92 53 доб.117

- News

- Events

- Media

Полезные ссылки

- Ministry of Telecom and Mass Communications of the Russian Federation

- Ministry of Science and Education of the Russian Federation

# Citations

1. [EMG- based Grasping force estimation for robot skill transfer learning](https://innopolis.university/en/nir2022/robot-skill-transfer-learning/), read 2026-10-24
