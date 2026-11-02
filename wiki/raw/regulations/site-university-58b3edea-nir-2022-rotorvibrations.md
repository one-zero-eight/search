---
type: regulation
title: "Read the article [NIR_2022_rotor-vibrations]"
resource: "https://innopolis.university/filespublic/NIR_2022_rotor-vibrations.pdf"
source_kind: official-document
language: ru
section: "site/university"
sources:
  - resource: "https://innopolis.university/filespublic/NIR_2022_rotor-vibrations.pdf"
    id: "8598f8e4e2e9"
    title: "Read the article [NIR_2022_rotor-vibrations]"
    last_modified: "2026-10-24T23:45:37+00:00"
generated:
  by: "catix-wiki/0.1 regulations"
  at: "2026-10-24T23:45:37+00:00"
extraction: "text layer (opendataloader)"
status: draft
---

# Read the article [NIR_2022_rotor-vibrations]

Reducing rotor vibrations in active conical fluid film bearings with controllable gap

1st Yuri Kazakov

Dept. of Mechatronics, Mechanics, and Robotics Orel State University (OSU) Orel, Russia KazakYurii@yandex.ru

4th Elena Kornaeva

Dept. of Information Systems and Digital Technologies Orel State University (OSU) Orel, Russia lenoksbox@mail.ru

2nd Alexey Kornaev

Research Center for Artificial Intelligence Innopolis University (IU) Innopolis, Russia a.kornaev@innopolis.ru

5th Leonid Savin

Dept. of Mechatronics, Mechanics, and Robotics Orel State University (OSU.) Orel, Russia savin3257@mail.ru

3rd Denis Shutin

Dept. of Mechatronics, Mechanics, and Robotics Orel State University (OSU) Orel, Russia rover.ru@gmail.com

Abstract—Despite the hydrodynamic lubrication is a self-controlled process, we designed control systems with the adaptive PI and a DQN-agent based controllers to minimize the rotor oscillations amplitude in a conical fluid film bearing. Design of the bearing allows its axial displacement and thus adjustment of its average clearance. The tests were performed using a simulation model in MATLAB software. The simulation model includes modules of a rigid shaft, a conical bearing, and a control system. The bearing module is based on numerical solution of the generalized Reynolds equation and its non-linear approximation with fully connected neural networks. The obtained results demonstrate that the both the adaptive PI controller and the DQN-based controller reduce the rotor vibrations even when imbalance in the system grows.

Index Terms—active fluid film bearing, conical bearing, simulation modeling, DQN-agent, adaptive PI controller

I. INTRODUCTION

Much of the work in the field of active bearings is associated with active magnetic bearings [1]–[5]. Control systems in fluid-film bearings can be applied to solve the following tasks: vibrations and noise minimization, friction losses reduction, increase of reliability and service life [6], [7]. Bearings with built-in (integrated) elements are widely used in practice [8]–[12]. Built-in elements to a fluid-film bearing structure allow to change the bearing geometry. Bearing models with movable pads are presented in articles [8]–[10]. Authors [13]–[15] deal with active tilting-pad bearings. Z. Cai et al. [13] and A. Wu et al. [14] manifest improving the bearings performance due to model based nonlinear controllers. It is demonstrated that the proposed nonlinear controller requires less control energy in comparison to a PID controller [14]. Article [15] presents the concept of an active bearing with the

The study was supported by the Russian Science Foundation grant No. 22-19-00789, https://rscf.ru/en/project/22-19-00789/. controlled supply pressure in radial direction by means of PD controllers.

The bearings control systems often have simple control algorithms. Despite the fairly simple structure of a controller, its tuning is a complex process. An alternative to the deterministic approach to control may be an approach based on the analysis of large experimental data [16], [17]. Deep Q network (DQN) is a modern and relatively simple discrete reinforcement learning algorithm [18]–[21]. Tarun [18] applied the DQN algorithm in control system of a manipulator to control its motions. J.B. Kim [20] developed transfer learning algorithm for DQN agent. The algorithm allows to train the agent using a simulation model instead of a real object. D. Berglund et al. [21] developed a hydraulic control system based on DQN agent. So, DQN agents are used in many applications and they also may be implemented in controllable fluid-film bearings. DQN agents require relatively small training dataset in comparison with other deep reinforcement learning agents.

This work presents a fluid film bearing control system that reducing rotor vibrations. The main control algorithms are based on the PI controller and reinforcement learning methods. The conical fluid film bearing is a bearing design with controllable gap.

