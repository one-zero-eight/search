---
type: regulation
title: "ioai26 task tour1 en"
resource: "https://lk-dovuz.innopolis.university/public/files/ioai26_task_tour1_en.pdf"
source_kind: official-document
language: ru
section: "site/dovuz"
sources:
  - resource: "https://lk-dovuz.innopolis.university/public/files/ioai26_task_tour1_en.pdf"
    id: "0f3f37b25f84"
    title: "ioai26 task tour1 en"
    last_modified: "2026-11-01T23:17:22+00:00"
generated:
  by: "catix-wiki/0.1 regulations"
  at: "2026-11-01T23:17:22+00:00"
extraction: "text layer (opendataloader)"
status: draft
---

# ioai26 task tour1 en

Task 1: Text Statistics

Before a neural network learns to write poems or answer questions, it needs to understand the basic patterns of language. Analyzing word lengths is the first step in preparing data for training language models. This task immerses you in the fundamental principles of Natural Language Processing (NLP) that underpin systems like ChatGPT.

Problem Statement

Given a text file text.txt containing arbitrary text in Russian and English. You need to:

## 1. Extract all words from the text according to the rules below.

## 2. Calculate three statistical metrics for the lengths of the extracted words:

- • Arithmetic mean (with precision of 6 decimal places)

- • Median (lower median for an even number of elements)

- • Mode (with conflict resolution in favor of the smallest value)

## 3. Save the results to two files: - words.txt — list of extracted words - result.txt —

calculated metrics

## 4. Archive both files into task1.zip.

Theoretical Background

What is a word? Word — a continuous sequence of alphabetic characters, where:

- • Alphabetic characters:

o Latin letters: a-z, A-Z o Cyrillic letters: а-я, А-Я, including ё and Ё

- • Separators: all other characters (digits, punctuation marks, spaces, special

characters).

Examples:

- • "Привет, world123! Это-тест." → Привет, world, Это, тест

- • "Hello-world" → Hello, world

- • "abc123def" → abc, def

Statistical Metrics

## 1. Arithmetic Mean

For a list of word lengths 𝐿 = [𝑙1,𝑙2,..., 𝑙𝑛]: 𝑙‾ =

𝑛 ∑𝑙𝑖 𝑛 𝑖=1 Requirement: result must be output with precision of 6 decimal places.

## 2. Median

