---
type: regulation
title: "Read the article [NIR_2022_parallel-robot]"
resource: "https://innopolis.university/filespublic/NIR_2022_parallel-robot.pdf"
source_kind: official-document
language: ru
section: "site/university"
sources:
  - resource: "https://innopolis.university/filespublic/NIR_2022_parallel-robot.pdf"
    id: "0d7f4eeba4fb"
    title: "Read the article [NIR_2022_parallel-robot]"
    last_modified: "2026-10-24T23:45:22+00:00"
generated:
  by: "catix-wiki/0.1 regulations"
  at: "2026-10-24T23:45:22+00:00"
extraction: "text layer (opendataloader)"
status: draft
---

# Read the article [NIR_2022_parallel-robot]

On Problem of Position and Orientation Errors of Large-Sized Cable-Driven Parallel Robot

Eugene Marchuk

University of Innopolis Innopolis, Russia 0000-0002-3758-9643

Yaroslav Kalinin

University of Innopolis Innopolis, Russia 0000-0001-6068-0886

Inna Vysotskaya

VSTU Volgograd, Russia 0000-0003-3407-9047

Alexander Maloletov

University of Innopolis Innopolis, Russia 0000-0002-7312-2944

Abstract—The article deals with the application of force sensors to estimate position error of center of mass of the mobile platform of a cable-driven parallel robot. Conditions of deformations of cables and towers of the robot are included in the numerical model and some external disturbances are included too. A method of estimation of the error in positioning via force sensors is sensitive to the magnitude of spatial oscillations of the mobile platform. To reduce torsional vibrations of the mobile platform around vertical axis dynamic damper has been included into the system.

Index Terms—cable, robot, additive, printing, position, orientation, errors, force sensors

I. INTRODUCTION

Cable-driven parallel robots are mechanical systems with parallel topological structure and wire ropes as tendons which move end-effector of the robot. In general, cable-driven robots consist of a cage which is the body of the robot and system of cables with pulleys and winches mounted at this cage. Sometimes elements of the robot can be mounted at the walls of buildings or at any spatial structures. For large-sized robots towers or masts can be used instead of cages to mount winches and pulleys at proximal anchor points, Fig. 1. Cable-driven robots are easily scalable and usually used in practical tasks of moving payloads in large volume of workspace of the robot. Typical applications for large-sized cable-driven parallel robots are warehousing, positioning of large objects, video recording at stadiums and so on. Middle-sized cable-driven parallel robots can be used for example as exosceletons. Small-sized cable-driven parallel robots are usually used for scientific research in laboratories or as prototypes when designing new systems.

II. CABLE-DRIVEN PARALLEL ROBOTS

Cable-driven parallel robots combine simplicity of rope hoists and efficiency of modern automatic control systems. Cable-driven parallel robots are similar with mechanisms of cable cranes which have been used since the end of the XIX century [1]. Moreover, lifting mechanisms as winches were well-known in the ancient world and their basics have not changed significantly up to nowadays [2]. The only differences are sources of power and the lack of automatic control in previous generations. The traditional Korean crane “Geojunggi”

The work has been supported by the RSF (Grant No. 22-29-01618). that has been known at least since XVII century is absolutely the same cable-driven parallel mechanism but running and driving by men [3]. In modern world automatic cable-driven parallel mechanisms have been used in a wide range of practical tasks only since the beginning of the XXI century. One of the first investigations of cable-driven parallel robotic systems appeared in the 80s of the XX century [4]. The first example applied to solving practical problems was the Stewart platform with a cable drive. It was used to stabilize the crane of the NIST Robocrane marine platform [5]. Since the 90s of the XX century many experimental exemplars and prototypes of cable-driven parallel robots have been made, the most famous of them described in scientific articles and reports are: FAL-CON, WARP, SEGESTA, IPANEMA, CableBOT, CoGiRo, see [6] – [11]. Cable-driven parallel robots are also differ by principles of mechanics (underactuated or overactuated), control, operational characteristics (the values of speed and acceleration may reach, respectively, 13 m/s and 43g), linear dimensions (tens of centimeters and tens of meters), ability to carry a payload of various weights, and so on, see [12], [13]. Another problem is modeling of cables. The conventional way is describing wire ropes and cables as catenary with different properties, see [14]. Several methods are proposed to describe cables in model of cable-driven parallel robot, cables can be described as catenaries, or as elastic rods, or as stiff rods, all this methods have advantages as well as disadvantages, see [15]. The most complete descriptions of cable-driven parallel robots are given in [16], [17]. The typical ways to improve accuracy of cable-driven parallel robots are given, for example, in works [18], [19]. These methods based on readings of force sensors with further processing the data with Kalman filter or with ANN and sometimes also with additional observation by cameras.

