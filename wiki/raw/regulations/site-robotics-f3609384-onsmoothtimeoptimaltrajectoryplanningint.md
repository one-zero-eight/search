---
type: regulation
title: "On-smooth-time-optimal-trajectory-planning-in-twisted-string-actuators"
resource: "https://robotics.innopolis.university/wp-content/uploads/2021/05/On-smooth-time-optimal-trajectory-planning-in-twisted-string-actuators.pdf"
source_kind: official-document
language: ru
section: "site/robotics"
sources:
  - resource: "https://robotics.innopolis.university/wp-content/uploads/2021/05/On-smooth-time-optimal-trajectory-planning-in-twisted-string-actuators.pdf"
    id: "425f1b1d4f30"
    title: "On-smooth-time-optimal-trajectory-planning-in-twisted-string-actuators"
    last_modified: "2026-10-31T09:36:32+00:00"
generated:
  by: "catix-wiki/0.1 regulations"
  at: "2026-10-31T09:36:32+00:00"
extraction: "text layer (opendataloader)"
status: draft
---

# On-smooth-time-optimal-trajectory-planning-in-twisted-string-actuators

On Smooth Time-Optimal Trajectory Planning in Twisted String Actuators

Simeon Nedelchev1, Student Member, IEEE, Daniil Kirsanov1, Igor Gaponov1, Senior Member, IEEE, Hyeonseok Seong2, Student Member, IEEE, and Jee-Hwan Ryu2 Senior Member, IEEE

Abstract—Twisted string actuators (TSA) are efficient, compliant cable actuators with high power density that have found their way into many engineering and robotics applications in recent years. They are generally used in the scenarios involving comparatively slow positioning, since quick motions in TSAs often result in large overshoot values, undesired oscillations and loss of cable tension. This work discusses time optimal trajectory generation for point-to-point transitions in TSA. We propose a method to generate smooth trajectories by directly solving an optimal control problem while respecting constraints on motor torque and speed and preventing tension loss on cables. We have conducted an experimental evaluation demonstrating that, in comparison to classical, constrained ‘bang-bang’ transitions, the proposed trajectories result in much faster settling time, nearly-zero overshoot and require almost 60% less motor power for tracking. The proposed method can help TSAs find their way into highly-dynamical applications that have been previously deemed to be too demanding, which include parallel manipulators and antagonistically-controlled systems.

I. INTRODUCTION

Twisted string actuator (TSA) is a unidirectional tendon-driven actuator in which a string (cable) is attached coaxially to a motor shaft. Motor twisting causes the string to contract and pull the payload attached to its other end towards the motor, which makes the string act as a rotary-to-linear transmission mechanism. In the past two decades, TSAs found their way into various research and engineering areas, including compliant exoskeletons and wearable robots [1], [2], active joints and motion generation mechanisms [3], [4], [5], robotic muscles [6], [7], robotic hands [8], haptic interfaces [9] and many others.

The majority of the above mentioned applications employ TSAs in comparatively slow positioning scenarios. If one, however, desires to use these actuators in dynamical applications (for instance, jumping and legged robots, fast robotic joints, manipulators and hands) they will inevitably face various issues, some of which are inherent to cable-driven systems while others are TSA-specific. The main hurdle among these is the uni-directional nature of twisted string actuator: like other cable-driven actuators, it can only pull

This work was supported by RFBR and National Research Foundation of Korea according to the research project No. 19-58-51014 (2019K2A9A1A06100174).

The authors are with the Institute of Robotics and Computer Vision, Innopolis University, Innopolis, Russia. {s.nedelchev, d.kirsanov}@innopolis.university, i.gaponov@innopolis.ru.

