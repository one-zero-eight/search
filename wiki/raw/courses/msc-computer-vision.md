---
type: course
title: "Computer Vision"
description: "Course covering computer vision techniques, classical and deep learning models, image processing, and practical implementation of models for real-world problems."
resource: "https://eduwiki.innopolis.university/index.php/MSc%3A_Computer_Vision"
tags: ["computer-vision", "course", "deep-learning", "image-processing", "robotics"]
aliases: ["MSc:Computer Vision"]
sources:
  - resource: "https://eduwiki.innopolis.university/index.php/MSc%3A_Computer_Vision"
    id: "7465"
    title: "MSc: Computer Vision"
    last_modified: "2022-08-29T08:43:40Z"
generated:
  by: "catix-wiki/0.1 (local)"
  at: "2026-10-22T00:29:56+00:00"
status: draft
stale_after: "2024-08-28T08:43:40+00:00"
---

# Computer Vision

- **Course name**: Computer Vision
- **Code discipline**: R-03
- **Subject area**: 

### Short Description
This course covers the following concepts: Computer vision techniques; Classical and deep learning models.

### Prerequisites

#### Prerequisite subjects


#### Prerequisite topics


### Course Topics
**Course Sections and Topics**

| Section | Topics within the section |
| --- | --- |
| Image Acquisition and Basic Image Processing | # Computer vision in action <br> # The Human Vision System <br> # Optical Illusions <br> # Sampling and Quantization <br> # Image Representation <br> # Colour Spaces |
| Image Filtering and Binary Vision | # Image noise <br> # Convolutions and kernels <br> # Smoothing and blurring <br> # Thresholding and histograms <br> # Morphological operations <br> # Gradients and Edge detection |
| Feature Extractors and Descriptors | # Histogram of Gradients (HoG) <br> # Scale-invariant feature transform (SIFT) <br> # Harris corner detector <br> # Template matching <br> # Bag of visual words <br> # Face Detection and Recognition (Viola Johns) |
| Deep learning models for computer vision | # You Only Look Once: Unified, Real-Time Object Detection (YOLO) <br> # Generative Adversarial Networks (GAN) <br> # Fully Convolutional Networks (FCN) for semantic segmentation <br> # Multi Domain Network (MDNet) for object tracking <br> # Generic Object Tracking Using Regression Networks (GOTURN) for object tracking |
### Intended Learning Outcomes (ILOs)

#### What is the main purpose of this course?
This course provides an intensive treatment of a cross-section of the key elements of computer vision, with an emphasis on implementing them in modern programming environments, and using them to solve real-world problems. The course will begin with the fundamentals of image processing and image filtering, but will quickly build to cover more advanced topics, including image segmentation, object detection and recognition, face detection, content-based image retrieval, artificial neural networks, convolutional neural networks, generative adversarial networks and much more. A key focus of the course is on providing students with not only theory but also hands-on practice of building their computer vision applications.

#### ILOs defined at three levels

##### Level 1: What concepts should a student know/remember/explain?
By the end of the course, the students should be able to ...
- Robots visual perception strategies
- Significant exposure to real-world implementations
- To develop research interest in the theory and application of computer vision

##### Level 2: What basic practical skills should a student be able to perform?
By the end of the course, the students should be able to ...
- Suitability of different computer vision models in different scenarios
- Ability to choose the right model for the given task

##### Level 3: What complex comprehensive skills should a student be able to apply in real-life scenarios?
By the end of the course, the students should be able to ...
- Hands on experience to implement different models to know inside behavior
- Sufficient exposure to train and deploy model for the given task
- Fine tune the deployed model in the real-world settings 
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
| Interim performance assessment | 50 |
| Exams | 30 |

#### Recommendations for students on how to succeed in the course


### Resources, literature and reference materials

#### Open access resources
- Handouts supplied by the instructor
- Materials from the interment and research papers shared by instructor

#### Closed access resources


