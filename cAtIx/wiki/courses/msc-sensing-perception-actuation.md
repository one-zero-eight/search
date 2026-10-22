---
type: course
title: "Sensing, Perception & Actuation"
description: "Course covering physical principles of sensors, data analysis, error analysis, image processing, point cloud processing, and sensor fusion for autonomous systems."
resource: "https://eduwiki.innopolis.university/index.php/MSc%3A_Sensing_Perception_Actuation"
tags: ["sensing", "perception", "actuation", "robotics", "sensors", "kalman-filter"]
aliases: ["MSc:Sensing Perception Actuation"]
sources:
  - resource: "https://eduwiki.innopolis.university/index.php/MSc%3A_Sensing_Perception_Actuation"
    id: "7467"
    title: "MSc: Sensing Perception Actuation"
    last_modified: "2022-08-29T08:45:17Z"
generated:
  by: "catix-wiki/0.1 (local)"
  at: "2026-10-22T00:42:25+00:00"
status: draft
stale_after: "2024-08-28T08:45:17+00:00"
prerequisites: [{"course": "/courses/bsc-physics-i.md", "as_written": "CSE402 — Physics I (Mechanics)"}, {"course": "/courses/bsc-physics-ii.md", "as_written": "CSE410 — Physics II - Electrical Engineering", "via": "model"}, {"course": "/courses/bsc-mathematicalanalysis-i.md", "as_written": "CSE201 — Mathematical Analysis I", "via": "model"}, {"course": "/courses/bsc-mathematicalanalysis-ii.md", "as_written": "CSE203 — Mathematical Analysis II", "via": "model"}, {"course": "/courses/msc-analyticalgeometryandlinearalgebrai.md", "as_written": "CSE202 — Analytical Geometry and Linear Algebra I"}, {"course": "/courses/bsc-analytic-geometry-and-linear-algebra-ii.md", "as_written": "CSE204 — Analytic Geometry And Linear Algebra II"}, {"course": "/courses/msc-probabilitystatistics.md", "as_written": "CSE206 — Probability And Statistics"}]
taught_by: ["/people/kirillpoletkin.md"]
relations_by: "process:catix-wiki-graph/0.1"
---

# Sensing, Perception & Actuation

## Sensing, Perception & Actuation
- **Course name**: Sensing, Perception & Actuation
- **Code discipline**: R-01
- **Subject area**: Visual Sensors, Data Analysis, Error Analysis, Theory of Measurements, Machine Vision, Inertial Sensors, Internal Sensors, Filtering, Sensor Fusion, Image Processing, Point Cloud Processing

### Short Description
This course covers the following concepts: Physical principles of sensors and their limitations; Measurements, Sensor Calibration, Data and Error analysis; Development of algorithms for image processing, feature extraction and object recognition; 3D Point cloud processing and scene reconstruction; Linear Kalman Filter and Sensor Fusion.

### Prerequisites

#### Prerequisite subjects
- CSE402 — Physics I (Mechanics)
- CSE410 — Physics II - Electrical Engineering
- CSE201 — Mathematical Analysis I
- CSE203 — Mathematical Analysis II
- CSE202 — Analytical Geometry and Linear Algebra I
- CSE204 — Analytic Geometry And Linear Algebra II
- CSE206 — Probability And Statistics

#### Prerequisite topics


### Course Topics
**Course Sections and Topics**

| Section | Topics within the section |
| --- | --- |
| Intro to Sensors. Data and Error Analysis | # Sensors’ classification and Applications <br> # Sensors Characteristics: Dynamic range, Accuracy, Signal & Noise ratio <br> # Error analysis: Systematic vs Statistical Errors, Accuracy and Precision, Central Limit Theorem, 3 sigma rule, outliers <br> # Sensor calibration. Direct and indirect measurements <br> # Introduction to Data Analysis: Linear Regression, Least-Squares Fitting, Curve fitting, and Smoothing |
| Perception | # Image sensors: camera matrix, characteristics. Color filters. <br> # Pinhole camera model, lenses and distortions <br> # Camera calibration, Intrinsic and Extrinsic matrices <br> # Video camera: CCTV, IR & thermal imaging camera, Fish eye camera <br> # Stereo vision: Stereosystem, Stereogeometry <br> # Image rectification, Disparity map, 3D Point Cloud from Stereo <br> # Point clouds processing, 3D reconstruction, Structure-from-Motion (SfM) <br> # LIDAR: Laser rangefinders. Laser-camera systems. Airborne LIDAR <br> # Depth, TOF, RGBD camera, MS Kinect: characteristics and calibration <br> # SONAR. Piezocrystalls. Doppler effect. Doppler radar. <br> # Acoustic sensor systems. Sound spectrogram <br> # mm-RADAR, Long-Range RADAR, Short-range RADAR |
| Sensor Fusion and Filtering | # Filtering <br> # Linear Kalman Filter (KF) <br> # Sensor Fusion <br> # Linear Kalman Filter vs Extended KF <br> # MoCap system <br> # Multicamera system |
| Actuators and Passive Sensors: GPS, IMU and Inertial Sensors | # GPS, differential GPS (dGPS) <br> # Inertial sensors: IMU, accelerometers, gyroscopes <br> # Magnetometers <br> # Internal sensors: position, velocity, torque & force sensors, encoders <br> # MEMS for robot applications <br> # Actuators <br> # Smart and Intelligent Sensors |
### Intended Learning Outcomes (ILOs)