2Department of Civil and Environmental Engineering, KAIST, Daejeon, South Korea. hysk.seong@kaist.ac.kr, jhryu@kaist.ac.kr and therefore there is always a risk of losing tension during the reciprocal (pushing) motion phase at high speeds. The resulting slack in the string leads to the loss of control and severe deterioration of cable’s lifetime. At the same time, the TSA-specific problems include non-negligible compliance of the strings and the ‘jamming’ nature of the twisting process, which makes the string resist twisting at the increased rate after a certain state is reached, while not assisting the motor during untwisting [10]. The above mentioned issues must be taken into account when planning fast TSA trajectories in a given dynamical motion.

Optimal trajectory planning, whose main goal is finding the fastest possible dynamical transition while accounting for actuator constraints and limitations, is an important subject in robotics field. One solution to such optimal control problem (OCP), for instance, can be found in the form of a so-called ‘bang-bang’ trajectory that yields the shortest possible transition time as the result of maximum admissible control efforts [11]. Despite having obvious advantages in terms of transition speed, jerky changes in controller activity required by the bang-bang algorithm are undesirable in practice and might often be unattainable in physical systems due to hardware limitations. In addition, using this direct approach in underactuated systems with variable and poorly-modeled stiffness (such as TSAs) can result in undesirable oscillations of the payload and the loss of tension on cables. Thus, one must consider other trajectory planning techniques which take into account additional physical constraints of the system, including its unidirectional nature.

This paper describes the framework of a time-optimal trajectory generation method for TSAs that directly solves an optimal control problem while accounting for the system’s dynamics and physical constraints (tension, unidirectional action, motor capabilities). The method generates optimal, slack-free trajectories whose tracking is always achievable without constraint violation, which is extremely important for dynamical and precise tracking systems.

The work also presents a comparative study and experimental evaluation of two trajectory planning methods (constrained bang-bang and the proposed algorithm with smoothing) for twisted string actuators in point-to-point motion scenarios. Experimental results highlight that tracking bang-bang trajectories yields undesirable oscillations, high overshoot values and violates physical constraints imposed on the system due to the unbounded jerks. All of these negative effects lead to increased control effort and settling time values. In contrast, tracking smoothed trajectories generated with the proposed framework results in more than two-fold decrease of settling time and minimal overshoot while preventing slack on strings and requiring less than half the actuator power.

To the authors’ best knowledge, this is the first dedicated work on TSA trajectory planning, with the majority of previous studies focusing primarily on modeling and control.

II. CONVENTIONAL TIME OPTIMAL TRANSITIONS

In this paper, we will be looking for trajectory (defined by the state vector x(t) = [q(t),q˙(t)] and control input u(t)) that supports transition from a given initial point qi, q˙i = 0 to the target point qf, q˙f = 0 within the minimal terminal time tf, provided that the states and control input remain in some admissible set x ∈ X, u ∈ U. We assume that the admissible sets X,U are not empty and can be defined by the constraints of the form g(q,q,˙ q¨). Thus, we can find the minimal time trajectory as the solution of the following optimal control problem (OCP): tf minimize: tf(q,q,˙ q¨) = dt

subject to: g(q,q,˙ q¨) ≤ 0 q(0) = qi, q(tf) = qf q˙(0) = q˙(tf) = 0,

(1)

One can note that the problem above is formulated as a classical variational problem. There are several methods that support solving problems of the form (1), with the majority of them exploiting the inner structure of the problem and applying the Pontryagin’s maximum principle or Bellman dynamic programming.

However, it is worth noting that in the definition (1) above, the boundaries (e.g. upper integration limit tf) might not be fixed, which makes the solution of these problems rather challenging. Therefore, it is always desirable to find some parameterization that re-formulates our problem into the one with fixed boundaries while producing the identical optimal solution. One of the most common methods to achieve this in a class of point-to-point trajectories is the so-called time scaling.

A time scaling function is a smooth, monotonically increasing C2-function s(t) with s(0) = 0,s(tf) = 1, such that the target trajectory can be written as q(s), subject to the boundary constraints q(0) = qi,q(1) = qf. Using this parameterization, one may define a point-to-point trajectory by applying the following transformation: q s(t) = q0 + s(t) qf − qi (2)