#### Software and tools used within the course
 
## Teaching Methodology: Methods, techniques, & activities

### Activities and Teaching Methods
**Activities within each section**

| Learning Activities | Section 1 | Section 2 | Section 3 | Section 4 |
| --- | --- | --- | --- | --- |
| Development of individual parts of software product code | 1 | 1 | 1 | 1 |
| Homework and group projects | 1 | 1 | 1 | 1 |
| Midterm evaluation | 1 | 1 | 1 | 1 |
| Testing (written or computer based) | 1 | 1 | 1 | 1 |
| Discussions | 1 | 1 | 1 | 1 |
### Formative Assessment and Course Activities

#### Ongoing performance assessment

##### Section 1
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | What are the color spaces and where it’s used? | 1 |
| Question | What are the primary and secondary colors? | 1 |
| Question | How image is formed into computers? | 1 |
| Question | How you will convert the RGB to grayscale images | 1 |
| Question | Loading and plotting the images in python environment | 0 |
| Question | Convertion of different color spaces | 0 |
| Question | How you find the skin in the images based on the color space models | 0 |
| Question | how to find red eye dot in face using color space models | 0 |
##### Section 2
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | What are the challenges to perform histogram task? | 1 |
| Question | Apply convolutional filter to calculate the response. | 1 |
| Question | What kind of parameters are required to apply different image filters? | 1 |
| Question | How you will compute the gradients of the image and its benefits? | 1 |
| Question | Implement Otsu Method | 0 |
| Question | Implement Sobel, Preweitt filters | 0 |
| Question | Implement Canny edge detector | 0 |
| Question | Perform analysis over the different filtering on the given images | 0 |
##### Section 3
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | How feature extractor works over the given image? | 1 |
| Question | What is the difference between the feature extraction and descriptors? | 1 |
| Question | Explain the examples of descriptors and feature extractors. | 1 |
| Question | Write down the pros and cons of SIFT, HOG and Harris. | 1 |
| Question | Implement template matching algorithm | 0 |
| Question | Implement histogram of gradient using CV2 library | 0 |
| Question | Implement of SIFT for the given task | 0 |
| Question | Implement Harris corner detection | 0 |
| Question | Analysis of different extractors for the given task | 0 |
##### Section 4
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | How classification task is different from detection task? | 1 |
| Question | Explain the transfer learning mechanism for object detection task. | 1 |
| Question | How many types of model exist for object tracking in videos. | 1 |
| Question | Write down the pros and cons of YOLO, FCN and MDNet. | 1 |
| Question | Implement YOLO using transfer learning mechanism | 0 |
| Question | Implement GAN for MNIST dataset | 0 |
| Question | Implement FCN and GOTURN | 0 |
| Question | Analysis of different models for the given task | 0 |
#### Final assessment
**Section 1**
1. How you can distinguish different color spaces?
1. Explain and provide the reason for the blind spot creation in human eye.
1. In what scenarios computer vision is better than human vision?
1. Write down different robotic application areas where computer vision is applied successfully.
**Section 2**
1. Calculate the kernels for the given images
1. Explain the difference between different filters
1. What is image noise and how it contributes to make the computer vision task difficult?
1. Apply different combination of the filters to achieve the required output of the given image.
**Section 3**
1. How you distinguish different feature extractors and descriptors?
1. What are the possible methods to detect the corners?
1. How corners are useful to help the robotic vision task?
1. How you will patch the different images to construct the map of the location?
**Section 4**
1. What are the loss functions used in YOLO?
1. What are the learnable parameters of FCN for semantic segmentation?
1. How semantic segmentation is different from instance segmentation?
1. Write the application areas for object tracking in robotics.

#### The retake exam
**Section 1**

**Section 2**

**Section 3**

**Section 4**

# Citations

1. [MSc: Computer Vision](https://eduwiki.innopolis.university/index.php/MSc%3A_Computer_Vision), revision 7465