#### What is the main purpose of this course?
One of the most important tasks of an autonomous system of any kind is to acquire knowledge about its environment. This is done by taking measurements using various sensors and then extracting meaningful information from those measurements. In this course we present the most common sensors used in mobile robots and autonomous systems and then discuss strategies for extracting information from the sensors.

#### ILOs defined at three levels

##### Level 1: What concepts should a student know/remember/explain?
By the end of the course, the students should be able to ...
- familiar with physical and sensing principles for Camera, Stereo vision, LIDAR, SONAR, Time-of-Flight camera, GPS, actuators, inertial and internal sensors
- acquainted with measurements and error analysis, data analysis, and sensor calibration
- familiar with triangulation principle, basics of image and point cloud processing methods

##### Level 2: What basic practical skills should a student be able to perform?
By the end of the course, the students should be able to ...
- Understand how to remove systematic error and how to decrease statistical error
- Recover depth information from stereo vision, structure-from-light and TOF cameras
- Explain how Linear Regression and Least-Squares Fitting allow to minimize measurement errors

##### Level 3: What complex comprehensive skills should a student be able to apply in real-life scenarios?
By the end of the course, the students should be able to ...
- Calibrate sensors to remove systematic errors
- Extract meaningful information from sensor’s data (features, objects, depth and accuracy information)
- Detect objects from 2D images
- Recover scene from 3D Point Cloud
- Filter noisy data
- Match models to datasets
- Fuse sensor’s data and apply Kalman Filtering
- Apply GPS, camera, LIDAR, RADAR, SONAR, IMU, Stereo camera for a mobile robot localization 
### Grading

#### Course grading range
| Grade | Range | Description of performance |
| --- | --- | --- |
| A. Excellent | 85-100 | - |
| B. Good | 70-84 | - |
| C. Satisfactory | 55-69 | - |
| D. Poor | 0-54 | - |

#### Course activities and grading breakdown
| Activity Type | Percentage of the overall course grade |
| --- | --- |
| Labs/seminar classes | 10 |
| Home assignments | 40 |
| Interim performance assessment | 15 |
| Quizzes | 20 |
| Exams | 15 |

#### Recommendations for students on how to succeed in the course


### Resources, literature and reference materials

#### Open access resources
- Roland Siegwart, Illah R. Nourbakhsh, and Davide Scaramuzza. Introduction to Autonomous Mobile Robots, MIT press, 2011.
- M. Chli, D. Scaramuzza, R. Siegwart, et al. Autonomous Mobile Robots, ETH Zurich, 2017, http://www.asl.ethz.ch/education/lectures/autonomous_mobile_robots.html
- Jacob Fraden. Handbook of modern sensors: physics, designs, and applications. Springer, 2010
- Alonzo Kelly. Mobile Robotics: Mathematics, Models, and Methods. Cambridge University Press, 2013
- Horn, Berthold K. P. Robot Vision. Cambridge, MA: MIT Press /McGraw-Hill, March 1986
- H. Choset, K. M. Lynch, et. al. “Principles of Robot Motion: Theory, Algorithms, and Implementations”, MIT press, 2005
- Gregory Dudek and Michael Jenkin. Computational Principles of Mobile Robotics, 2nd ed., Cambridge University Press, 2010

#### Closed access resources


#### Software and tools used within the course
 
## Teaching Methodology: Methods, techniques, & activities