The value in the middle of an ordered list. For even 𝑛, the lower median is taken (element with index (𝑛 − 1)//2 in the sorted list). Example: [2,3,5,8] → 𝑛 = 4, index (4 − 1)//2 = 1 → median = 3.

## 3. Mode

The most frequent length. In case of equal frequencies, the smallest value is chosen.

Example: [2,3,2,4,3,4] → frequencies: 2 → 2, 3 → 2, 4 → 2 → mode = 2.

Input Data

- • File text.txt in UTF-8 encoding with arbitrary text.

Output Data

Archive task1.zip containing two files:

1. words.txt Each line — a word from the original text in order of appearance. Example (for text "Hello, world! Это тест123."): Hello world Это тест

2. result.txt Three lines with calculated metrics:

3.833333

Grading Criteria

| № | Criterion | Points |
| --- | --- | --- |
| 1.1 | Correct word extraction (considering separators) | 25 |
| 1.2 | Correct calculation of mean and median | 35 |
| 1.3 | Correct mode selection (including handling equal frequencies) | 40 |
|  | Total | 100 |

Technical Requirements

- • Use only standard Python libraries (re, collections, etc.).

- • Arithmetic mean must have precision ±1e-6.

- • Median and mode — integer values.

- • All files must be in UTF-8 encoding.

Task 2: Data Cleaner

In the real world, data is rarely perfect. Like archaeologists cleaning ancient artifacts from dust, data scientists spend most of their time cleaning “dirty” data. Missing values, sensor errors, garbage characters — all of this hinders analysis. Today you will learn to transform chaotic data into clean, workable numbers. Without this, no artificial intelligence model can provide accurate results!

Problem Statement

Given a ZIP archive data.zip containing files of various formats. You need to:

## 1. Find all CSV files in the archive (extension case does not matter: .csv, .CSV, etc.).

## 2. Extract correct data from each line of CSV files according to the rules below.

## 3. Save all correct lines to file valid_lines.txt.

## 4. Calculate the arithmetic mean for each of the three columns across all correct lines

and write the results to file result.txt with precision of 6 decimal places.

## 5. Archive both files into task2.zip.

Theoretical Background

What is CSV?

CSV (Comma-Separated Values) — a text format for storing tabular data where values are separated by commas. For this task, strict formatting rules apply.

Rules for a correct CSV line:

- • Each line contains exactly three floating-point numbers

- • Numbers are separated by commas without spaces

- • All three values must be correct floating-point numbers in decimal format

Examples of correct lines:

1.5,2.3,4.1

-0.5,10,3.14

0.0,0.0,0.0 Examples of incorrect lines:

1.5, 2.3, 4.1 ← spaces around commas

1.5,2.3 ← fewer than three values 1e3,2.3,4.1 ← exponential notation abc,2.3,4.1 ← non-numeric value 1.5,,4.1 ← missing value What is a floating-point number in this task? Allowed formats:

- • Integer numbers: 42, -17, 0

- • Fractional numbers: 3.14, -0.5, 100.0

- • Numbers with zero fractional part: 0.0, -0.0

Prohibited:

- • Exponential notation (1e3, 2.5e-2)

- • Special symbols (inf, NaN, null)

- • Numbers with spaces or other separators

Arithmetic Mean by Column For each column 𝑗 (𝑗 = 1,2,3), the mean is calculated as:

𝑁

𝑁 𝜇𝑗 =

∑𝑥𝑖𝑗

, 𝑖=1 where 𝑁 — total number of correct lines, 𝑥𝑖𝑗 — value in the 𝑖-th line and 𝑗-th column.

Input Data

Archive data.zip in UTF-8 encoding containing: - Files with .csv extension (case does not matter) in the root of the archive - Other files (.txt, .json, without extension) and files in nested folders are ignored

Example archive structure: data.zip

├── file1.csv ← process

├── file2.txt ← ignore ├── data.CSV ← process (case does not matter) └── subfolder/

└── more.csv ← ignore (nested folders are not processed)

Output Data

Archive task2.zip containing two files:

3. valid_lines.txt

- – Each line: three correct numbers in format {number1},{number2},{number3}

- – Line order: preserves the order of file processing and lines within them

- – UTF-8 encoding

4. result.txt

- – One line with three numbers separated by spaces: {mean_col1} {mean_col2}

{mean_col3}

- – Precision: exactly 6 decimal places

- – Example: -3.000000 1.000000 34.380000

Grading Criteria

| № | Criterion | Points |
| --- | --- | --- |
| 2.1 | Correct CSV file filtering and rejection of incorrect lines (file format, column count, data type) | 50 |
| 2.2 | Correct calculation of column means with required precision | 50 |
| Total |  | 100 |

Technical Requirements

- • Use only standard Python libraries (zipfile, csv, re, etc.)

- • Numeric tolerance for means: ±10−6

- • File processing order may be arbitrary

- • All files must be in UTF-8 encoding

- • When processing files, consider only files in the root directory of the archive

Task 3: Anomaly Detector in Time Series

Every second, millions of sensors collect data on critically important systems: from patients’ heart rates to the condition of nuclear reactors. Early anomaly detection helps prevent disasters and save lives. The foundation of such systems lies in local context analysis — comparing the current value with the characteristic behavior of the system in its immediate vicinity. This task immerses you in the fundamental principles of time series and statistical quality control used in medicine, industry, and scientific research.

Problem Statement

Given a time series of measurements in the file series.txt. For each element of the series with index 𝑖 (starting from 0), it is necessary to determine whether it is an anomaly relative to its local environment.

A point 𝑥𝑖 is considered an anomaly if all of the following conditions are met simultaneously:

## 1. A complete sliding window of 11 points can be built for it (i.e., 5 ≤ 𝑖 ≤ 𝑁 − 6, where

𝑁 is the total number of points).

## 2. Its deviation from the local mean exceeds twice the standard deviation: |𝑥𝑖 − 𝜇𝑖| >

2 ⋅ 𝜎𝑖.

## 3. The standard deviation in the window is positive: 𝜎𝑖 > 0.

Requirements:

## 1. For all points in the range [5, 𝑁 − 6], calculate 𝜇𝑖 (mean) and 𝜎𝑖 (standard deviation)

for their windows.

## 2. Generate the file checks.txt with calculation results.

## 3. Generate the file result.txt with the list of indices of anomalous points.

## 4. Archive both files into task3.zip.

Theoretical Background

Time Series

A time series is a sequence of values measured at successive time moments. Examples: hourly air temperature, patient’s pulse every second, vibration sensor readings.

Sliding Window

To analyze the local context around point 𝑥𝑖, a window of 11 neighboring values is used: 5 points to the left, the point 𝑥𝑖 itself, and 5 points to the right. Window indices for point 𝑖: [𝑖 − 5, 𝑖 − 4,…,𝑖,…,𝑖 + 4,𝑖 + 5].

