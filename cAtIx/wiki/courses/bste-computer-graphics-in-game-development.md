---
type: course
title: "Computer Graphics in Game Development"
description: "A course on fundamental computer graphics algorithms for real-time applications, focusing on implementing CPU rasterizers, ray tracers, and GPU-accelerated renderers using DirectX12."
resource: "https://eduwiki.innopolis.university/index.php/BSTE%3A_Computer_Graphics_in_Game_Development"
tags: ["computer-graphics", "game-development", "directx12", "rasterization", "ray-tracing", "cse811"]
sources:
  - resource: "https://eduwiki.innopolis.university/index.php/BSTE%3A_Computer_Graphics_in_Game_Development"
    id: "7991"
    title: "BSTE: Computer Graphics in Game Development"
    last_modified: "2022-12-16T12:31:26Z"
generated:
  by: "catix-wiki/0.1 (local)"
  at: "2026-10-22T02:05:28+00:00"
status: draft
stale_after: "2024-12-15T12:31:26+00:00"
prerequisites: [{"as_written": "CSE101"}, {"course": "/courses/bsc-introduction-to-programming-ii.md", "as_written": "CSE102"}, {"as_written": "CSE104"}, {"course": "/courses/bsc-data-structures-algorithms.md", "as_written": "CSE117"}, {"as_written": "CSE119"}, {"as_written": "CSE202"}, {"course": "/courses/bsc-analytic-geometry-and-linear-algebra-ii.md", "as_written": "CSE204"}]
relations_by: "process:catix-wiki-graph/0.1"
---

# Computer Graphics in Game Development

## Computer Graphics in Game Development
- **Course name**: Computer Graphics in Game Development
- **Code discipline**: CSE811
- **Subject area**: Software Engineering

### Short Description
This course gives a fundamental knowledge of computer graphics algorithms with main focus on real-time applications (including games). As soon as computer graphics is being GPU-accelerated, a major row of fundamental graphics tasks and issues are hidden by GPU graphics libraries and engines. To research these tasks and issues students will implement their own renders both from scratch as using low-level graphical API.
The main goal of this course is to practice creating own renderers. Working individually with instructor guidance, students will create CPU rasterizer, ray tracer, and GPU-accelerated rasterizer based on DirectX12.

### Prerequisites

#### Prerequisite subjects
- CSE101
- CSE102
- CSE104
- CSE117
- CSE119
- CSE202
- CSE204

#### Prerequisite topics
- C++ programming
- Linear algebra: vector-matrix operations, matrix-matrix operations

### Course Topics
**Course Sections and Topics**

| Section | Topics within the section |
| --- | --- |
| Basics of rasterization | # Clearing of an image <br> # 3D model format <br> # Vertex transformation <br> # Triangle rasterization <br> # Depth buffer |
| Basics of raytracing | # Camera rays <br> # Ray intersection <br> # Lighting and shadows <br> # Acceleration structures <br> # Anti-aliasing |
| Basics of DirectX12 | # Application’s window <br> # DX12 initialization <br> # Resources in DX12 <br> # Pipeline setup in DX12 <br> # Per frame updates |
| Advanced technics and algorithms | # Resource copying <br> # Depth buffer in DX12 <br> # Textures <br> # Lighting <br> # Shadows |
### Intended Learning Outcomes (ILOs)

#### What is the main purpose of this course?
What is the main goal of this course  formulated in one sentence?
The main goal of this course is to introduce student to real-time computer graphics challenges and issue and to give them theoretical and practical knowledge about technics and algorithms that are used in solving it.

#### ILOs defined at three levels

##### Level 1: What concepts should a student know/remember/explain?
By the end of the course, the students should be able to ...
- Understand complexity of real-time computer graphics domain
- Differentiate between rasterization and ray-tracing renderers
- List technics and algorithms are used for rendering
- Understand how GPU accelerates rendering process

##### Level 2: What basic practical skills should a student be able to perform?
By the end of the course, the students should be able to ...
- create own rasterization software
- create own ray tracing software
- write shaders in HLSL format
- create own GPU-accelerated rasterization using DirectX12

##### Level 3: What complex comprehensive skills should a student be able to apply in real-life scenarios?
By the end of the course, the students should be able to ...
- implement different kinds of rendering applications
- apply a-state-of-art algorithms in rendering applications
- troubleshoot GPU-accelerated graphics applications
- fix performance issues of renderer applications 
### Grading

#### Course grading range
| Grade | Range | Description of performance |
| --- | --- | --- |
| A. Excellent | 90-100 | - |
| B. Good | 80-89 | - |
| C. Satisfactory | 70-79 | - |
| D. Fail | 0-69 | - |

#### Course activities and grading breakdown
| Activity Type | Percentage of the overall course grade |
| --- | --- |
| Assignment | 75 |
| Quizzes | 25 |