II. CONTROLLED SHAFT BEARING SYSTEM CONCEPTION

The hydrodynamic lifting effect depends on many factors including fluid film thickness. The more the fluid film thickness is, the less the load-carrying capacity is. In turn, the fluid film thickness in a bearing depends on the eccentricity of the shaft and the average bearing clearance value [22]. The main idea of this research is that the average bearing clearance can be controlled in a conical fluid-film bearing due to the axial bearing displacement.

The proposed conical bearing system includes the shaft supported with the coupling at the left-side end and with the conical bearing at the right-side end (see Fig. 1). This concept is intended for conducting computational experiments and testing the ideas for the development of controllers. The bearing is lubricated with water or oil supplied with pressure p0. The supply pressure is generated with a pump and can be controlled with a servo valve. The shafts coupling is not rigid and can take the load.

In a screw-nut transmission, the nut has a conical surface. The movement of the nut allows an axial force to be applied to the face of the bearing. This action causes the bearing to move. The reactions in the damping element depends on the movement values and the speed of the bearing.

Bearing position control allows you to adjust the average gap in the bearing and, as a result, its properties, such as load capacity, friction torque, etc. The proposed shaft-bearing system also includes displacement sensors for measuring the shaft’s right end position in horizontal, vertical and axial directions, a pressure sensor for measuring the supply pressure, and a torque sensor for measuring the friction torque.

III. SIMULATION MODELING CONTROLLED SHAFT-BEARING SYSTEM

The general simulation model of a controlled shaft-bearing system was designed using the Simscape Multibody module and the Deep Learning, Reinforcement Learning, and Signal Processing toolboxes of the MATLAB software.

A. Rotor dynamics. The shaft-bearing simulation model is shown in Fig. 2. The Force ANN and Torque ANN blocks approximate the lubricating layer reaction forces and frictional torque as a function of the speed and position data of the rotor in the bearing obtained from the Bearing Joint block. The Imbalance Force block generates centrifugal force according to the given value of unbalance. The Damping element Reaction block calculates the reaction element according to Fig. 1. The End Face Force block calculates the axial force depending on the fluid supply pressure. There are stiffness and damping coefficients in the Coupling block. They were chosen in such a way that at p0 the shaft displacement was about 0. The peculiarity of this method of modeling is that the developed simulation models can be equivalent to real objects. This allows to perform a long training agents process on a simulation model without the data from a real object.

B. Hydrodynamic lubrication.

A set of simulation tests was performed to calculate the shaft trajectories for the following approximation using feed-forward neural networks [23]. The tests were performed with the following conditions. The shaft with the mass of 3 kg rotates at the constant speed of 3000 rpm. The damping element stiffness and damping coefficients are K = 40000N/m, and B = 50N · s/m, respectively. The bearing with taper angle α = 3 degrees operates with the supply pressure p0 = 1.2 · 105Pa. The range of change of the bearing displacement was from −0.5 · 10−6m to 0.7 · 10−6m.

The bearing reaction and the friction torque can be represented as functions of shaft position in a bearing, shaft speed [22], and unbalance: F⃗b = F⃗b(Xi,Vi,mud), M = M(Xi,Vi,mud) [24]. Where Xi are coordinate axes, Vi is velocity in coordinate axes, mud is unbalance. It is a known fact that artificial neural networks allow nonlinear approximation (interpolation) with high accuracy [23]. The appropriate programming tool is the Neural Net Fitting toolbox in the MATLAB [23]. The two datasets of about 384000 samples each were collected on the base of simulations to train, validate and test the networks in proportion of 0.8:0.15:0.05, respectively.

The approximation error is less than 1. Outside the training domain the error of the shaft position is 3.5, and for the friction torque - 3. However, errors increase with the increase of the shaft axial displacement.

IV. ADAPTIVE PI CONTROLLER MODEL

A. Mathematical model. The adaptive PI controller is based on a simple PI controller: uAPI = u(z) = Pe(z) + ItS e(z) 1 − z (1) where P and I are the proportional and integral coefficients, respectively, tS is the sample time, z is a complex number, u is a output controller signal, e(z) is error control. The controller has been upgraded for the use in the shaft-bearing system. The control error of the adaptive PI controller: eAPI =    |pos| − hmax0 ifX3 > X3min pos > hmax0 , 0 ifX3 > X3min p⃗os ≤ hmax0 , |X3| − X3min ifX3 < X3min, (2) where pos = X12 + X22 is eccentricity, hmax0 is desired control area in a bearing, X3min is minimal admissible position on the X3 axis.