Important: A window can only be built for indices 𝑖 where all neighbors exist (5 ≤ 𝑖 ≤ 𝑁 −

6). Mean Value (𝜇) The arithmetic mean of values in the window: 𝑖+5

𝜇𝑖 =

∑ 𝑥𝑘 𝑘=𝑖−5

Standard Deviation (𝜎) A measure of the spread of values relative to the mean (population formula): 𝑖+5

𝜎𝑖 = √

∑ (𝑥𝑘 − 𝜇𝑖)2 𝑘=𝑖−5

2𝜎 Rule

In normally distributed data, ~95% of values lie within 𝜇 ± 2𝜎. Points outside this interval are considered statistically significant anomalies.

Input Data

- • File series.txt contains 𝑁 lines. Each line is a real number 𝑥𝑖, representing a

measurement at time moment 𝑖. File encoding: UTF-8.

Output Data

Archive task3.zip containing two files:

5. checks.txt — for each index 𝑖 from the range [5,𝑁 − 6]:

- – Line format: {i} {mu_i:.8f} {sigma_i:.8f} {is_anomaly}

- – Where is_anomaly = 1 if the point is anomalous, otherwise 0.

6. result.txt

— indices of all detected anomalies (one per line, no duplicates, in ascending order). If there are no anomalies

— the file is empty.

Example for input data of 16 points:

# checks.txt

5 10.00000000 0.00000000 0

6 10.00000000 0.00000000 0

7 13.63636364 11.49912255 0

8 13.63636364 11.49912255 0

9 13.63636364 11.49912255 1

10 13.63636364 11.49912255 0

# result.txt

Files checks.txt and result.txt must be archived into task3.zip.

Grading Criteria

| № | Criterion | Points |
| --- | --- | --- |
| 3.1 | Correct implementation of local context analysis algorithm (sliding window and statistics calculation) | 60 |
| 3.2 | Correct anomaly detection using the 2𝜎 rule and output file generation | 40 |
| Total |  | 100 |

Technical Requirements

- • Use the population formula for standard deviation.

- • Calculation error for 𝜇 and 𝜎 must not exceed 10−6.

- • Values 𝜇𝑖 and 𝜎𝑖 must be output with precision of at least 8 decimal places.

- • All files must be in UTF-8 encoding.

- • Use only standard Python libraries.

Task 4: Simple Recommendation System

Recommendation systems are the invisible assistants of modernity. They select movies, music, products, and even friends. At the heart of many of them lies a simple idea: “You will like what similar people like.” In this task, you will implement a classic collaborative filtering algorithm — the very one that started the era of personalization. Perhaps these very calculations will one day help someone find the perfect book… or even a solution to a complex problem.

Problem Statement

Given a file ratings.txt containing a user-item rating matrix. Your task:

## 1. For each user 𝑣 ≠ 0, calculate the cosine similarity with user 0 only on commonly

rated items.

## 2. Find the user 𝑣max with the maximum similarity.

## 3. Among items that user 0 has not rated (𝑟0𝑗 = 0), select the item that received the

maximum rating from 𝑣max. If there are multiple such items — select the item with the minimum index.

## 4. Output the result as an archive task4.zip containing two files: - similarities.txt -

result.txt

Theoretical Background

What is a rating matrix? A rating matrix 𝑅 ∈ ℝ𝑈×𝐼 is a two-dimensional table where:

- • 𝑈 — number of users (rows),

- • 𝐼 — number of items (columns),

- • 𝑟𝑢𝑖 — rating given by user 𝑢 to item 𝑖 (integer values from 0 to 5, where 0 means no

rating).

Example of a 4×6 matrix:

Item 0

Item 1

Item 2

Item 3

Item 4

Item 5

User 0

User 1

User 2

User 3

Cosine similarity between users

Cosine similarity is a measure of similarity between two vectors based on the angle between them. For two users 𝑢 and 𝑣, it is calculated only on commonly rated items 𝐼𝑢𝑣:

∑𝑗∈𝐼𝑢𝑣 𝑟𝑢𝑗 ⋅ 𝑟𝑣𝑗 √∑𝑗∈𝐼𝑢𝑣 𝑟𝑢𝑗2 ⋅ √∑𝑗∈𝐼𝑢𝑣 𝑟𝑣𝑗2 sim(𝑢,𝑣) = where 𝐼𝑢𝑣 = {𝑗 ∣ 𝑟𝑢𝑗 > 0 and 𝑟𝑣𝑗 > 0} — set of item indices rated by both users. Calculation example: For User 0 ([5,0,4,0,0,3]) and User 3 ([5,0,3,0,0,4]):

- • Common items: indices {0,2,5},

- • Rating vectors for common items: [5,4,3] and [5,3,4],