### Activities and Teaching Methods
**Activities within each section**

| Learning Activities | Section 1 | Section 2 | Section 3 | Section 4 |
| --- | --- | --- | --- | --- |
| Development of individual parts of software product code | 1 | 1 | 1 | 1 |
| Homework assignments | 1 | 0 | 0 | 0 |
| Midterm evaluation | 1 | 1 | 1 | 1 |
| Testing (written or computer based) | 1 | 1 | 1 | 1 |
| Discussions | 1 | 1 | 1 | 1 |
| Homework and group projects | 0 | 1 | 1 | 1 |
### Formative Assessment and Course Activities

#### Ongoing performance assessment

##### Section 1
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | UAV flies through the strong wind and begins to oscillate. The pitch angle change was measured with the gyro during a few seconds. Exclude from the consideration rare random deviation (outliers) and estimate the true value of the roll angle. Calculate the confidence interval of error for 99.9% confidence level. Consider that the gyro errors are normally distributed, except for the rare random deviations. Proper regression technique should be applied so as to fit the data while excluding rare random deviations. | 1 |
| Question | UAV flies through the strong wind and begins to oscillate. The roll angle change was measured with the gyro during a few seconds. Exclude from the consideration rare random deviation (outliers) and estimate the true value of the roll angle. Calculate the confidence interval of error for 95% confidence level. Consider that the gyro errors are normally distributed, except for the rare random deviations. Proper regression technique should be applied so as to fit the data while excluding rare random deviations. | 1 |
| Question | The human CoM (center of mass) during the walking has been measured with Kinect sensors. Estimate the true value of the x-component of acceleration. For example, you can use a moving average filter. Calculate the confidence interval of error for 95% confidence level. Consider that the errors are normally distributed, except for the rare random deviations. Proper regression technique should be applied so as to fit the data while excluding rare random deviations. | 1 |
| Question | UAV performs loop-the-loop. The pitch angle change was measured with the gyro during 1 seconds. Exclude from the consideration rare random deviation (outliers) and estimate the true value of the roll angle. Calculate the confidence interval of error for 95% confidence level. Consider that the gyro errors are normally distributed, except for the rare random deviations. Proper regression technique should be applied so as to fit the data while excluding rare random deviations. | 1 |
| Question | You are given a dataset (select the dataset with corresponds to your ID), includes some data points in R<math>{\textstyle ^{3}}</math> . Your task is to estimate whether it represents a plane, line or something else. You must use the RANSAC for this task. Explain the way you selected your minimal sample set, number of iteration and the threshold level? It would be better to provide an analytical solution derivation as well as graphical interpretation. | 1 |
| Question | Inside the right hand of the AR-601 robot there is an accelerometer. Engineers fixed the robot on the crane and went for a lunch. Robot was swinging by inertia for a few minutes. Engineers came back after lunch and read the data from accelerometer. Help them to understand what they measured. Exclude from the consideration rare random deviation (outliers) and estimate the true value of the y-component of acceleration. Calculate the confidence interval of error for 99.9% confidence level. Consider that the accelerometer errors are normally distributed, except the rare random deviations. Proper regression technique should be applied so as to fit the data while excluding rare random deviations. | 1 |
| Question | Introduction to Confidence Interval (CI) | 0 |
| Question | Introduction to Linear Regression | 0 |
| Question | Introduction to Logistic Regression | 0 |
| Question | Introduction to RANSAC | 0 |
| Question | Introduction to Maximum Likelihood Estimation (MLE) | 0 |
##### Section 2
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | Place a 3d object such as a cube or a cylinder or something you like in an appropriate way with respect to Kinect. Then you are going to use Kinect 2 in order to get the depth map. Associate depth map with RGB information in order to isolate the object, which is to be extracted from the ground plane and other background. You may have to use RANSAC or some other algorithms to extract the object and find the center point of the object in the 3D space. It may be relative to Kinect or any known position in the world. | 1 |
| Question | Calibrate a camera (your phone or computer camera should be utilized) using the chessboard pattern. It’s logically to switch off the auto focus mode of the camera, if it is enabled. The number of images should be at least 30 (with different chessboard positions). Obtain the intrinsic and extrinsic parameters. Once you have calibrated your camera, store intrinsic and extrinsic parameters. Then take a photo of some object (for example, a cup) using the calibrated camera, estimate the height and width of the selected object using both a ruler and an image from the calibrated camera. Calculate the distance between the camera image plane and the selected object. | 1 |
| Question | The provided dataset contains left and right images in two different folders with the same name. For this task please select image pair corresponds to your id (0000[Id].png). You need to use 8 point algorithm in order to find the fundamental matrix. For the initial key points detection (minimum 8 corresponding points) you can either do it manually or use any key points detection technique. Next step is to estimate the disparity map for the selected image pair. You may assume the baseline of the stereo camera as the 10cm and focal length of both the left and right side cameras as 2.8mm. If you need any additional assumptions, please elaborate them in the report. | 1 |
| Question | Build the hardware, and program and implement suitable code, for a simple color sensor suitable for an application of interest to you. An example of the principle you might employ is a hardware where the component in the center is a photo transistor; it detects light – with varying sensitivity – across the full visible spectrum, a little into the ultraviolet, and into the infrared to a little. Basic idea of the color meter is that LEDs are turned on and off in sequence, and the correspondingly detected signals are recorded. When all the LEDs are off the ambient (background) is recorded. In this way a ”signature” of any particular color patch placed in a location that is illuminated by the LEDs and seen by the phototransistor is generated. You could then, for example, compare the signature that you obtain from an ”unknown” item with the signatures of various items that you previously stored in a ”library”, hence identify (with some quantifiable degree of certainty) the ”unknown” item. Even If you do use this principle, you don’t have to use exactly these components. In your Arduino kit you probably have a variety of LEDs, probably including one ”tri-color” LED, and a phototransistor that you can use. | 1 |
| Question | CCD vs CMOS technologies | 0 |
| Question | Bayer mosaic filter vs Faveon capture color filter | 0 |
| Question | Pinhole camera model | 0 |
| Question | Stereo vision, Disparity map and Stereo image rectification | 0 |
| Question | Multiple Camera Vision | 0 |
| Question | Structure-from-Motion | 0 |
| Question | ToF and multi-frequency phase-shift LIDAR technologies | 0 |
| Question | SONAR sensing, SONAR transducer and transmitter | 0 |
| Question | Distributed acoustic sensing (DAS) and applications | 0 |
| Question | Doppler mm-wave RADAR | 0 |
##### Section 3
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | UAV flies through the strong wind and begins to oscillate. The pitch angle change was measured with the gyro during a few seconds. Estimate proper trajectory for the pitch angle while considering the gyro reading are normally distributed by using Kalman filter. | 1 |
| Question | UAV flies through the strong wind and begins to oscillate. The roll angle change was measured with the gyro during a few seconds. Estimate proper trajectory for the roll angle while considering the gyro reading are normally distributed by using Kalman filter. | 1 |
| Question | UAV performs loop-the-loop. The pitch angle change was measured with the gyro during a few seconds. Estimate proper trajectory for the pitch angle while considering the gyro reading are normally distributed by using Kalman filter. | 1 |
| Question | The human CoM (center of mass) during the walking has been measured with Kinect sensors. Estimate proper trajectory for the human CoM movement while considering reading are normally distributed by using Kalman filter. | 1 |
| Question | Inside the right hand of the AR-601 robot there is an accelerometer. Engineers fixed the robot on the crane and went for a lunch. Robot was swinging by inertia for a few minutes. Engineers came back after lunch and read the data from accelerometer. Help them to understand what they measured. Estimate proper trajectory for the accelerometer reading while considering reading are normally distributed by using Kalman filter. | 1 |
| Question | Expected Value and Variance of a Random Variable. Gaussian Distribution. | 0 |
| Question | One Dimensional Kalman Filter | 0 |
| Question | The main stages of Linear Kalman Filter (KF): Prediction and Update steps. KF initialization | 0 |
| Question | Linear Kalman Filter vs Extended KF | 0 |
| Question | KF, EKF, UKF and Particle Filter - main features and differences | 0 |
| Question | Motion Capture (MoCap) system | 0 |
| Question | Multicamera system | 0 |
##### Section 4
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Question | Take your smart phone and run for at least 100 meters with a constant speed. Your task is to estimate the trajectory where you ran with your phone which may be used to get some sensor reading such as accelerometer, gyroscope, GPS sensor and so on. You should use multidimensional Kalman filter with sensor fusion to solve this task. In the report clearly explain all the assumptions you made. | 1 |
| Question | Inside the right hand of the AR-601 robot there is an accelerometer. Engineers fixed the robot on the crane and went for a lunch. Robot was swinging by inertia for a few minutes. Engineers came back after lunch and read the data from accelerometer. Help them to understand what they measured. Estimate proper trajectory for the accelerometer reading while considering reading are normally distributed by using Kalman filter. | 1 |
| Question | GPS vs differential GPS (dGPS) | 0 |
| Question | 9DOF IMU | 0 |
| Question | Optical vs Mechanical Gyroscope | 0 |
| Question | Laser vs Fiber Gyroscope | 0 |
| Question | Absolute vs Incremental Encoders | 0 |
| Question | MEMS for robot applications | 0 |
| Question | What are the Smart and Intelligent Sensors? | 0 |
#### Final assessment
**Section 1**
1. Why do mobile robots need sensors?
1. Why do mobile robots need actuators?
1. What are the risks of not calibrating the robot sensors?
1. Why do we need to calibrate sensors?
1. What’s the difference between external and internal robot sensors?
1. What is the difference between Statistical and Systematic errors?
1. What is the difference between accuracy and precision?
1. Which type of error influences on accuracy and which type influences on precision?
1. Can we eliminate stochastic errors?
1. Can we eliminate systematic errors?
1. What is the difference between direct and indirect measurements?
1. How can we determine the uncertainty of indirect measurements?
1. Which type of error can be brought into measurements, if you did not perform the sensor calibration?
1. Sensors’ data contain rare random deviations (outliers), which are characterized a priori as unreliable values with unknown distribution law. Which algorithm can we apply for eliminating these unreliable values?
1. It is known that the instrumental error of the HOKUYO URG-04LX-UG01 laser rangefinder (LRF) is about ± 3% of measuring value. Let’s consider a quadcopter with the LRF, which flies in a corridor, making stops each 1 m to map the environment with the rangefinder. It is known that due to the quadcopter fluctuations, the total LRF measurement error increases up to ± 10% from the measurement value. How long does the quadcopter need to stay at each stop to map the environment with minimal error, if LRF performs 10 scans/sec?
1. Why do we use the regression analysis?
1. When we speak about regression data, what do we mean?
1. Can we use linear regression for variables with strong nonlinear relationships?
1. Can a least-squares fit be applied for polynomials?
1. Can we apply regression analysis for noisy wave described by sine function?
1. What is outlier?
1. What is the main idea of RANSAC?
**Section 2**
1. What’s the difference between CCD and CMOS?
1. Which advantages of CMOS technology do you know?
1. What’s the difference between Bayer mosaic filter and Faveon capture filter?
1. Why does the Bayer mosaic array have in two times more green color filters if compare with red and blue ones?
1. Why do we need to calibrate camera?
1. Which subjects or structures can we use for camera calibration?
1. What’s the difference between intrinsic and extrinsic parameters?
1. What’s the difference between radial and tangential distortions?
1. Can we calibrate a camera with autofocusing?
1. What is the pinhole camera model?
1. Does the pinhole camera model contain lens?
1. What’s the name of calibration parameters that reproject 3D world coordinate system to the 3D camera’s coordinate system?
1. What’s the name of calibration parameters that transform the 3D camera’s coordinates into the 2D image coordinates?
1. What is the optical center of a camera?
1. Which technology is widely used for producing a megapixel camera? CMOS or CCD?
1. What is the matrix name, which concludes focal length and a skew coefficient?
1. What are the applications of stereo vision?
1. What is the stereo vision?
1. Why do we calibrate the stereo camera system?
1. What is the output of stereo vision?
1. How do we get 3D reconstruction from binocular stereo?
1. Which visual cues (patterns) can provide 2D image with 3D information?
1. What is the triangulation?
1. What is the Stereo Image Rectification?
1. Why do we take multiple pairs of chessboard images from different angles during calibration?
1. What is the meaning of use an asymmetric chessboard as a calibration pattern?
1. Can we store the calibration images in a format with lossy compression?
1. What is the connection between anaglyph image and stereo image rectification?
1. What is the disparity map in stereo vision reconstruction process?
1. What is the result of Stereo Vision Scene Reconstruction?
1. What’s the difference between Time-of-flight & Structured-light sensors?
1. Give short description of Depth Measurement Techniques for Stereo Vision, ToF cameras, Kinect and LIDAR.
1. What is the motivation to use 3D sensors?
1. Which 3D sensing applications do you know?
1. What are the disadvantages of Multiple Camera Vision?
1. What is the ToF camera?
1. What’s the difference between ToF camera and scanning LIDAR?
1. What’s the difference of ToF imaging for Pulsed Modulation and Continuous Wave Modulation?
1. What do flying pixels mean?
1. What is the ToF Depth inhomogeneity?