B. Simulation model.

The simulation environment includes a Controller block, an Environment, a Button, and a Lamp. The Button is intended to turn the controller on and off. The Lamp notifies the observer about the output of the oscillations of the rotor beyond the specified limits (see Fig. 3).

The control error value is input to the controller, which is calculated by (2). The values h0 and k are used to select the trusted control area. The Cumulative sum accumulates the control signal. The control signal of the controller is the force with which the actuator acts on the bearing. The output signal of the controller is limited by the limits Lmax and Lmin.

V. DQN AGENT MODEL A. Mathematical model.

The DQN agent is a reinforcement learning algorithm. At each time step T the controller (agent) receives feedback from

Fig. 1. Schematic of a shaft-bearing system with an active conical bearing.

Fig. 2. Rotor simulation model. the system (environment) in the form of a state signal ST, then takes an action AT and a reward rT in response. It is supposed that a current state completely characterizes the state of the system.

The agent trains a critic q(S,A) to estimate the return of the future reward [25]: qt = rT + γrT+1 + γ2rT+2 + ..., (3) where γ is discount.

During the training process it is necessary to achieve the minimization of the error between the trained function q(S,A) and the optimal function q∗(S,A) that can be estimated with the Bellman equation [25]: qT∗ (ST,AT) = rT + γ max

[qT+1(ST+1,AT+1)] (4) The critic is normally an artificial neural network that

A minimizes the loss function while training: m

m

(yT − q(ST,AT|Θ(k)))2, (5)

L(Θ(k)) = i=1 where Θ(k) are the weights of the network, m is the number of training samples in the minibatch, yT = qT∗ is the estimation for the future reward.

B. Simulation model.

The control system is a DQN agent block with input parameters of observation, reward and interrupt functions, and with an output control signal (see Fig. 4) [25].

The control system generates a discrete signal in the range of pre-set values. This control system uses 5 variants of the control signal:-1, -0.5, 0.5, 1, 0 N. The control signal at each time step is added to the accumulated signal value. The frequency of the control signal is 10 Hz.

VI. RESULTS AND DISCUSSION

Malfunctions of rotary machines can lead to growing oscillations in time. Such phenomena adversely affect the system and can lead to its failure. The simulation test series were performed in order to obtain qualitative estimations of the proposed control systems. Control systems were tested on the task of minimizing the amplitudes of rotor oscillations in time.

The rotating machine simulation model has the following parameters: the shaft is 380 mm long and 40 mm in diameter, the shaft mass is 3 kg and its imbalance 0 ≤ mud ≤ 1−4 kgm. The shaft rotates at a constant speed of 3000 rpm. The conical bearing, 26 mm wide and 40 / 42.8 mm diameters, is lubricated with water under controlled supply pressure p0=0.12 MPa. The conical angle is 3 degrees and the bearing maximal axial displacement is about 1.5 mm. The stiffness and damping coefficients of the damping element are equal to K=40000 N/m and B=50 Ns/m.

A. Adaptive PI controller.

A simulation environment was created to test the controller. It was assumed that during the simulation, the amplitude of rotor oscillations would increase. The growth of the amplitude was set by the increasing imbalance. The imbalance varied from 0 to 9.3 · 10−5. The simulation time was 35 s. The adaptive PI controllers have the following settings: P= 0.0001,

Fig. 3. Adaptive PI controller.

Fig. 4. DQN controller.

I= 0.001, Lmax=0.1, Lmin=-0.1, k=0.8. The critical area of rotor operation is the radius exceeding 85 µm. At this moment, the light comes on.

It is assumed that the rotary machine is operating under fault conditions. This leads to growing amplitudes of rotor oscillations. After the rotor exits the selected critical area, a signal light is activated. The operator has the option to turn on the controller. When the controller is turned on, a control action is generated. The simulation results are shown in Fig. 5.

Fig. 5 shows the trajectories of the rotor oscillations. It can be seen that the final amplitude of rotor oscillations under control is less than if there was no control system. When the controller is turned on, at about 23 seconds, you can see how the rotor begins to move towards the geometric center of the bearing. With this movement, there is a decrease in the size of the lubricating layer and an increase in the stiffness and damping coefficients. This leads to a decrease in the amplitude of the oscillations of the rotor.