This work proposes simple geometrical approach to estimate the errors of large-sized cable-driven parallel robot with sufficient accuracy via readings of force sensors only of lower cables for specific configuration of cable system.

III. DESIGN AND MODELING

It should be understood that in a real cable-driven robot the dynamics of real cable structures will differ from oscillations of rod systems with unilateral constraints which is supposed in the most of models. To provide an acceptable complexity

Fig. 1. Model of the building complex of the University of Innopolis. of the mathematical model and the feasibility of the problem, we ought to abandon a more adequate model of the Irvin’s cables in favor of the rods. It is assumed that the rod model with unilateral constraints matches the main properties of high-loaded cable.

A. Cable System

Strictly speaking cables have properties of structural and geometrical nonlinearity, but some of them in special cases may be supposed negligible. It is assumed that cables are highly stressed and not sagging, so cables are represented as elastic rods. With this assumption geometrical nonlinearity is cancelled out. Thus we only have the problem of structural nonlinearity, which is discussed in context of dynamics. Therefore, the basics of kinematics of cable-driven parallel robot may be described in terms of linear algebra with conventional methods. We are interested in lengths of cables which are: li = ai − Rbi − r (1) where r is radius vector connecting origin of world frame with origin of tool frame, ai is vector connecting origin of world frame with i-th proximal anchor point, bi is vector connecting origin of tool frame with i-th distal anchor point, and R is transformation matrix.

Also we will use transposed Jacobian matrix, which is: l1

∥l1∥2 ... l

∥l8∥2

JT =

(2) b1 × l

∥l1∥2 ... b8 × l

∥l8∥2

As we said earlier, cables have properties of structural nonlinearity and may resist only to stretching but not to pressing. This property is included in mathematical model via activation function which argument is deformation of ith cable: f = f ·

1 + ea−b∆l (3) where f is force of tension in i-th cable, ∆l is deformation of i-th cable, a and b some coefficients.

Deformations of cables are defined according to Hook law. Each i-th cable is considered as viscoelastic body according to Voigt model:

∆l˙ l0

∆l l0 f = ES

+ ηS

(4) where E is Young modulus, η is dynamic viscosity of material of cable, S is cross-section of cable, and l0 is length of unloaded cable.

Therefore, dynamics of cable-driven parallel robot can be described in terms of damping oscillations, where damping factors are viscosities of material of cables and media:

Mq¨ + D˙q + gc = −wp + JTf (5) where M is mass matrix, D is damping matrix, gc is factor of centripetal force and angular moments, wp is outer wrench, JT is transposed Jacobian, f is vector of forces in cables, and q is vector of generalized coordinates.

Finally, substitute (1) - (4) into (5):

Mq¨ + D˙q + gc = −wp + JTf ◦

1 + ea−b∆l (6) For solving (6) most of methods of numerical integration work well and ode45 is supposed to be the conventional way.

B. Towers as Bernoulli Beams

Appropriate models of towers can be given with finite elements, but these methods have very high computational cost. We may give rough approximation of towers as Bernoulli beams, more exactly, vertical uniform cantilever beams. We do not know coordinates of the top of deformed tower, but we may assume that the direction of vector of force which is applied to the tower at proximal anchor point does not change significantly after deformation of the tower. Then we suppose vector of force coinciding with given direction of cable and find horizontal projection of the force, and obtain the deflection of the free end of the beam:

L3 3EIA

F (7)

∆x = where L is the length of a beam; E is Young modulus; IA is the moment of area which depends on the shape of cross-sectional area of a beam; F is the force which is applied perpendicular to a beam [20].

We also may assume that impact of deformation of each tower on the system can be represented via elongation of the corresponding cable and this elongation is equal to obtained ∆x. These assumptions are included in the numerical model of the robot and used in simulation.

C. Estimation the Errors

The idea is based on supposing the errors in positions of lower proximal anchor points negligibly small. Considering the tower has properties of vertical cantilever beam we suppose that deformations in the lower part of the beam are significantly fewer than ones in the upper half, especially at the top. The condition of deformations of towers is included in the model but for real structures it is hard to obtain precise position of upper proximal anchor points. Then the methods of linear algebra which are conventional in design and modeling of cable-driven parallel robots become unusable. To avoid the uncertainty we may exclude upper cables from calculations and use only lower cables. The necessary condition is such that all Tait-Bryan angles for given orientation of mobile platform must be equal to zero.

Let us consider a horizontal plane and four lower cables are lying in this plane when mobile platform meets given position. If cables deform under the payload then plane transforms to truncated rectangular right pyramid, Fig. 2.