- • Numerator: 5 ⋅ 5 + 4 ⋅ 3 + 3 ⋅ 4 = 25 + 12 + 12 = 49,

- • Denominator: √52 + 42 + 32 ⋅ √52 + 32 + 42 = √50 ⋅ √50 = 50,

- • sim(0,3) = 49/50 = 0.98.

Input Data

File ratings.txt in UTF-8 encoding:

- • Each line corresponds to one user.

- • Numbers are separated by spaces.

- • The first line is the target user (User 0).

- • Example content:

5 0 4 0 0 3

4 0 5 0 0 4

0 3 0 2 5 0 5 0 3 0 0 4 Output Data Archive task4.zip must contain two files:

1. similarities.txt

- • For each user 𝑣 ≠ 0 who has at least one commonly rated item with User 0, a line in

the format:

- • {user_id} {similarity}

- • similarity is output with precision of 8 decimal places.

- • Line order can be arbitrary.

- • Example:

1 0.97402464 3 0.98000000

2. result.txt

- • One line containing an integer — the index of the recommended item.

- • Example:

Grading Criteria

| № | Criterion | Points |
| --- | --- | --- |
| 4.1 | Correct reading of matrix and identification of common items | 20 |
| 4.2 | Correct calculation of cosine measure for all users | 40 |
| 4.3 | Correct recommendation selection (maximum rating, tie-break by minimum ID) | 40 |
| Total |  | 100 |

Technical Requirements

- • Use only standard Python libraries (math, json, etc.).

- • Numerical tolerance for similarity: ±10−6.

- • At least one possible recommendation is guaranteed.

- • All files must be in UTF-8 encoding.

- • If multiple users have the same maximum similarity, any of them can be selected.

- • If multiple items have the same maximum rating, the item with the minimum index

is selected.

Task 5: N-gram Analysis

Neural networks don’t read words the way humans do. They analyze sequences of characters and learn based on which combinations occur most frequently. Character pairs and triples like “pr”, “st”, “ty” carry the rhythm and structure of language. N-gram analysis is one of the oldest yet most powerful methods for encoding language in machine learning. Spam filters, translators, and text analysis systems are built on this foundation. Your task is to decode the “DNA of language” by finding the most frequent character sequences.

Problem Statement

Given: Archive corpus.zip containing multiple text files with .txt extension (case-insensitive).

Required:

## 1. Process all text files in the archive in alphabetical order of filenames (case-insensitive), combining their contents in the specified order.

## 2. Clean the combined text according to preprocessing rules.

## 3. Count frequencies of unigrams (1-grams) and bigrams (2-grams) in the cleaned text.

## 4. Find top-10 most frequent unigrams and bigrams according to sorting rules.

## 5. Prepare two files: cleaned.txt (cleaned text) and result.txt (n-gram frequencies).

Result: Archive task5.zip containing files cleaned.txt and result.txt.

Theoretical Background

What is an 𝑛-gram? An 𝑛-gram is a sequence of 𝑛 consecutive characters in text. Examples:

- • Unigram (𝑛 = 1): individual characters, e.g., “H”, “e”, “l”

- • Bigram (𝑛 = 2): character pairs, e.g., “He”, “el”, “ll”

From a string of length 𝐿, you can extract:

- • 𝐿 unigrams,

- • 𝐿 − 1 bigrams.

Text Cleaning Keep only letters:

- • Latin letters: a-z, A-Z

- • Cyrillic letters: а-я, А-Я, ё, Ё

- • Remove everything else: digits, punctuation, spaces, special characters.

Cleaning example:

Original text: "Hello, world123!!! This is AI."

→ Only letters: "HelloworldThisisAI"

File Processing Order

To ensure reproducibility, files are processed in alphabetical order of filenames (case-insensitive). For example:

- • file1.txt, file2.txt, notes.TXT, README.txt

- • Processing order: file1.txt → file2.txt → notes.TXT → README.txt

Frequency Counting and Sorting

- • Frequency — number of occurrences of an 𝑛-gram in text.

- • Top-10 sorting rules:

## 1. Descending frequency order.

## 2. For equal frequencies — ascending ASCII code order.

ASCII order (important characters):

'A' < 'B' < ... < 'Z' < 'a' < 'b' < ... < 'z' < 'А' < 'Б' < ... < 'Я' < 'а' < 'б ' < ... < 'я'

Sorting example: For unigrams with frequencies: 'а': 10, 'б': 10, 'A': 10, 'в': 5, 'B': 5 Top-3 after sorting: A, а, б.

Input Data

- • Archive corpus.zip contains files with .txt extension (e.g., file1.txt, notes.TXT).