Assuming that the system remains at rest at the terminal and initial points (X˙0 = X˙f = 0), the boundary conditions on s˙ can be given as s˙(0) = s˙(tf) = 0, while differentiating the expression above yields:

∂q ∂s s˙ = qf − qi s ˙ (3) q˙ =

∂2q ∂s2

∂q ∂s s˙2 = qf − qi s ¨ (4) q¨ = s¨+

The pair {s,s˙} ∈ S in fact describes the evaluation of desired trajectory, and may itself be viewed as a dynamical system defined on the first quadrant of the phase plane S.

The main advantage of this formulation is that the cost function (terminal time tf) may now be written as a function of only the states {s,s˙}: tf

tf ds ds s˙−1ds (5) This idea was simultaneously introduced by Shin [12] and dt = dt = tf =

Bobrow [13].

Thus, we may re-formulate the minimal time problem (1) as follows:

s˙−1ds minimize:

subject t o: gs(s,s,˙ s¨) ≤ 0 s(0) = 0, s(tf) = 1 s˙(0) = s˙(tf) = 0, s˙ ≥ 0

(6)

It follows from the analysis of the OCP above that the coordinate s˙ should be maximized at all times.

Let us define some admissible curves {sa,s˙a} ∈ Sa as solutions of constraints gs(sa,s˙a,s¨a) = 0 subject to the boundary conditions sa(0),sa(tf),s˙a(0),s˙a(tf). Now, the optimal trajectory {s∗,s˙∗} should lie on the boundary of the set Sa. Thus to obtain optimal solution one may numerically integrate the differential constraints and find their intersection. This procedure is widely known as time-optimal time scaling algorithm and was well studied and efficiently implemented [14], [15], [16].

The advantages of this method are its simplicity and numerical efficiency. However, this technique has its limitations, including the discontinues in jerk, dependence on the accuracy of integration routines, and applicability to only specific types of constraints. A possible way to overcome these drawbacks is by using so-called direct methods that support solving the problem (6) without additional assumptions on the type of constraints. Moreover treating OCP directly allow to smoothen the resulting trajectory by minimizing the jerk thanks to the modified cost function given by

... s2}ds (7)

{wts˙−1 + ws

Jc =

where wt,ws are the gains that tune penalization of time and smoothing terms, respectively. The similar cost was introduced before to generate human like motion profiles by minimizing derivatives of joint torques [17] as well as to minimize jerk in space manipulators [18].

The following section describes the application of the proposed time optimal transition method to twisted string actuators.

III. TIME OPTIMAL TRANSITIONS IN TWISTED STRING ACTUATORS

This section re-formulates the problem discussed above for the particular case of TSA. In this work, we will only r θr θr

L X-

L X-

L

L

L

X

Fig. 1. Schematic depiction of a section of twisted string consider point-to-point trajectories in the operational space X given by initial and terminal points {Xi,Xf} ∈ [0,0.3L]. The upper bound of this interval originates from empirical observations which suggest that the strings may have problems untwisting and are hard to model precisely when contracted by more than 30% of their initial length, and this upper bound have been customarily used in most of the TSA-related works.

A. On Constraints

While planning time optimal trajectories in twisted string actuators, one has to consider the following constraints: limited motor capabilities in terms of power P, torque τ and speed θ˙, unidirectional nature of cable-driven actuation, and nonlinear relationship between motor angle θ and string contraction X (payload’s position). The last item is TSA-specific, while the two previous constraints apply to other tendon and cable systems as well. In this subsection, we will tackle each of these issues one-by-one and provide formulation of associated constraints in terms of time scaling variables {s,s,˙ s¨}.

- 1) Kinematics and Motor Velocity: According to the

conventional representation of a section of twisted string depicted in Fig. 1, a cable of length L and radius r, twisted at an angle θ, forms a helix and contracts by X amount. For the resulting right triangle with the sides (L − X),θr, and L, one can derive the following geometric constraint: θ2r2 + (L − X)2 − L2 = 0 (8)