The height of the third trapezoid is the estimated position error in vertical coordinate. Strictly speaking this is not a frustum and not trapezoids. But comparing with the lengths of segments of cables the differences are small and we can suppose the assumption is correct. In general case for n lower cables we also suppose a frustum with n trapezoidal side faces but some additional calculations are required.

Such way we can calculate only the absolute value of estimated error and we do not know signs of segments of the curve. How can we know if the center of mass of the mobile platform upper or lower relatively to given position? Of course, if only the gravity force acts on the mobile platform then the center of mass can be only lower. But in the case of overshooting of automatic control system it can be upper too. The ends of cables which are connected to distal anchor points have to be equipped with electronic levels. This way we know the direction of each cable relatively to their proximal anchor points: upward or downward. The algorithm which is proposed below allows to define the signs of segments of the curve via positive or negative angles of rising cables in vertical plane:

Fig. 2. Geometry of lower cables. α = n αi (11) i=1 f(α) = sign(α) (12) where αi is the angle of rising of i-th cable.

To smooth function of signum out we approximate it with sigmoid step function. It has a form:

Now we can find the heights of any two trapezoids which are opposite faces of obtained truncated rectangular pyramid: h1 = l∗2 4 − (d − a)2 + l∗2 4 − l∗2

2(d − a)

(8) h2 = l∗2

(d − a)2 + l∗2

3 − l∗2

(9)

3 −

2(d − a) where l1∗,l2∗,l3∗,l4∗ are lengths of segments of deformed cables; a is the distance between two neighbour distal anchor points; d is the distance between two neighbour proximal anchor points.

The length of each segment ln∗ is obtained as sum of the given length of the segment with elongation of the cable which is calculated through Hook law.

Then we can find the height of the third trapezoid having two edges the heights of previous two trapezoids:

(c − b)2 + h22 − h21 2(c − b)

(10) h = h22 − where b is the distance between two neighbour distal anchor points; c is the distance between two neighbour proximal anchor points.

1 + e−k(α−c) − 1 (13) where k,c are some constants. σ(α) =

Multiplying the functions we obtain estimated error for vertical coordinate of center of mass of the mobile platform: h = f(l1∗,l2∗,l3∗,l4∗) (14)

∆h = h · σ(α) (15) the result is shown in Fig. 3

Errors in heights of distal anchor points relatively to given positions in tool frame are defined via application of rotation matrix to given vectors of distal anchor points:

 

  = R

 

  (16) x∗b yb∗ zb∗ xb yb zb

∆zb = zb∗ − zb (17) where xb,yb,zb are coordinates of i-th distal anchor point in tool frame; R is rotation matrix.

So, if distal anchor points meet their given vertical coordinates then pitch and roll angles also meet given ones.

0.2

0.1

0 50 100 150 200 250 300 350 400 450 500

0.05

-0.05

0 50 100 150 200 250 300 350 400 450 500

0.05

-0.05

0 50 100 150 200 250 300 350 400 450 500

Fig. 3. Estimation of position error in z-axis.

0.05

-0.05

0 50 100 150 200 250 300 350 400 450 500

0.05

-0.05

0 50 100 150 200 250 300 350 400 450 500

Fig. 5. Orientation errors.

D. Error Compensation

The idea of error compensation is based on the next assumptions:

- • lower proximal anchor points meet their given positions;

- • configuration of cable system meets the configuration

described above;

- • given orientation angles are equal to zero.

Then two processes have to be executed simultaneously, the first one is compensation of error in vertical coordinate of center of mass of the mobile platform and the second one is compensation of errors in pitch and roll angles. Examples of position and orientation errors for motion of mobile platform without and with error compensations are given in Fig. 4, 5.

0.05

-0.05

-0.1

0 50 100 150 200 250 300 350 400 450 500

0.05

-0.05

-0.1

0 50 100 150 200 250 300 350 400 450 500

Fig. 4. Position errors.

The mobile platform have to be equipped with gyroscope. The first process is executed via synchronized lifting of all upper cables. It is run with PID regulation. The second process is executed via separated lifting of each upper cable to minimize the error in height of each distal anchor point. It is also run with PID regulation. So, the method is suitable without any additions if there are no external disturbances such as wind pulsations and so on. In other cases additional filtering of signals of the errors is required.