B. DQN agent.

The DQN agent training process has the following settings: the maximum number of iterations is 1000, the maximum episode duration is 5 s, the learn rate is 0.001, the experience buffer length is 100000 time steps, the discount factor is 0.85, the mini batch size is 250. The DQN agent network architecture is shown in Fig. 4. The number of neurons in hidden layers is [[14, 18, 18]]. At each time step, the DQN agent receives the reward of +1 if the oscillations is smaller than 0.9h0. Otherwise, the reward is equal to +0. A penalty of -50 is applied when the axial displacement of the shaft is more than 1.5 mm., or smaller -0.7, or the shaft touches the bearing. The DQN agent was trained at 630 iterations. The test results are presented on the figure.

The imbalance varied from 2 · 10−5 to 9.4 · 10−5. The simulation time was 5 s. The figure shows that the final trajectory of the rotor oscillations with control is smaller than without control. The resulting path lies very close to the bearing surface. This is due to the error of the model rework (see Fig. 6).

VII. CONCLUSIONS

The proposed simulation model of a rotating machine with the adjustable conical fluid film bearing allow to estimate the efficiency of control systems based on an adaptive PI controller

Fig. 5. Rotor trajectories when controlled by the Adaptive PI controller. a) with control, b) without control.

Fig. 6. Rotor trajectories when controlled by the DQN-agent. a) with control, b) without control. and a DQN-agent. The following points can be highlighted from the simulation results.

**1.** Oscillations in an adjustable conical fluid-film bearing can be decreased different control techniques. However, this is due to a change in the gap and the risk of violation of the hydrodynamic regime of friction.

**2.** Intellectual control systems, e.g. based on DQN-agent, allow to deal with operating limitations of a fluid film bearing and random changes in their operating conditions easier than by convenient controllers. Adaptive PI controllers also show good results in minimization of the friction torque. The more complex the requirements to the control system are, the more preferable it is to use intellectual control techniques.

**3.** The main advantage of a DQN-agent is its ability to adapt to complex environments and operating conditions. Its main disadvantage is connected with long training process. The disadvantage may be partially reduced by using digital twins of the machines.

**4.** When comparing the two control methods, the main points can be identified. The agent shows the best results in amplitude reduction. This is due to the easier and more flexible adjustment of the agent and its boundary conditions.

However, such systems require quite a lot of time for training. In turn, the adaptive PI controller requires setting the boundary values, which are configured by a person. The choice of the optimal values of these parameters is quite difficult because it is impossible to predict the behavior of the system in advance.

ACKNOWLEDGMENT

The study was supported by the Russian Science Foundation grant No. 22-19-00789, https://rscf.ru/en/project/22-19- 00789/.

REFERENCES

[1] A. B. Palazzolo, R. R. Lin, R. M. Alexander, A. F. Kascak, and J. Montague, “Test and theory for piezoelectric actuator-active vibration control of rotating machinery,” Journal of Vibration and Acoustics, vol. 113, pp. 167–175, 1991.

[2] Y. Aydın and F. G¨urleyen, “Adaptive and non-adaptive variable structure controls with sliding mode for active magnetic bearings (ambs) and magnetic levitation (maglev) systems: A comparative study,”IFAC-PapersOnLine, vol. 49, pp. 447–452, 2016.

[3] R. Siva Srinivas and R. Tiwari and Ch Kannababu, “Application of active magnetic bearings in flexible rotordynamic systems – A state-of-the-art review,”Mechanical Systems and Signal Processing, vol. 106, pp. 537– 572, 2018.

[4] L. Di and Z. Lin, “Control of a flexible rotor active magnetic bearing test rig: a characteristic model based all-coefficient adaptive control approach,” Control Theory and Technology 2014 12:1, vol. 12, pp. 1–12, 2014.

[5] J. Zhao, H. T. Zhang, M. C. Fan, Y. Wu, and H. Zhao, “Control of a constrained flexible rotor on active magnetic bearings,” IFAC-PapersOnLine, vol. 48, pp. 156–161, 2015.

[6] Łukasz Bre´nkacz, Łukasz Witanowski, Marta Drosi´nska-Komor and Natalia Szewczuk-Krypa, “Research and applications of active bearings: A state-of-the-art review,” Mechanical Systems and Signal Processing, vol. 151, pp. 1–39, 2021.