- • Only files with .txt extension participate in processing (case-insensitive).

- • File encoding: UTF-8.

- • Processing order: alphabetical order of filenames (case-insensitive).

Output Data

Archive task5.zip containing two files:

1. cleaned.txt:

- – Cleaned text without spaces.

- – Entire text written in one line.

- – Example content: HelloworldThisisAI.

2. result.txt:

- – Exactly 20 lines in format: {n_gram}<TAB>{frequency}.

- – First 10 lines: top-10 unigrams.

- – Next 10 lines: top-10 bigrams.

- – Separator: tab character (\t).

- – Example content:

e 4 l 3 o 3 ... He 1 el 1 ll 1 ...

Grading Criteria

| № | Criterion | Points |
| --- | --- | --- |
| 5.1 | Correct file reading in alphabetical order, content merging and proper text cleaning | 30 |
| 5.2 | Top-10 unigrams with correct sorting | 30 |
| 5.3 | Top-10 bigrams with correct sorting | 40 |
| Total |  | 100 |

Technical Requirements

- • Allowed libraries: os, re, collections.Counter, glob, zipfile.

- • Encoding of all files: UTF-8.

Task 6: Image Processing with Filters

Before neural networks can recognize objects in images, they need to learn how to extract useful features from them. Image filtering is one of the fundamental methods of computer vision that allows highlighting edges, suppressing noise, and enhancing important details. This task will introduce you to the basic operations of image processing that underpin modern computer vision systems.

Problem Statement

Given a file image.png containing a grayscale image. You need to sequentially apply two filters to it:

## 1. Gaussian blur with a 5×5 kernel and σ = 1.0

## 2. Sharpening filter using the “unsharp masking” method

## 3. Image inversion to obtain the final result

Save the results of all processing stages to separate files and archive them.

Implementation Requirements

Processing Stages and Output Files To verify the correctness of each stage, intermediate results must be saved:

1. kernel.txt — file with the computed Gaussian kernel 5×5

- – Format: 5 lines, each containing 5 floating-point numbers (space-separated)

- – Precision: 6 decimal places

- – Requirement: sum of all kernel elements must equal 1.0 with precision ±1e-6

2. blurred.png — image after applying Gaussian blur

- – Format: PNG, 8 bits per pixel

- – Pixel values must be rounded to integers and clamped to the range [0, 255]

3. sharpened.png — image after applying the sharpening filter (before inversion)

- – Format: PNG, 8 bits per pixel

- – Pixel values must be rounded to integers and clamped to the range [0, 255]

4. result.png — final image after applying inversion

- – Format: PNG, 8 bits per pixel

- – Inversion formula: (I_{final}(x,y) = 255 - I_{sharpened}(x,y))

All files must be archived into task6.zip.

Theoretical Background

Gaussian Blur Gaussian kernel of size (k k) is calculated using the formula: 𝑥2+𝑦2 2𝜎2

2𝜋𝜎2 𝑒−

𝐺(𝑥,𝑦) = where (x, y) — coordinates relative to the kernel center ((-2 x ), (-2 y ) for a 5×5 kernel). To apply the filter, convolution operation is performed:

𝐼𝑏𝑙𝑢𝑟𝑟𝑒𝑑(𝑥, 𝑦) = ∑ ∑ 𝐼

(𝑥 + 𝑖,𝑦 + 𝑗) ⋅ 𝐺(𝑖,𝑗) 𝑖=−2 𝑗=−2

Kernel calculation example (σ = 1.0): For center pixel (x=0, y=0):

2𝜋 ⋅ 12

𝐺(0,0) =

02+02

2𝜋 𝑒−

2⋅12 =

≈ 0.159155

Sharpening Filter (Unsharp Masking) The method is based on extracting high-frequency components of the image. Algorithm:

## 1. Original image: (I)

## 2. Blurred image: (B) (obtained from the previous step)

## 3. Detail mask: (M = I - B)

## 4. Enhanced image: (I_{sharp} = I + M)

where (= 1.5) — detail enhancement coefficient. Example: For a pixel with value 100:

- • Blurred value: 95

- • Detail mask: 100 - 95 = 5

- • Enhanced value: 100 + 1.5 × 5 = 107.5 → 108 (after rounding)

Image Inversion

Inversion transforms bright areas to dark and vice versa, which is useful for visualizing details:

𝐼𝑖𝑛𝑣𝑒𝑟𝑡𝑒𝑑(𝑥,𝑦) = 255 − 𝐼𝑠ℎ𝑎𝑟𝑝(𝑥,𝑦)

Border Handling When applying filters to pixels near image borders, use reflection strategy:

𝐼(𝑥,𝑦) =