E. Wind Pulsations We have a model of cable-driven parallel robot with elastic cables and deformable towers, and now is the time to add a factor of some external disturbance in the model, say, wind pulsations. In this model wind pulsations are supposed having properties of white noise. Therefore, signals of the errors become noisy and control system works unstable. It has been carried out that sufficient configuration of the filter for the given model includes two channels with transfer functions as low-pass filters. In such a way output signals have some weights and output signal of the filtering block is the sum of these weighted signals. This configuration is used as for regulation the error in vertical coordinate as for compensation of errors in pitch and roll angles. The coefficients and weights for these two different types of regulators obviously should be different. The numerical experiment has been carried out. The configuration has been tested with moving the mobile platform in different areas of workspace of the robot and the results are shown in Fig. 6, 7. Position errors with errors in pitch and roll angles could be compensated satisfactory but almost uncontrollable rotation around vertical axis provided torsional vibrations and these vibrations impact on all dynamic system. To get rid of the oscillations in position errors the torsional vibrations have to be reduced. Possible way to reduce these torsional oscillations is adding dynamic damper to the mobile platform [21].

F. Dynamic Damper

The idea of dynamic damping is to absorb the vibration energy bypassing the primary system. Dynamic dampers re-

0.05

-0.05

-0.1

0 50 100 150 200 250 300 350 400 450 500

0.05

-0.05

-0.1

0 50 100 150 200 250 300 350 400 450 500

Fig. 6. Position errors with wind pulsations.

0.1

-0.1

0 50 100 150 200 250 300 350 400 450 500

0.1

-0.1

0 50 100 150 200 250 300 350 400 450 500

Fig. 7. Orientation errors with wind pulsations. duce vibration in the specific frequency domain of oscillating object. The system of differential equations describes dynamic damping for torsional oscillations:

Jϕ¨ + bd(ϕ˙ − ϕ˙d) + cϕ + cd(ϕ − ϕd) = M0eiωt Jdϕ¨d + bd(ϕ˙d − ϕ˙) + cd(ϕd − ϕ) = 0

(18) where Jd is moment of inertia of the damper; bd and cd are viscoelastic properties of the damper; ϕd is angle of rotation of the damper; the same letters without indexes mark the values for mobile platform of the robot; the right part of the first equation is some external periodic torque.

Therefore, parameters bd and cd have to be given, moment of inertia Jd of the damper is also given, variables ϕ˙ and ϕ are inputs, so, solving the second differential equation we can find ϕ˙d and ϕd.

There is used a passive dynamic damper with given constants as viscoelastic properties. The object of damping and the dynamic damper are assumed as co-axed cylinders. Graphs for errors with attached dynamic damper are given in Fig. 8. Graphs for moments and angles of rotation around vertical axis are given in Fig. 9. Because of noisy moment of the mobile platform M there is also shown Mf which is filtered M, and Md is moment of the damper.

0.05

-0.05

-0.1

0 50 100 150 200 250 300 350 400 450 500

0.1

-0.1

0 50 100 150 200 250 300 350 400 450 500

Fig. 8. Position and orientation errors with damping.

0.2

-0.2

0 50 100 150 200 250 300 350 400 450 500

-1

-2

0 50 100 150 200 250 300 350 400 450 500

Fig. 9. Angles of rotation and moments for damper and platform.

IV. SIMULATION

The simulation has been run with the given properties of cable-driven parallel robot which are listed below:

- • H is height of towers,

H = 15 m;

- • c,d are distances between two neighbour towers,

c = 20 m,d = 20 m;

- • m is mass of mobile platform,

m = 350 kg;

- • md is mass of the dynamic damper,

md = 50 kg;

- • J is moment of inertia of mobile platform,

J = 28 kg · m2;

- • Jd is moment of inertia of the dynamic damper,

J = 4 kg · m2;

- • ES is Young modulus for material of towers, steel,

ES = 200 GPa;

- • ED is Young modulus for material of cables, Dayneema,

ED = 130 GPa;

- • cd is torsion spring constant of the dynamic damper,

cd = 3.0728 N · m · rad−1;

- • bd is angular damping constant of the dynamic damper,

bd = 0.6171 Joule · s · rad−1;

The platform is moving on planar curvilinear trajectory at height 4 m and upper limit for smoothly changing speed of motion is 0.15 m · s−1.

The results of simulation are shown in Fig. 10, 11.

0.05

-0.05

-0.1

0 1000 2000 3000 4000 5000 6000

0.1

-0.1

0 1000 2000 3000 4000 5000 6000

Fig. 10. Position and orientation errors.

5000

4000

3000

2000

1000

0 1000 2000 3000 4000 5000 6000

0.04

0.02

0 1000 2000 3000 4000 5000 6000

Fig. 11. Tensions in cables and deflections of towers.

V. SUMMARY

The main obtained result is significant reducing of position and orientation errors of mobile platform in model of the robot. It has been shown that impact of deformable structures of the robot and some external disturbances can be substantially reduced with controlling the cable system and attachment passive dynamic damper to the mobile platform.