#### Recommendations for students on how to succeed in the course
Careful follow in-class guidance
Pass assignments in time
Do creative tasks

### Resources, literature and reference materials

#### Open access resources
- 1. Kanke V.A. The metascientific foundations of nuclear knowledge management // Nuclear Energy and Technology. 2016. Vol. 2. Pp. 73–81.
- 2. Frich A. The human eye and colour perception [Electronic resource]. 2015. URL:.
- 3. Anthony S. What the iPad 3’s retina display looks like under a microscope [Electronic resource]. 2012. URL: What the iPad 3’s Retina display looks like under a microscope.
- 4. McGuire M. Computer graphics archive. 2017.
- 5. Computer Graphics C.U.P. of. Cornell box data [Electronic resource]. 2005. URL:.
- 6. Turk G. The stanford bunny [Electronic resource]. 2000. URL:.
- 7. Wavefront obj file format summary // FileFormat.Info.
- 8. Alamia M. World, view and projection transformation matrices [Electronic resource]. URL:.
- 9. Serrano H. From model space to screen space- opengl space transformations [Electronic resource]. 2015. URL:.
- 10. Satran M., Jacobs M. The direct3d transformation pipeline [Electronic resource]. 2019. URL:.
- 11. Kaleniuk O. Interactive guide to homogeneous coordinates [Electronic resource]. 2020. URL:.
- 12. Jia Y.-B. Homogeneous coordinates // Handout of the Problem Solving Techniques for Applied Computer Science Lecture at Iowa State University. 2014. Vol. 58.
- 13. Sokolov D. Lesson 2: Triangle rasterization and back face culling [Electronic resource]. 2018. URL:.
- 14. Rasterization: A practical implementation [Electronic resource]. 2015. URL:.
- 15. Ray tracing: Rendering a triangle [Electronic resource]. 2014. URL:.
- 16. Phong B.T. Illumination for computer generated pictures // Commun. ACM. New York, NY, USA: Association for Computing Machinery, 1975. Vol. 18, № 6. Pp. 311–317.
- 17. The phong model, introduction to the concepts of shader, reflection models and brdf [Electronic resource]. 2015. URL:.
- 18. Satran M. Texture coordinates (direct3d 9) [Electronic resource]. 2018. URL:.
- 19. Satran M. Directly mapping texels to pixels (direct3d 9) [Electronic resource]. 2018. URL:.
- 20. Moreton H., Stam N. Turing texture space shading [Electronic resource]. 2018. URL:.
- 21. Williams L. Pyramidal parametrics // Acm siggraph computer graphics. ACM, 1983. Vol. 17. Pp. 1–11.
- 22. Golus B. Sharper mipmapping using shader based supersampling [Electronic resource]. 2019. URL:.
- 23. Rahman J. Shadow rendering techniques: Hard and soft: PhD thesis. BRAC University, 2007.
- 24. opengl-tutorial.org. Tutorial 16 : Shadow mapping [Electronic resource]. 2012. URL:.
- 25. Satran M. Cascaded shadow maps [Electronic resource]. 2018. URL:.
- 26. Shirley P. Ray tracing in one weekend. second. Amazon.com Services LLC, 2019. Vol. 1.
- 27. Lefrançois M.-K., Gautron P. DX12 raytracing tutorial - part 2 [Electronic resource]. URL:.
- 28. Galvan A. Ray tracing denoising [Electronic resource]. 2019. URL:.
- 29. Kubisch C. Life of a triangle [Electronic resource]. 2015. URL:.
- 30. Satran M. et al. Direct3D 12 programming guide [Electronic resource]. 2019. URL:.
- 31. Satran M. The component object model [Electronic resource]. 2018. URL:.
- 32. Walbourn C. ComPtr [Electronic resource]. 2019. URL:.
- 33. Fernando R. GPU gems: Programming techniques, tips and tricks for real-time graphics. Pearson Higher Education, 2004.
- 34. GPU gems 2: Programming techniques for high-performance graphics and general-purpose computation / ed. Pharr M. Addison Wesley, 2005.
- 35. Nguyen H. Gpu gems 3. First. Addison-Wesley Professional, 2007.
- 36. Fujita S. Tinyobjloader [Electronic resource]. 2020. URL:.
- 37. Satran M., Jacobs M. Get started with win32 and c++ [Electronic resource]. 2018. URL:.
- 38. Whitted T. An improved illumination model for shaded display. // Commun. ACM. 1980. Vol. 23, № 6. Pp. 343–349.
- 39. Parker S.G. et al. OptiX: A general purpose ray tracing engine // ACM siggraph 2010 papers. New York, NY, USA: Association for Computing Machinery, 2010.
- 40. Kajiya J.T. The rendering equation // SIGGRAPH Comput. Graph. New York, NY, USA: Association for Computing Machinery, 1986. Vol. 20, № 4. Pp. 143–150.
- 41. Kotel’nikov V.A. On the transmission capacity of ’ether’ and wire in electric communications // Usp. Fiz. Nauk. Uspekhi Fizichikh Nauk, 2006. Vol. 176, № 7. Pp. 762–770.
- 42. Karis B. High quality temporal anti-aliasing [Electronic resource]. 2014. URL:.
- 43. DirectXMath programming guide [Electronic resource]. 2018. URL:.
- 44. Haines E., Akenine-Moller T. Ray tracing gems: High-quality and real-time rendering with dxr and other apis. USA: Apress, 2019.
- 45. Strothotte T., Schlechtweg S. Non-photorealistic computer graphics: Modeling, rendering, and animation // Morgan Kaufmann. 2002.
- 46. Lyon R. A brief history of ’pixel // Proceedings of SPIE - The International Society for Optical Engineering. 2006. Vol. 6069.
- 47. Overvoorde A. Index buffer - vulkan tutorial [Electronic resource]. 2019. URL:.
- 48. Satran M. et al. Input-assembler stage [Electronic resource]. 2020. URL:.
- 49. Satran M., Jacobs M., Coulter D. Vertex shader stage [Electronic resource]. 2020. URL:.
- 50. Satran M. et al. Pixel shader stage [Electronic resource]. 2020. URL:.
- 51. Satran M. et al. Output-merger stage [Electronic resource]. 2021. URL:.
- 52. Pharr M., Jakob W., Humphreys G. Physically based rendering: From theory to implementation [Electronic resource]. 2021. URL:.
- 53. Halton J.H. Algorithm 247: Radical-inverse quasi-random point sequence // Commun. ACM. New York, NY, USA: Association for Computing Machinery, 1964. Vol. 7, № 12. Pp. 701–702.
- 54. NVIDIA. NVIDIA dlss [Electronic resource]. 2018. URL:.
- 55. McKesson J.L. Linearity and gamma [Electronic resource] // Learning modern 3D graphics programming. 2015. URL:.
- 56. Ray tracing gems ii / ed. Adam Marrs Peter Shirley, Wald I. Apress, 2021.