Differentiating the equation above with respect to time and assuming speed of variation of system parameters r˙ and L˙ to be negligible in comparison with X˙ and θ˙, one obtains the following differential constraint on velocities: θr2θ˙ + (X − L)X˙ = 0 (9)

Expressing the linear velocity X˙ from (9) yields the following relationship between input and output velocities: θr2 L − X θ˙ = J θ˙ (10)

X˙ = with the term J hereinafter referred to as the Jacobian of twisted string. It should be noted that, for the transmission system that is TSA, the Jacobian is equivalent to the inverse of transmission (gear) ratio and may be written both in terms of θ or X using the constraint (8) as

√2LX − X2 L − X θr2 L − X θr2 √L2 − θ2r2

(11)

J =

= r

=

In practice, the maximum value of motor speed θ˙ is bounded by its nominal value θ˙n, which may be written in terms of payload position X and speed X˙ using the expressions above as |J −1X˙ | ≤ θ˙n. Furthermore, applying transformations (2) one can rewrite the constraint above with respect to time scaling as follows:

|s˙| ≤ v(s) (12) where v(s) > 0 is a function that represents the maximal value of linear velocity normalized to the path given nominal motor speed, v(s) = (Xf − Xi)−1J X(s) θ ˙n. It is worth noting that in this form we do not invert the Jacobian thus avoiding singularity related problems. The above formulas enable us to handle dynamics-related phenomena in TSAs, as described below.

- 2) Dynamics, Tension and Torque: One of the most

widely used approaches for considering motor torque limitations involves introducing constraints on nominal torque values:

|τ| ≤ τn, (13)

To do so, we must establish the relationship between motor torque τ and trajectory parameters {X,X,˙ X¨}, as described by the TSA dynamics. In this work, we assume a linear TSA to be an isolated, non-conservative system, experiencing the effects of the gravitational force (acting on the payload of known mass m) and frictional forces (acting on both the motor and linear sliders): τ = Iθ¨+ bθθ˙ + (J + 21 ∂C∂θ T)T + τfr T = mX¨ + bXX˙ + mg + Ffr

(14) where I is motor inertia, the terms bθ and bX represent motor and load viscous friction coefficients, C is nonlinear compliance of strings, τfr and Ffr denote additional motor and load friction torques and forces that are not functions of speed (for instance, Coulomb dry friction). If needed, this dynamical model can be easily extended to describe a particular TSA-driven system. The proposed model has been evaluated in our previous works and demonstrated sufficient accuracy when describing dynamic TSA trajectories [10].

The compliance term C was introduced to model strings ‘jamming’ effect in the form of a nonlinear spring that counteracts string twisting, and the partial derivative of this term ∂C/∂θ may be calculated as follows:

2 2L2 − r2θ2 Kr∗

L3 K∗ r L2 − θ2r2

∂C ∂θ rθ3 +

= 2 θ

L where Kr∗/r = Kr,KL∗/L = KL denote normalized stiffness coefficients.

One can note that in (14), the torque τ is defined in terms of motor {θ,θ,˙ θ˙} and load {X,X,˙ X¨} variables. However, one can eliminate the motor-side terms using the constraint (8) and its derivatives. Thus, one may rewrite the expression for motor torque as follows: τ = D(X)X¨ + h(X,X˙ ) (15)

This makes it possible to rewrite constraints on the torque in the time scaling form:

|Ds(s)¨s + hs(s,s˙)| ≤ τn (16) where Ds(s) = (Xf − Xi)D(X(s)) and hs(s,s˙) = h X(s),X˙ (s,s˙) . Note that dynamics (14) as well as kinematic constraints (8) and their derivatives are only valid when there is no slack on strings, T > 0. If, at some point in time, the strings become loose, system dynamics will be described by dynamical equations of two decoupled subsystems (motor and payload, respectively), as it follows from the expression (14) when setting T = 0. In case of linear TSA, zero tension (slack) on the strings can occur as the result of abrupt motor stoppage when the payload is moving upward or during excessively fast untwisting of strings. To prevent the slack, one can define a constraint that will ensure maintaining some minimal value of tension Tmin as follows: mX¨ + bXX˙ + mg + Ffr ≥ Tmin (17) Lastly, applying transformation X → s yields:

Tmin − mg − Ffr m(Xf − Xi) − bX m s˙ (18) At this point, the constraints can be summarized as fols¨ ≥ lows:





Ds(s)¨s + hs(s,s˙) − τn −Ds(s)¨s + hs(s,s˙) − τn s˙ − v(s) −s˙ − v(s) g(s,s,˙ s¨) =

 

 

Tmin−Ffr−bXs˙ m − g − (Xf − Xi)¨s

Thus, one can use these constraints directly in the solution of related OCP which is described in the following subsection.

B. Trajectory Planner

There are several ways to solve the OCP described above to design a time optimal trajectory planner, with most approaches consisting of 2 phases. In the first phase, we re-formulate the variational problem over the set of continuous-time functions into an optimization problem (generally non-linear and non-convex) with a finite set of decision variables and nonlinear constraints imposed on them. The second phase is solving the resulting nonlinear optimization problem.

One of the most popular approaches to solving boundary value problems are the so-called shooting methods. With this approach, one divides the time scaling interval s into N equal sub-intervals and then applies 2N differential constraints approximated by the 4-th order Runge-Kutta method (double integrator on the time scaling acceleration s¨). Introducing additional n constraints in the form of gi(s,s,˙ s¨) ≤ 0 on each sub-interval, together with boundary and monotonic constraints yields optimization problem with the total of 3N variables {s,s,˙ s¨} and (n + 3)N + 4 constraints. In this study, we used the CasADi framework [19] that provides a convenient and easy-to-use interface to the C++ written interior point nonlinear solver (IPOPT) [20].

Fig. 2. Phase plane representation of time-optimal scaling trajectories {s, s˙}, for bang-bang and smoothed solutions

Fig. 3. Temporal plots of time scaling trajectories {s, s˙}, for bang-bang and smoothed solutions

To illustrate the performance of the trajectory planner for the TSA, we have tested our implementation on the classical ‘bang-bang’ trajectory and its smoothed counter-part. It is worth noting that smoothing should be done in the payload (task) space, and the corresponding translation can be done by applying the following normalization: ws = (Xf − Xi)2wx where wx is a certain positive gain that describes jerk penalization in the task space.

Phase plots of two sample time scaling trajectories are presented in Fig. 2 . One can see that the bang-bang trajectories occupy the whole admissible region (filled in red) bounded by constraints (dashed lines), thus providing maximal area under the phase curve and supporting minimal possible transient time t∗f. Conversely, the region of smoothed trajectories has a slightly smaller area which results in comparatively slower motion. The corresponding temporal plots of s and s˙ are presented in Fig. 3. One can note that the bang-bang algorithm requires a sharp change in s˙ at around 0.07 seconds, which implies hard discontinuity (instant change from maximum positive to maximum negative) motor action, which may cause undesired jerk, oscillations of payload and the loss of tension on strings. However, ensuring smooth transitioning between different constraint curves with the proposed method eliminates any discontinuities in motor

TABLE I IDENTIFIED SYSTEM PARAMETERS

L0 [mm] r0 [mm] m [kg] J [gcm2] τc [mNm]

**169.0** 0.78 2.05 15.68 1.97

bθ [µNms] Fc [N] bX [Ns/m] Kr∗ [kN/m] KL∗ [kN/m]

**2.31** 2.11 7.31 11.67 10.02

acceleration and helps minimize the effects of possible model uncertainties.

C. Controller

Once the optimal time scaling trajectory {s∗,s˙∗,s¨∗} has been found, one may use expressions (2), (3), (4) in order to find associated optimal load trajectory {X∗,X˙ ∗,X¨∗}. Once this step is complete, one can use (8), (9), (14) describing TSA kinematics and dynamics to find the corresponding motor-space variables {θ∗,θ˙∗,θ¨∗} as well as optimal motor torque τ∗.