The next stage is to design robust control for the robot because stable work is obligatory condition for industrial applications in robotics.

REFERENCES

[1] I. Samset, “The History of Rope Transportation”, Springer Netherlands, 1985.

[2] I. McNeil, “An Encyclopaedia of the history of technology”, Routledge, 1996.

[3] P.W. Kim, “Scientific Disciplines of Geojunggi (the Traditional Crane) in Korean Science, Technology and History Class”, EURASIA Journal of Mathematics Science and Technology Education, 13(9), pp. 6147– 6163, 2017.

[4] S.E. Landsberger, “Design and construction of a cable-controlled, parallel link manipulator”, Massachusetts Institute of Technology, 1984.

[5] J.S. Albus, “Cable arrangement and lifting platform for stabilized load lifting”, US Patent No. 4 883 184, Nov. 28, 1989.

[6] S. Kawamura, W. Choe, S. Tanaka, and S.R. Pandian, “Development of an ultrahigh speed robot FALCON using wire drive system”, Proceedings of 1995 IEEE International Conference on Robotics and Automation, volume 1, pp. 215–220, 1995.

[7] K. Maeda, S. Tadokoro, T. Takamori, M. Hiller, and R. Verhoeven, “On design of a redundant wire-driven parallel robot WARP manipulator”, Proceedings 1999 IEEE International Conference on Robotics and Automation, volume 1, pp. 895–900, 1999.

[8] T. Bruckmann, A. Pott, and M. Hiller, “Calculating force distributions for redundantly actuated tendon-based Stewart platforms”, Advances in Robot Kinematics, pp. 403–412, 2006.

[9] A. Pott, H. M¨utherich, W. Kraus, V. Schmidt, P. Miermeister, and A. Verl, “IPAnema: A family of Cable-Driven Parallel Robots for Industrial Applications”, Cable-Driven Parallel Robots. Mechanisms and Machine Science, volume 12, pp. 19–34, 2012.

[10] M. Rodriguez, “Parallel Cable Robotics for Improving Maintenance and Logistics of Large-Scale Products,” Tecnalia, 2013.

[11] P. Tempel, P. Herve, O. Tempier, M. Gouttefarde, and A. Pott, “Estimating inertial parameters of suspended cable-driven parallel robots — Use case on CoGiRo”, 2017 IEEE International Conference on Robotics and Automation (ICRA), pp. 6093–6098, 2017.

[12] E. Marchuk, Ya. Kalinin, and A. Maloletov, “Mathematical Modeling of Eight-Cable-Driven Parallel Robot”, 2021 International Conference ”Nonlinearity, Information and Robotics” (NIR), pp. 1–5, 2021.

[13] A. Akhmetzyanov, M. Rassabin, A. Maloletov, M. Fadeev, A. Klimchik, “Deep learning with transfer learning method for error compensation of cable-driven robot,” ICINCO 2020 - Proceedings of the 17th International Conference on Informatics in Control, Automation and Robotics, pp. 553-564, 2020.

[14] M. Irvine, “Cable Structures”, Dover Publications, 1992.

[15] Ya.V. Kalinin, E.A. Marchuk, “Specifity of Including of Structural Non-linearity in Model of Dynamics of Cable-Driven Robot”, Mekhatronika, Avtomatizatsiya, Upravlenie, volume 22, 10, pp. 547–552, 2021.

[16] A. Pott, “Cable-Driven Parallel Robots: Theory and Application,” Springer International Publishing, 2018.

[17] B. Zi, S. Qian, “Design, Analysis and Control of Cable-Suspended Parallel Robots and Its Applications”, Springer Singapore, 2017.

[18] J. Piao, E.-S. Kim,H. Choi, Ch.-B. Moon,E. Choi, J.-O. Park, and Ch.-S. Kim, “Indirect Force Control of a Cable-Driven Parallel Robot: Tension Estimation using Artificial Neural Network trained by Force Sensor Measurements,” Sensors, 19(11), p. 2520, 2019.

[19] M.H. Haghighipanah, “Estimation of Position and External Force of Cable Driven Surgical Robots”, University of Washington, 2017.

[20] R.S. Esfandiary, B. Lu, “Modeling and Analysis of Dynamic Systems”, CRC Press, 2018.

[21] L. Meirovitch, “Fundamentals of Vibrations”, McGraw-Hill, 2001.

# Citations

1. [Read the article [NIR_2022_parallel-robot]](https://innopolis.university/filespublic/NIR_2022_parallel-robot.pdf), file 0d7f4eeba4fb