𝐼(0,𝑦), if 𝑥 < 0 𝐼(𝑤𝑖𝑑𝑡ℎ − 1,𝑦), if 𝑥 ≥ 𝑤𝑖𝑑𝑡ℎ 𝐼(𝑥,0), if 𝑦 < 0 𝐼(𝑥,ℎ𝑒𝑖𝑔ℎ𝑡 − 1), if 𝑦 ≥ ℎ𝑒𝑖𝑔ℎ𝑡

{

Reflection example for a 3×3 image: For coordinate (-1, 1) → (0, 1) For coordinate (3, 2) → (2, 2)

Input Data

- • File image.png in PNG format with a grayscale image (8 bits per pixel, values 0-255)

- • Image size not less than 5×5 pixels

Output Data

Four files archived in task6.zip:

1. kernel.txt — Gaussian kernel matrix 5×5 (5 lines with 5 numbers each, precision 6 decimal places)

2. blurred.png — image after Gaussian blur

3. sharpened.png — image after sharpening

4. result.png — final image after inversion

Grading Criteria

| № | Criterion | Points |
| --- | --- | --- |
| 6.1 | Correct Gaussian kernel calculation (precision, normalization) | 25 |
| 6.2 | Proper convolution implementation and border handling | 35 |
| 6.3 | Correct application of sharpening filter and inversion | 40 |
|  | Total | 100 |

Technical Requirements

- • Allowed libraries: numpy, PIL (Pillow), math, zipfile

- • Calculation precision:

- – Gaussian kernel: at least 6 decimal places

- – Intermediate calculations: 32-bit floating-point numbers

- • Value constraints: all pixel values must be in the range [0, 255]

- • File formats:

- – kernel.txt — text file in UTF-8 encoding

- – All images — PNG format, 8 bits per pixel

Notes

- • Gaussian kernel must be symmetric relative to the central element

- • Sum of all Gaussian kernel elements must be strictly equal to 1.0

- • Border handling must use reflection strategy, not zero-padding

- • All intermediate results must be saved to verify the correctness of each stage

- • Final inversion is applied only to the sharpened result to create a high-contrast

representation of details

Task 7: Matrix Representation of Convolution with Different Parameters

Modern convolutional neural networks (CNNs) form the foundation of computer vision and image processing. Understanding how convolution operations can be represented as matrix transformations is crucial for optimizing computations and gaining deep insight into neural network architectures. This task immerses you in the mathematical foundations of CNNs used in systems like ResNet, VGG, and other deep learning architectures.

Problem Statement

Given an input image 𝑋 of size 8 × 8 and three convolution kernels of different sizes:

## 1. Kernel 𝐾1 of size 2 × 2 with stride = 1

## 2. Kernel 𝐾2 of size 3 × 3 with stride = 2

## 3. Kernel 𝐾3 of size 4 × 4 with stride = 2

For each kernel, construct the corresponding convolution matrix 𝐾mat(𝑖) that transforms the vectorized representation of the image vec(𝑋) into the vectorized convolution result vec(𝑌𝑖): vec(𝑌𝑖) = 𝐾mat(𝑖) ⋅ vec(𝑋), where 𝑌𝑖 is the convolution result for the 𝑖-th kernel (without padding). The dimensions of the output matrices 𝐾mat(𝑖) must be determined independently based on the kernel parameters and image size. Save the results to three files and archive them in task7.zip.

Theoretical Background

What is Convolution?

Convolution is a fundamental operation in CNNs that applies a kernel (filter) to local regions of an image to detect features. Key parameters:

- • Kernel — weight matrix determining which features will be detected

- • Stride — step size for moving the kernel across the image

- • Padding — border addition (padding = 0 in this task)

Output Image Size Formula The size of the output image for convolution without padding is determined by: input_size − kernel_size stride output_size = ⌊

⌋ + 1 where ⌊⋅⌋ denotes floor rounding. Examples:

- • For 8 × 8 image and 2 × 2 kernel with stride = 1: (8 − 2)/1 + 1 = 7

- • For 3 × 3 kernel with stride = 2: (8 − 3)/2 + 1 = 3

- • For 4 × 4 kernel with stride = 2: (8 − 4)/2 + 1 = 3

Image Vectorization Vectorization in row-major order transforms an 8 × 8 matrix into a vector of length 64: 𝑥00 𝑥01 … 𝑥07 𝑥10 𝑥11 … 𝑥17 ⋮ ⋮ ⋱ ⋮ 𝑥70 𝑥71 … 𝑥77

] vec → vec(𝑋) = [𝑥00,𝑥01, …, 𝑥07,𝑥10,…,𝑥77]⊤