Once all the variables have been found, we may define the desired state to be x∗ = [X∗,X˙ ∗,θ∗,θ˙∗]T and apply full-state feedback controller in the following form: u = K(x)x˜ + τ∗ (19) where x˜ = x∗ − x is the tracking error in both payload and motor spaces while the term K is the state-dependent matrix given by the following expression:

K(x) = J (x)PX J (x)DX Pθ Dθ T

In fact, the first two terms in the K matrix above represent task space (payload) PD regulator gains transformed to the motor space via string Jacobian, while the other two terms (Pθ,Dθ) are intended for direct control in the motor space.

This section outlines the procedures to formulate constraints, design trajectory planner and controller to ensure smooth transitions in twisted string actuators. The next section presents the experimental evaluation of the proposed approach.

IV. EXPERIMENTAL EVALUATION A. Experimental Setup

To verify the viability of the proposed technique experimentally, we have manufactured the testbed shown in Fig.

## 4. It is composed of a brushed DC motor (Maxon DCX22L

20W, 24V) equipped with a quadrature optical incremental encoder (1024 CPT), a linear encoder with the resolution of 18 µm (Avago H9740-1 360 LPI) to measure the actual string contraction and velocity (ground truth), and a digital control unit (32 bit Arm Cortex-M7 216 MHz core-based) connected to the motor driver (ESCON 70/10). We have installed a pair of 1-mm Dyneema strings in the TSA. To measure the string tension, we have used a thru hole load cell (Futek LTH300 50 lb) together with a signal amplifier (Futek IAA100). Kinematic and dynamic parameters of the testbed are summarized in Table I.

Fig. 4. Experimental setup: 1) Force sensor, 2) Linear encoder, 3) Static load, 4) A DC motor with angular incremental encoder, 5) Twisted strings

TABLE II RESULT OF TRAJECTORY TRACKING

Trajectoty Bang-Bang Smoothed

Calculated tf [s] 0.130 0.155

Actual tf [s] 0.303 0.161

Overshoot [%] 12.26 0

Tension [N] ≥0/45 4/40

Torque [mNm] -50/50 -35/35

RMS Power [W] 4.11 1.58

B. Desired Trajectory and Constraints

The goal of this experimental study is to compare the TSA behaviour when tracking point-to-point trajectories generated with constrained band-bang and proposed smoothing time optimal method. This problem may be viewed as a simplified pick-and-place task that usually needs to be performed in the time-optimal fashion.

In order to thoroughly test the performance of proposed trajectory planner in various operation conditions and contraction regions of the strings, we have designed an experiment in which the payload needs to be moved through a sequence of transitions between several points while obeying the constraints on the motor torque |τ| ≤ 35 mNm and speed |θ˙| ≤ 1000 rad/s, as well as that on string tension T ≥ 5 N.

Once we calculate both trajectories (constrained bang-bang and smoothed), we implement the control law (19) with the feedback gains of PX = 30,DX = 5,Pθ = 0.3,Dθ = 0.15 (we track string contraction in millimeters). The control values are computed on a digital control unit with the frequency of 1 kHz .

Experimental results of tracking are presented in Fig. 5- 6 while some extreme values of trajectory and transient response parameters for longest transition (from 5 mm to 30 mm) are summarized in Table II. Even though theoretically, tracking bang-bang trajectories should result in the fastest

Fig. 5. Temporal plots of tracking bang-bang and smoothed trajectories

Fig. 6. Temporal plot of tension on the string and motor torque settling time, in practice the discontinuities in acceleration (unbounded jerk) yield significant overshoot and undesirable oscillations, as can be inferred from the top plot in Fig.

## 5. Conversely, tracking the smoothed trajectory results in

much faster response with minimal oscillations. One can also notice from the bottom plot that smooth trajectories are much less demanding in terms of motor speeds, even though they result in faster settling times. For a quantitative comparison of the actual settling times we propose the following criteria: tf