#### Closed access resources
- 1. Kanke V.A. Istoriya, filosofiya i metodologiya tehniki i informatiki. Uchebnik. Uriat, 2014.
- 2. Kanke V.A. Metascientific foundations of understanding of status of technology // Nuclear Energy and Technology. 2017. Vol. 3.

- 3. Kanke V.A. Metascientific and philosophical reasons to define the status of computer science // Automatic Documentation and Mathematical Linguistics. 2017. Vol. 51. Pp. 101–107.
- 4. Hunt R.W.G., Pointer M.R. Measuring colour. Wiley, 2011.
- 5. Marschner S., Shirley P. Fundamentals of computer graphics, fourth edition. 4th ed. Natick, MA, USA: A. K. Peters, Ltd., 2016.
- 6. Pineda J. A parallel algorithm for polygon rasterization // Proceedings of the 15th annual conference on computer graphics and interactive techniques. 1988. Pp. 17–20.
- 7. McGuire M. The graphics codex. 2.14 ed. Casual Effects, 2018.
- 8. Ericson C. Real-time collision detection. CRC Press, 2004.
- 9. Möller T., Trumbore B. Fast, minimum storage ray-triangle intersection // J. Graph. Tools. USA: A. K. Peters, Ltd., 1997. Vol. 2, № 1. Pp. 21–28.

#### Software and tools used within the course
- Provide at least 3 open/freemium access tools
- Visual Studio Community , https://visualstudio.microsoft.com/free-developer-offers/
- CLion, https://www.jetbrains.com/clion/buy/#discounts
- RenderDoc, https://renderdoc.org/ 
## Teaching Methodology: Methods, techniques, & activities

### Activities and Teaching Methods
**Teaching and Learning Methods within each section**

| Teaching Techniques | Section 1 | Section 2 | Section 3 | Section 4 |
| --- | --- | --- | --- | --- |
| Problem-based learning (students learn by solving open-ended problems without a strictly-defined solution) | 1 | 1 | 1 | 1 |
| Project-based learning (students work on a project) | 1 | 1 | 1 | 1 |
| Modular learning (facilitated self-study) | 1 | 1 | 1 | 1 |
| Contextual learning (activities and tasks are connected to the real world to make it easier for students to relate to them); | 1 | 1 | 1 | 1 |
| развивающего обучения (задания и материал "прокачивают" ещё нераскрытые возможности студентов); | 1 | 1 | 1 | 1 |
| концентрированного обучения (занятия по одной большой теме логически объединяются); | 1 | 1 | 1 | 1 |
| inquiry-based learning | 1 | 1 | 1 | 1 |
| Task-based learning | 1 | 1 | 1 | 1 |
**Activities within each section**