𝑋 = [

Index of element 𝑋[𝑖,𝑗] in the vector: 𝑘 = 𝑖 ⋅ 8 + 𝑗.

Convolution Matrix The convolution matrix 𝐾mat has dimensions (output_size2) × 64:

- • Each row corresponds to one pixel of the output image

- • Each column corresponds to one pixel of the input image

- • Element 𝐾mat[𝑝,𝑞] contains the kernel weight applied to pixel 𝑞 when computing

pixel 𝑝

Construction rules:

## 1. Determine the output image size for each kernel

## 2. For each position in the output image:

- - Determine the corresponding window in the input image considering stride

- - Place kernel weights in the corresponding positions of the matrix row

## 3. All other matrix elements are zero

Input Data

Three files with convolution kernels:

- • kernel1.txt — 2 × 2 kernel

- • kernel2.txt — 3 × 3 kernel

- • kernel3.txt — 4 × 4 kernel

Each file contains kernel values in format: k00 k01 ... k0m k10 k11 ... k1m ... kn0 kn1 ... knm

Output Data

Archive task7.zip containing three files: - result1.txt — convolution matrix for first kernel (2 × 2, stride = 1) - result2.txt — convolution matrix for second kernel (3 × 3, stride = 2) - result3.txt — convolution matrix for third kernel (4 × 4, stride = 2) Format of each file:

{row0_col0} {row0_col1} ... {row0_col63}

{row1_col0} {row1_col1} ... {row1_col63}

... {rowM_col0} {rowM_col1} ... {rowM_col63} where 𝑀 = output_size2. Each number is output with precision of 3 decimal places.

Example for 2 × 2 Kernel with stride = 1

For kernel:

**1.0** 0.5

**0.0** 0.0 and 8 × 8 image, output size will be 7 × 7 = 49.

First two lines of result1.txt:

**1.000** 0.500 0.000 0.000 0.000 0.000 0.000 0.000 0.000 0.000 0.000 0.000 0.000 0. 000 0.000 0.000 0.000 0.000 0.000 0.000 0.000 0.000 0.000 0.000 0.000 0.000 0.00 0 0.000 0.000 0.000 0.000 0.000 0.000 0.000 0.000 0.000 0.000 0.000 0.000 0.000

**0.000** 0.000 0.000 0.000 0.000 0.000 0.000 0.000 0.000 0.000 0.000 0.000 0.000 0. 000 0.000 0.000 0.000 0.000 0.000 0.000 0.000 0.000

**0.000** 1.000 0.500 0.000 0.000 0.000 0.000 0.000 0.000 0.000 0.000 0.000 0.000 0. 000 0.000 0.000 0.000 0.000 0.000 0.000 0.000 0.000 0.000 0.000 0.000 0.000 0.00 0 0.000 0.000 0.000 0.000 0.000 0.000 0.000 0.000 0.000 0.000 0.000 0.000 0.000

**0.000** 0.000 0.000 0.000 0.000 0.000 0.000 0.000 0.000 0.000 0.000 0.000 0.000 0.

000 0.000 0.000 0.000 0.000 0.000 0.000 0.000

...

Explanation: The first row corresponds to computing the top-left pixel of the output. The 2 × 2 kernel is applied to pixels (0,0), (0,1), (1,0), (1,1) of the input image. In vectorized representation, these pixels have indices 0, 1, 8, 9. Kernel weights 1.0 and 0.5 are placed at positions 0 and 1 respectively.

Grading Criteria

| № | Criterion | Points |
| --- | --- | --- |
| 7.1 | Correct calculation of output image sizes for all kernels | 25 |
| 7.2 | Correct construction of matrix for one kernel | 25 |
| 7.3 | Construction of all three convolution matrices | 35 |
| 7.4 | Proper stride handling when building the matrix | 15 |
|  | Total | 100 |

Technical Requirements

- • Only numpy library is allowed.

- • Each number in output files must be printed with precision of 3 decimal places.

- • Vectorization order: row-major.

- • All files must be in UTF-8 encoding.

- • Numeric tolerance during validation: ±10−6.

Task 8: Optimal Policy in a Grid

Reinforcement learning forms the foundation for creating autonomous systems capable of making decisions in complex environments. From chess programs to robot control systems — they all use principles of state evaluation and optimal strategy search. The Value Iteration algorithm represents a fundamental dynamic programming method that allows an agent to pre-evaluate the value of each state in the environment. This task immerses you in the essence of planning algorithms that underpin modern artificial intelligence systems.

Problem Statement

Given a rectangular grid of size 𝐻 × 𝑊, where:

- • S — agent’s starting position (exactly 1 cell)

- • T — treasure (goal, provides reward +10)

- • X — traps (provide penalty −5)

- • . — empty cells (penalty −0.1 per step)

The agent can perform actions in 4 directions: up, down, left, right. When attempting to move outside the grid boundaries, the agent remains in the current position. Terminal states are T and X, from which no further transitions are possible.

Requirements:

## 1. Implement the Value Iteration algorithm with discount factor 𝛾 = 0.9 for 100

iterations

## 2. Calculate the value of the starting state 𝑉(𝑆) after 100 iterations

## 3. Prepare three result files: - map.txt — coordinates of key cells in format type row

col - v1.txt — value function values after 1st iteration - result.txt — value 𝑉(𝑆) after 100 iterations

## 4. Archive all files into task8.zip

Theoretical Background

Basic Concepts Environment — rectangular grid where each cell represents a state. Coordinate system: (𝑟𝑜𝑤,𝑐𝑜𝑙), where 𝑟𝑜𝑤 = 0 corresponds to the top row, 𝑐𝑜𝑙 = 0 — left column. State 𝑠 — agent’s current position (𝑟𝑜𝑤,𝑐𝑜𝑙). Action 𝑎 — movement direction choice from set 𝐴 = {Up,Down,Left,Right}.

Reward 𝑅(𝑠,𝑎,𝑠′):

- • +10 when transitioning to treasure state T

- • −5 when transitioning to trap state X

- • −0.1 for all other transitions (including boundary exit attempts)

Terminal states — states marked T and X. For terminal states 𝑉(𝑇) = 𝑉(𝑋) = 0, as no transitions are possible from them.

Value Function and Algorithm Value function 𝑉(𝑠) — expected total discounted reward under optimal policy starting from state 𝑠. Bellman equation for optimal value:

𝑉∗(𝑠) = max

[𝑅(𝑠,𝑎) + 𝛾 ⋅ 𝑉∗(𝑠′)] 𝑎∈𝐴

Value Iteration algorithm: 1. Initialization: 𝑉0(𝑠) = 0 for all states 𝑠 2. Iteration: For 𝑘 = 1 to 100:

𝑉𝑘(𝑠) = max

[𝑅(𝑠,𝑎) + 𝛾 ⋅ 𝑉𝑘−1(𝑠′)] 𝑎∈𝐴 where 𝑠′ — next state when taking action 𝑎 from state 𝑠 3. Result: 𝑉100(𝑆) — value of starting state after 100 iterations

Example For grid:

....T .X... S..X. .....

Key point coordinates:

- • 𝑆: (2,0)

- • 𝑇: (0,4)

- • 𝑋: (1,1) and (2,3)

After 1st iteration:

- • 𝑉(0,3) = 𝑅 + 𝛾 ⋅ 𝑉(𝑇) = 10 + 0.9 ⋅ 0 = 10.0 (directly before treasure)

- • 𝑉(2,0) = max𝑎[𝑅 + 𝛾 ⋅ 𝑉(𝑠′)] = −0.1 + 0.9 ⋅ 0 = −0.1 (starting position)

Input Data

File grid.txt in UTF-8 encoding, containing 𝐻 lines of 𝑊 characters (S, T, X, .). Example content:

....T .X... S..X. .....

Output Data

Archive task8.zip containing three files in UTF-8 encoding:

1. map.txt Coordinates of key points in format type row col (each point on new line): S 2 0 T 0 4

X 1 1

X 2 3

2. v1.txt Matrix of value function values after 1st iteration (𝐻 lines of 𝑊 numbers with precision of 1 decimal place, separated by spaces):

-0.1 -0.1 -0.1 10.0 0.0

-0.1 0.0 -0.1 -0.1 -0.1

-0.1 -0.1 -0.1 0.0 -5.0

-0.1 -0.1 -0.1 -0.1 -0.1

3. result.txt Value 𝑉(𝑆) after 100 iterations (6 decimal places):

7.500000

Grading Criteria

| № | Criterion | Points |
| --- | --- | --- |
| 8.1 | Correct map parsing and coordinate determination | 20 |
| 8.2 | Correct implementation of one Value Iteration step | 40 |
| 8.3 | Accurate computation of 𝑉(𝑆) after 100 iterations | 40 |
| Total |  | 100 |

Technical Requirements

- • Algorithm parameters: 𝛾 = 0.9, number of iterations = 100

- • Calculation precision: ±0.01 for 𝑉(𝑆)

- • All files must be in UTF-8 encoding

- • Solution must be deterministic and reproducible

# Citations

1. [ioai26 task tour1 en](https://lk-dovuz.innopolis.university/public/files/ioai26_task_tour1_en.pdf), file 0f3f37b25f84