(20) b κt = E tf s

Calculating the above criterion yields the value of κt = 2.14, which means that tracking smoothed trajectories in fact results in more than two-fold decrease of settling times in comparison to the bang-bang trajectories, as demonstrated by experiments on the real TSA device.

In addition, tracking bang-bang type trajectory leads to the violation of imposed constraints, namely that on tension, as it follows from the top plot in Fig. 6 slack on the string result in saturating force sensor. As a consequence, having slack on strings due to high payload accelerations requires increased control effort (directed, among others, at dampening undesired motion), which results in additional power losses on the motor and payload sides. On the other hand, one can observe from both plots in Fig. 6 that tracking smoothed trajectory never leads to violating tension constraints or excessive torques.

To compare controller activities in both cases, we calculated the ratio between mechanical power on the motor side given by following expression:

Pb2dt Ps2dt κP = τd2θ˙d2dt τs2θ˙s2dt

=

(21) where Pb,Ps represent mechanical power when tracking bang-bang and smoothed trajectories, respectively.

Calculating the value of the criteria above yields κP = 2.6, suggesting that following smoothed trajectories required, on average, approximately 60% less energy from the motor.

V. CONCLUSION AND FUTURE WORKS

This paper proposes a trajectory planning method to generate time optimal transitions in twisted string actuators. The problem in question was formulated as an optimal control problem without any additional restrictions on the type of constraints, and solved directly. The proposed technique supports generating point-to-point trajectories while respecting the constraints on motor speed and torque as well as that on string tension to prevent any possible slack.

We have also conducted an experimental study which highlighted the fact that tracking the trajectories generated by classical, constrained bang-bang method leads to undesirable oscillations of payload and to violation of imposed constraints due to discontinuities in acceleration. Conversely, smoothed trajectories help effectively eliminate these effects and provide easily trackable trajectories which support constrained motion of system, while resulting in nearly twice smaller settling times due to the absence of oscillations. Moreover, tracking smoothed trajectories was shown to be approximately 60% more efficient in terms of required motor power.

This work opens up new perspectives for the application of twisted string actuators to highly-dynamical motion control systems hitherto unavailable for TSA. For instance, as our next goal is to apply the proposed technique to plan time optimal transitions in antagonistically-driven TSA-based devices, such as parallel manipulators and human-machine interfaces. On a different note, we are also planning to improve the performance of the proposed method by treating the trajectory as a sequence of splines and thus reducing the number of optimization variables.

REFERENCES

[1] Z. Yao, C. Linnenberg, R. Weidner, and J. Wulfsberg, “Development of a soft power suit for lower back assistance,” in 2019 International Conference on Robotics and Automation (ICRA). IEEE, 2019, pp. 5103–5109.

[2] S. Zhao, Y. Yang, Y. Gao, Z. Zhang, T. Zheng, and Y. Zhu, “Development of a soft knee exosuit with twisted string actuators for stair climbing assistance,” in 2019 IEEE International Conference on Robotics and Biomimetics (ROBIO). IEEE, 2019, pp. 2541–2546.

[3] D. Lee, D. H. Kim, C. H. Che, J. B. In, and D. Shin, “Highly Durable Bidirectional Joint with Twisted String Actuators and Variable Radius Pulley,” IEEE/ASME Transactions on Mechatronics, vol. PP, no. c, p. 1, 2019.

[4] M. A. Khan, B. Suthar, I. Gaponov, and J. H. Ryu, “Single-Motor-Based Bidirectional Twisted String Actuation With Variable Radius Pulleys,” IEEE Robotics and Automation Letters, vol. 4, no. 4, pp. 3735–3741, 2019.

[5] R. Addo-Akoto and J. H. Han, “Bidirectional actuation of buckled bistable beam using twisted string actuator,” Journal of Intelligent Material Systems and Structures, vol. 30, no. 4, pp. 506–516, 2019.