| Learning Activities | Section 1 | Section 2 | Section 3 | Section 4 |
| --- | --- | --- | --- | --- |
| Lectures | 1 | 1 | 1 | 1 |
| Interactive Lectures | 1 | 1 | 1 | 1 |
| Lab exercises | 1 | 1 | 1 | 1 |
| Experiments | 1 | 1 | 1 | 1 |
| Development of individual parts of software product code | 1 | 1 | 1 | 1 |
| Individual Projects | 1 | 1 | 1 | 0 |
| Discussions | 1 | 1 | 1 | 1 |
| Quizzes (written or computer based) | 0 | 0 | 0 | 1 |
### Formative Assessment and Course Activities

#### Ongoing performance assessment

##### Section 1
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Individual Assignments | In this assignment, students should implement a rasterizer from scratch. Expected that this rasterizer is able to read a 3D model file, perform vertex transformations, rasterize triangles taking into account depth, and save resulting image to a png file. To obtain a higher mark, students may implement any creative task based on the rasterizer. | 1 |
##### Section 2
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Individual Assignments | In this assignment, students should implement a raytracer from scratch. Expected that this raytracer is able to build an acceleration structure based upon 3D model file, cast camera rays, and based on ray travering generate a result image. To obtain a higher mark, students may implement a creative task | 1 |
##### Section 3
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Individual Assignment | In this assignment, students should create a GPU-accelerated rasterizer using DirectX12 API. The rasterizer should read a 3D model from a file and draw it on screen taking into account mouse movements and keystrokes. There are no creative tasks | 1 |
##### Section 4
| Activity Type | Content | Is Graded? |
| --- | --- | --- |
| Quiz | Final test | 1 |
#### Final assessment
**Section 1**
1. Can be a final exam, project defense, or some other equivalent of the final exam.
1. For the final assessment, students should pass the final test in Moodle. This test consists of 25 questions. Each question cost 1 point. There is a list of questions:
1. 1. What is a pixel?
1. 2. What is the meaning of "v" beginning lines in the OBJ file?
1. 3. What is the correct transformation order?
1. 4. What are homogeneous coordinates?
1. 5. Which stage of the graphics pipeline can transform vertices from object space to NDC?
1. 6. Which stage of the graphics pipeline assembles vertices into primitives?
1. 7. Which vectors are required to define the view matrix?
1. 8. How does the edge function look like?
1. 9. What is the sum of the barycentric coordinates inside a triangle?
1. 10. Which stage of the graphics pipeline can define a pixel color?
1. 11. What values are stored in Z-buffer?
1. 12. What is a ray?
1. 13. In which space we can trace rays?
1. 14. What information about triangle intersection does Möller-Trumbore algorithm return?
1. 15. What does it mean negative t value after ray intersection shader?
1. 16. What kind of shader do we need to use for shadow rays implementation?
1. 17. Tracing of a shadow ray returns t less than a distance to a corresponding light. What does it mean?
1. 18. Why do we need to warp an object into AABB for ray tracing?
1. 19. How many samples does make sense to use in SSAA to get the best quality of the image?
1. 20. What kind of resource heap doesn't have CPU access?
1. 21. What is the best type of resource to transfer a transform matrix?
1. 22. What function is used to compile shaders from a file?
1. 23. What kind of synchronization primitives is using for CPU-GPU synchronization?
1. 24. What resource state is required for depth buffer using?
1. 25. How to setup PSO to render a wireframe image?
**Section 2**

**Section 3**

**Section 4**


#### The retake exam
**Section 1**
1. The retake is related to the worst activity result. If a student doesn't pass the test, during the retake the student will take the final test once again. If a student doesn't finish assessments, during the retake the student will redo the assessments.
1. P7. Activities and Teaching Methods by Sections
1. Mark what techniques and methods are used in each section (1 is used, 0 is not used).
1. Table A1: Teaching and Learning Methods within each section
1. Table A2: Activities within each section
**Section 2**

**Section 3**

**Section 4**

<!-- catix:relations -->
## Relations

- Prerequisites: CSE101; [Introduction To Programming II](/courses/bsc-introduction-to-programming-ii.md) (CSE102); CSE104; [Data Structures and Algorithms](/courses/bsc-data-structures-algorithms.md) (CSE117); CSE119; CSE202; [BSc: Analytic Geometry And Linear Algebra II](/courses/bsc-analytic-geometry-and-linear-algebra-ii.md) (CSE204)
<!-- /catix:relations -->

# Citations

1. [BSTE: Computer Graphics in Game Development](https://eduwiki.innopolis.university/index.php/BSTE%3A_Computer_Graphics_in_Game_Development), revision 7991