1. What are the sources of systematic error for depth sensors?
1. Describe the main principle of Structured Light Imaging (e.g. for Kinect).
1. What’s the difference between LIDAR and Kinect?
1. What are the basic camera elements?
1. What is the focal length?
1. What are the Field of View and Angle of View?
1. Which Angle of View and Focal Length do you have at Zoom In?
1. What is the Depth of Field (DoF)?
1. What is Macro Photography (Close-up shooting) mode?
1. What is Fish eye camera?
1. What is Fish eye camera configuration concept?
1. What are the main characteristics of IR / thermal imaging camera?
1. What is the LIDAR?
1. What does a conventional LIDAR system involve?
1. What is the difference between incoherent and coherent LIDAR detection schemes?
1. How does LIDAR work?
1. Which optical components can LIDAR conclude?
1. What’s the advantage of low energy micro pulse LIDAR?
1. What is the difference between ToF and multi-frequency phase-shift LIDAR technologies?
1. Which achievements can we expect from LIDAR industry in the nearest future?
1. Give examples of LIDAR applications in surveillance and security.
1. What is the motivation to use LIDARs at the Airborne Laser Scanning?
1. What is SONAR?
1. How does SONAR work?
1. What are the main SONAR characteristics?
1. How can objects or surfaces’ features influence on SONAR sensing?
1. How does SONAR sensing change with work frequency increase?
1. What is the character of directional diagram for typical SONAR?
1. What are SONAR applications?
1. What is the typical material for the modern SONAR transducers?
1. How does piezo crystal work as the SONAR transducer and transmitter?
1. What is the piezoelectric effect? (direct and inverse)
1. How do Level Sensors work in tanks or cisterns?
1. How does Echo Sounders work?
1. What is the Doppler effect?
1. What is Distributed acoustic sensing (DAS)?
1. How can Distributed acoustic sensing (DAS) sense the acoustic signal?
1. What is Rayleigh scattering?
1. How does Doppler radar work?
1. Give examples of Distributed acoustic sensing (DAS) applications.
1. What is the mm-wave RADAR?
1. How does mm-wave RADAR work?
**Section 3**
1. What’s the difference between least square fitting and Kalman filtration?
1. What’s the difference between Conventional and Recursive Estimating the Mean?
1. What’s the difference between filtration and smoothing?
1. Does averaging deal with smoothing or filtration?
1. What are the advantages of Kalman filter implementation?
1. What can be the applications of Kalman filter?
1. What are the maximal and minimal values of Kalman gain (Kalman coefficient) and what they mean?
1. What is the difference between Kalman Filter (KF) and Extended Kalman Filter (EKF)?
1. The observations are processed using Kalman Filter. Imagine that State has 5 elements, and 1 observation data type. What is the size of the estimation error covariance matrix?
1. Describe two main steps of Kalman filter.
1. With what type of random variable distribution Kalman filter works?
1. What is the sensor fusion?
1. What is the advantage of sensor fusion?
1. Give an example of obtaining qualitatively new information from Sensor Fusion.
1. Give examples of Sensor fusion applications.
1. Why do we build multi-sensor systems instead of using a single sensor?
1. What is motivation to use Sensor Fusion in Robotics?
1. Why don’t we prefer averaging sensors’ data instead of fusion?
1. How can we combine (process) sensors’ data to get the best estimate of measurement value?
1. Can we fuse the sensors of different types with different measurement techniques and accuracies?
1. Why do we present the sensor’s models in terms of probability distributions?
1. What is the mean of a random variable? What is the variance of a random variable?
1. What is the Probability Density Function (PDF)? What is the Multi-modal Probability Density Function?
1. What are the advantages of using Gaussian PDF?
1. What does the central limit theorem state?
1. Let’s merge two Gaussian noise models. Is the standard deviation of the merged model bigger than for the initial noise models?
1. Having the sensor fusion, in which case the data averaging can be effective?
1. What’s the difference between the sensor fusion by Kalman Filter and Particle Filter?
1. Can we process non Gaussian Noise by Linear Kalman Filter?
**Section 4**
1. What can GPS module do?
1. Is GPS module typically able to work indoor?
1. What does the altimeter module include?
1. What can an altimeter module do?
1. What is inertia? What is inertial sensors?
1. Which types of inertial sensors do you know?
1. Which are two basic classes of rotation sensing gyros do you know?
1. What is the difference between Rate gyros and Rate integrating gyros?
1. What is IMU? What can it do?
1. What does accelerometer measure?
1. Can accelerometers measure the gravity?
1. What’s the difference between accelerometer and gyro?
1. What can 3D gyro measure?
1. Why is built-in temperature sensor used in modern gyros or accelerometers?
1. Why is embedded power down or sleep functions used in modern gyros?
1. What is the magnetometer?
1. What can magnetometer (compass module) do?
1. How does MEMS accelerometer work?
1. Which material is used for MEMS accelerometer’ spring and mass?
1. What is the Coriolis force?
1. Give examples of the Coriolis force appearance.
1. Does MEMS gyroscope contain of rotating mechanical parts?
1. How does MEMS gyro work?
1. Which optical gyros do you know?
1. Which components do you know in Laser Gyro?
1. How does laser gyro work?
1. What is Sagnac effect?
1. What is the advantages and disadvantages of Laser Gyro?
1. What is the difference between Ring-Laser Gyro (RLG) and Fibre optic gyro (FOG)?
1. Which position robot sensors do you know?
1. Which sensors can be used to measure mechanical quantities?
1. How do linear potentiometers work?
1. How do rotary potentiometers work?
1. What are the strain gauges?
1. What is the difference between strain gauges and tensometers?
1. How does differential pressure sensor work?
1. How do Force Measurement Resistors (FSR) work?
1. What are the Force Measurement Resistors (FSR)?
1. How do Capacitive sensors work?
1. What is the difference in position (displacement) measurements of conventional capacitive sensors and differential capacitive sensors?
1. Compare capacitive and inductive position sensors.
1. What is the principle of Inductive position sensor’s work?
1. What is piezoelectricity?
1. How does sensitivity depend on frequency in a typical piezoelectric sensor?
1. What does optical encoder measure?
1. What are the main components of optical encoder?
1. Can incremental encoders save angle position when power is switched off?
1. What is the difference between incremental and absolute optical encoders?
1. What is the Gray Code?
1. Does it have sense to apply the Gray code for incremental encoders?
1. What is the Resolver?
1. What is the difference between Resolvers and Optical Encoders?
1. What is MEMS?
1. What is the motivation to use MEMS?
1. Which materials can be used in MEMS fabrication?
1. Which basic MEMS fabrication techniques do you know?
1. What is the right order of fabrication process (etching, patterning, deposition)?
1. What is the patterning?
1. What is the etching?
1. Which types of micromachining do you know?
1. Which actuators do you know?
1. Give the examples of MEMS applications.
1. What are the typical MEMS dimensions?
1. What are the Smart sensors?
1. What is the motivation in Smart sensors?
1. What is the advantages of Smart sensors?