[6] T. Helps, M. Taghavi, S. Wang, and J. Rossiter, “Twisted Rubber Variable-Stiffness Artificial Muscles,” Soft Robotics, vol. 00, no. 00, pp. 1–10, 2019.

[7] S. A. Souza, P. Muehlbauer, S. Janzen, J. Liu, and P. P. Pott, “Series and parallel actuation array of elastic micro-twisted string actuators,” in IKMT 2019-Innovative small Drives and Micro-Motor Systems; 12. ETG/GMM-Symposium. VDE, 2019, pp. 1–5.

[8] S. H. Jeong, K.-S. Kim, and S. Kim, “Designing Anthropomorphic Robot Hand With Active Dual-Mode Twisted String Actuation Mechanism and Tiny Tension Sensors,” IEEE Robotics and Automation Letters, vol. 2, no. 3, pp. 1571–1578, 2017.

[9] A. Pepe, M. Hosseini, U. Scarcia, G. Palli, and C. Melchiorri, “Development of an haptic interface based on twisted string actuators,” in 2017 IEEE International Conference on Advanced Intelligent Mechatronics (AIM). IEEE, 2017, pp. 28–33.

[10] S. Nedelchev, I. Gaponov, and J.-H. Ryu, “Accurate dynamic modeling of twisted string actuators accounting for string compliance and friction,” IEEE Robotics and Automation Letters, vol. 5, no. 2, pp. 3438–3443, 2020.

[11] S. M. LaValle, Planning algorithms. Cambridge university press, 2006.

[12] K. Shin and N. McKay, “Minimum-time control of robotic manipulators with geometric path constraints,” IEEE Transactions on Automatic Control, vol. 30, no. 6, pp. 531–541, 1985.

[13] J. E. Bobrow, S. Dubowsky, and J. S. Gibson, “Time-optimal control of robotic manipulators along specified paths,” The international journal of robotics research, vol. 4, no. 3, pp. 3–17, 1985.

[14] F. Debrouwere, W. Van Loock, G. Pipeleers, Q. T. Dinh, M. Diehl, J. De Schutter, and J. Swevers, “Time-optimal path following for robots with convex–concave constraints using sequential convex programming,” IEEE Transactions on Robotics, vol. 29, no. 6, pp. 1485– 1495, 2013.

[15] Q.-C. Pham, “A general, fast, and robust implementation of the time-optimal path parameterization algorithm,” IEEE Transactions on Robotics, vol. 30, no. 6, pp. 1533–1540, 2014.

[16] Q.-C. Pham and O. Stasse, “Time-optimal path parameterization for redundantly actuated robots: A numerical integration approach,” IEEE/ASME Transactions on Mechatronics, vol. 20, no. 6, pp. 3257– 3263, 2015.

[17] Y. Uno, M. Kawato, and R. Suzuki, “Formation and control of optimal trajectory in human multijoint arm movement,” Biological cybernetics, vol. 61, no. 2, pp. 89–101, 1989.

[18] P. Huang, K. Chen, J. Yuan, and Y. Xu, “Motion trajectory planning of space manipulator for joint jerk minimization,” in 2007 International Conference on Mechatronics and Automation. IEEE, 2007, pp. 3543– 3548.

[19] J. A. E. Andersson, J. Gillis, G. Horn, J. B. Rawlings, and M. Diehl, “CasADi – A software framework for nonlinear optimization and optimal control,” Mathematical Programming Computation, vol. 11, no. 1, pp. 1–36, 2019.

[20] A. W¨achter and L. T. Biegler, “On the implementation of an interior-point filter line-search algorithm for large-scale nonlinear programming,” Mathematical programming, vol. 106, no. 1, pp. 25–57, 2006.

# Citations

1. [On-smooth-time-optimal-trajectory-planning-in-twisted-string-actuators](https://robotics.innopolis.university/wp-content/uploads/2021/05/On-smooth-time-optimal-trajectory-planning-in-twisted-string-actuators.pdf), file 425f1b1d4f30