[7] F. Qin, Y. Li, H. Qi, and L. Ju, “Advances in compact manufacturing for shape and performance controllability of large-scale components-a review,” Chinese Journal of Mechanical Engineering, vol. 30, pp. 7–21, 2017.

[8] A. Chasalevris and F. Dohnal, “Improving stability and operation of turbine rotors using adjustable journal bearings,” Tribology International, vol. 104, pp. 369–382, 2016.

[9] A. Chasalevris and F. Dohnal, “Modal interaction and vibration suppression in industrial turbines using adjustable journal bearings,” Journal of Physics: Conference Series, vol. 744, 2016.

[10] A. Chasalevris and F. Dohnal, “Enhancing stability of industrial turbines using adjustable partial arc bearings,” Journal of Physics: Conference Series, vol. 744, 2016.

[11] R. Pai and D. W. Parkins, “Performance characteristics of an innovative journal bearing with adjustable bearing elements,” Journal of Tribology, vol. 140, 2018.

[12] J. M. Krodkiewski and G. J. Davies, “Modelling a new three-pad active bearing,” Proceedings of the ASME Turbo Expo 2004, vol. 6, pp. 799– 808, 2008.

[13] Z. Cai, M. S. D. Queiroz, and M. M. Khonsari, “Adaptive control of active tilting-pad bearings,” Proceedings of the American Control Conference, vol. 4, pp. 2907–2912, 2003.

[14] A. Wu, M. S. de Queiroz, and Z. Cai, “Model-based control of active tilting-pad bearings,” IEEE/ASME Transactions on Mechatronics, vol. 12, pp. 689–695, 2007.

[15] I. F. Santos and F. Y. Watanabe, “Compensation of cross-coupling stiffness and increase of direct damping in multirecess journal bearings using active hybrid lubrication: Part I—theory,” Journal of Tribology, vol. 126, pp. 146–155, 2004.

[16] T. P. Lillicrap, J. J. Hunt, A. Pritzel, N. Heess, T. Erez, Y. Tassa, D. Silver, and D. Wierstra, “Continuous control with deep reinforcement learning,” 4th International Conference on Learning Representations, ICLR 2016 - Conference Track Proceedings, 2016.

[17] Lucian Bu¸soniu, Tim de Bruin, Domagoj Toli´c, Jens Kober and Ivana Palunko, “Reinforcement learning for control: Performance, stability, and deep approximators,” Annual Reviews in Control, vol. 46, pp. 8–28, 2018.

[18] Tarun Bhargav Sriram, “Vision-Based Reinforcement Learning Controller Of Robotic Arm Manipulator,” Master of Science in Systems and Control, Department of Electrical Engineering, Control Systems Group, 2021.

[19] S. Yeo, Y. Naing, T. Kim, and S. Oh, “Achieving balanced load distribution with reinforcement learning-based switch migration in distributed sdn controllers,” Electronics 2021, Vol. 10, Page 162, vol. 10, p. 162, 2021.

[20] J. B. Kim, H. K. Lim, C. M. Kim, M. S. Kim, Y. G. Hong, and Y. H. Han, “Imitation reinforcement learning-based remote rotary inverted pendulum control in openflow network,” IEEE Access, vol. 7, pp. 36682– 36690, 2019.

[21] D. Berglund and Niklas Larsson, “Controlling a Hydraulic System using Reinforcement Learning,” Link¨oping University, Department of Management and Engineering, 2021.

[22] Y. Hori, “Hydrodynamic lubrication,” Hydrodynamic Lubrication, pp. 1–231, 2006.

[23] A. V. Kornaev, N. V. Kornaev, E. P. Kornaeva, and L. A. Savin, “Application of artificial neural networks to calculation of oil film reaction forces and dynamics of rotors on journal bearings,” International Journal of Rotating Machinery, vol. 2017, 2017.

[24] Y. N. Kazakov, A. V. Kornaev, D. V. Shutin, S. Li, and L. A. Savin, “Active fluid-film bearing with deep q-network agent-based control system,” Journal of Tribology, vol. 144, 8 2022.

[25] “Train DQN Agent to Swing Up and Balance Pendulum - MATLAB & Simulink,” https://www.mathworks.com/help/reinforcement-learning/ug/train-dqn-agent-to-swing-up-and-balance-pendulum.html (accessed May 14, 2022).

# Citations

1. [Read the article [NIR_2022_rotor-vibrations]](https://innopolis.university/filespublic/NIR_2022_rotor-vibrations.pdf), file 8598f8e4e2e9