#### The retake exam
**Section 1**

**Section 2**

**Section 3**

**Section 4**

<!-- catix:relations -->
## Relations

- Prerequisites: [Physics I (mechanics)](/courses/bsc-physics-i.md) (CSE402 — Physics I (Mechanics)); [BSc: Physics II](/courses/bsc-physics-ii.md) (CSE410 — Physics II - Electrical Engineering, matched by the model); [BSc: Mathematical Analysis I](/courses/bsc-mathematicalanalysis-i.md) (CSE201 — Mathematical Analysis I, matched by the model); [BSc: Mathematical Analysis II](/courses/bsc-mathematicalanalysis-ii.md) (CSE203 — Mathematical Analysis II, matched by the model); [Analytical Geometry and Linear Algebra I](/courses/msc-analyticalgeometryandlinearalgebrai.md) (CSE202 — Analytical Geometry and Linear Algebra I); [BSc: Analytic Geometry And Linear Algebra II](/courses/bsc-analytic-geometry-and-linear-algebra-ii.md) (CSE204 — Analytic Geometry And Linear Algebra II); [Probability and Statistics](/courses/msc-probabilitystatistics.md) (CSE206 — Probability And Statistics)
- Taught by: [Kirill Poletkin](/people/kirillpoletkin.md)
<!-- /catix:relations -->

# Citations

1. [MSc: Sensing Perception Actuation](https://eduwiki.innopolis.university/index.php/MSc%3A_Sensing_Perception_Actuation), revision 7467
