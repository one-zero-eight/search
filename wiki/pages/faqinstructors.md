---
type: page
title: "FAQInstructors"
description: "A guide for instructors on how to use the Innopolis University wiki, covering editing, formatting, tables, math, and content import/export."
resource: "https://eduwiki.innopolis.university/index.php/FAQInstructors"
tags: ["wiki", "media", "instructors", "faq", "editing"]
sources:
  - resource: "https://eduwiki.innopolis.university/index.php/FAQInstructors"
    id: "9681"
    title: "FAQInstructors"
    last_modified: "2024-12-04T20:40:04Z"
generated:
  by: "catix-wiki/0.1 (local)"
  at: "2026-10-22T01:22:41+00:00"
status: draft
stale_after: "2026-12-04T20:40:04+00:00"
---

# FAQInstructors

## Introduction to MediaWiki

The MediaWiki software is used by tens of thousands of websites and thousands of companies and organizations. It powers Wikipedia and also this website. MediaWiki helps you collect and organize knowledge and make it available to people. It's powerful, multilingual, free and open, extensible, customizable, reliable, and free of charge.

## Content editing

### How to log in the system?

Use your regular credentials for this purpose: user@innopolis.ru and the password from your account.
If you cannot log in, please contact the IT-department [@iuithelp](https://t.me/iuithelp)

### How to create a page?

** From the search box **
If you search for a page that doesn't exist, then you will be provided with a link to create the new page.

** Using the URL **
You can use the wiki's URL for creating a new page.

The URL to an article of the wiki is usually something like this:
- https://eduwiki.innopolis.university/index.php/ARTICLE

If you replace ARTICLE with the name of the page you wish to create, you will be taken to a blank page which indicates that no article of that name exists yet.

<blockquote>To get more detailed information you can refer to the user's manual: 
[Help: Starting a new page](https://www.mediawiki.org/wiki/Help:Starting_a_new_page)</blockquote>

### How to edit a page?

Clicking the "Edit" page tab at the top of the page will take you to the edit page for that article, where you can create the new page by typing your text, and clicking submit. Moreover, if you need not edit the whole page but only its part, you can click on "Edit" link related to this certain part and work only with it. If the text is so long it helps to save a time.

Note that only the authorized users are able to edit the content.

<blockquote>Here you can get more information about the editing process: [Help:Editing pages](https://www.mediawiki.org/wiki/Help:Editing_pages)</blockquote>

### How to work with text and its structuring?

<blockquote>Detailed user guide on text formatting: [MediaWiki: User guide](https://en.wikibooks.org/wiki/MediaWiki_User_Guide)</blockquote>

#### How to structurize a text?

Headings are created using sequences of "=" characters, placed before the heading title and after the heading title, on the same line. The level of headings is determined by the number of "=" characters.

Examples:

| Level | Example |
| --- | --- |
| 2. | ==Plants== |
| 3. | ===Plants=== |
| 4. | ====Plants==== |

*Start level:* 2

Do not use headings of level 1, such as "=Title="; start with level 2 instead. The heading at level 1 is used for the title of the page.

*Maximum level:* 6

The maximum level of a heading is 6, rendered using ======Heading L6======. Entering a heading with 7 equals-signs such as =======Heading L7======= results in the creation of a heading of the level 6, with one equal-sign becoming part of the text of the heading: "=Heading L7=".

<blockquote>See more details here: [MediaWiki user guide: sections and headings](https://en.wikibooks.org/wiki/MediaWiki_User_Guide/Sections_and_Headings)</blockquote>

#### How to format text?

The following is an overview of text formatting available in Mediawiki:

**Basic text formatting**

| Formatting | Markup | Note |
| --- | --- | --- |
| **Boldface** | <code><nowiki>**text**</nowiki></code> |  |
| *Italics* | <code><nowiki>*text*</nowiki></code> |  |
| ***Boldface and italics*** | <code><nowiki>***text***</nowiki></code> |  |
| **Boldface combined with wikilink** | <code><nowiki>**text**</nowiki></code> | The reverse order of ticks and brackets does not work: <code><nowiki>**text**</nowiki></code> |

Other text formatting such as underline or blockquote needs to be done using HTML tags, including U for underline, TT for typewriter text, S for strikethrough, SUB for lower index and SUP for upper index.

#### How to use HTML tags?

Text formatting can also be done using HTML and CSS. Some of the most useful HTML elements are:

**Most needed HTML markup**

| Task | Markup | Note |
| --- | --- | --- |
| Preformatted text | <syntaxhighlight lang="html"> <br> <pre> <br> preformatted <br> </pre> <br> </syntaxhighlight> | The effect in wiki differs from the one in HTML; in wiki, the text within the PRE element is treated as within NOWIKI element, leaving all the HTML and wiki markup uninterpreted. |
| Blockquote | <syntaxhighlight lang="html"><blockquote>Longer passage.</blockquote></syntaxhighlight> |  |
| Comments | <syntaxhighlight lang="html"></syntaxhighlight> | Avoid nesting, such as <syntaxhighlight lang="html"> --></syntaxhighlight> |
| Generic inline element | <syntaxhighlight lang="html"></syntaxhighlight> | Can be styled arbitrarily using cascading style sheets - CSS. |
| Generic block element | <syntaxhighlight lang="html"></syntaxhighlight> | Can be styled arbitrarily using cascading style sheets - CSS. |

Some HTML elements are not allowed, such as A and IMG.

#### How to work with lists?

Bullet lists:

| Example Syntax | Example Output |
| --- | --- |
| * a <br> ** b <br> ** c <br> *** d | * a <br> ** b <br> ** c <br> *** d |

Numbered lists:

| Example Syntax | Example Output |
| --- | --- |
| # a <br> ## b <br> ## c <br> ### d | # a <br> ## b <br> ## c <br> ### d |

Definition lists:

| Example Syntax | Example Output |
| --- | --- |
| ; defined term : definition <br> ; defined term 2 : definition 2 | ; defined term : definition <br> ; defined term 2 : definition 2 |

Mixed lists:

| Example Syntax | Example Output |
| --- | --- |
| * a <br> *# b <br> *# c | * a <br> *# b <br> *# c |

#### How to insert a link?

There are five types of hypertext links in MediaWiki, but two of them are the mostly used:

- Internal links to other pages in the same wiki (commonly called "wikilinks")
- External links to pages at other websites

** Internal hyperlinks **

| Task | Markup |
| --- | --- |
| Internal hyperlink | <nowiki>keyword</nowiki> |
| Internal hyperlink  to a section | <nowiki>link title</nowiki> |
| Internal hyperlink showing a different word | <nowiki>its appearance</nowiki> |
| Internal hyperlink with a tooltip | <nowiki>its appearance</nowiki> |
| Internal hyperlink in bold | <nowiki>**keyword**</nowiki> |

** External hyperlinks **

| Task | Markup |
| --- | --- |
| External hyperlink | <nowiki>[URL_containing_no_spaces title of the URL]</nowiki> |

<blockquote>You can also fing some more details here: [Help: links](https://www.mediawiki.org/wiki/Help:Links)</blockquote>

### How to format tables?

The following code
<pre>
| Left | Center | Right |
| --- | --- | --- |
| Top left cell | Top center cell | Top right cell |
| Middle left cell | Middle center cell | Middle right cell |
| Bottom left cell | Bottom center cell | Bottom right cell |
</pre>

gives the following:

| Left | Center | Right |
| --- | --- | --- |
| Top left cell | Top center cell | Top right cell |
| Middle left cell | Middle center cell | Middle right cell |
| Bottom left cell | Bottom center cell | Bottom right cell |

<blockquote>Basics: [MediaWiki User guide: Tables](https://en.wikibooks.org/wiki/MediaWiki_User_Guide/Tables)</blockquote>

<blockquote>Advanced: [Wiki: Tables](https://en.wikipedia.org/wiki/Help:Table)</blockquote>

### How to work with math formulas?

You can enter mathematical formulas into a wiki, using a <code>math</code> tag, such as:

<pre>
<math>\sqrt{2}</math>
</pre>

The formulas are marked up in the TeX markup, the markup of a complex typesetting system specialized on mathematics.


To get started, follow the examples below.


**Examples of mathematical markup**

| No. | Desired Effect | Markup |
| --- | --- | --- |
| 1. | <math>\alpha</math> | <syntaxhighlight lang="tex"><math>\alpha</math></syntaxhighlight> |
| 2. | <math>\sqrt{2}</math> | <syntaxhighlight lang="tex"><math>\sqrt{2}</math></syntaxhighlight> |
| 3. | <math>\sqrt{1-e^2}</math> | <syntaxhighlight lang="tex"><math>\sqrt{1-e^2}</math></syntaxhighlight> |
| 4. | <math>\frac{2}{4}=0.5</math> | <syntaxhighlight lang="tex"><math>\frac{2}{4}=0.5</math></syntaxhighlight> |
| 5. | <math>\sum_{k=1}^N k^2</math> | <syntaxhighlight lang="tex"><math>\sum_{k=1}^N k^2</math></syntaxhighlight> |
| 6. | <math>\int\limits_{1}^{3}\frac{e^3/x}{x^2}\, dx</math> | <syntaxhighlight lang="tex"><math>\int\limits_{1}^{3}\frac{e^3/x}{x^2}\, dx</math></syntaxhighlight> |
| 7. | <math>\begin{bmatrix} <br> 0      & \cdots & 0      \\ <br> \vdots & \ddots & \vdots \\ <br> 0      & \cdots & 0 <br> \end{bmatrix}</math> | <syntaxhighlight lang="tex" style="border: none;><math>\begin{bmatrix} <br> 0      & \cdots & 0      \\ <br> \vdots & \ddots & \vdots \\ <br> 0      & \cdots & 0 <br> \end{bmatrix}</math></syntaxhighlight> |
| 8. | <math>\begin{pmatrix} <br> x & y \\ <br> z & v <br> \end{pmatrix}</math> | <syntaxhighlight lang="tex" style="border: none;"><math>\begin{pmatrix} <br> x & y \\ <br> z & v <br> \end{pmatrix}</math></syntaxhighlight> |

### How to put a source code?

The following code:
<pre>
‎<syntaxhighlight lang="python" line>
def quick_sort(arr):
	less = []
	pivot_list = []
	more = []
	if len(arr) <= 1:
		return arr
	else:
		pass
‎</syntaxhighlight>
</pre>
gives:
‎<syntaxhighlight lang="python" line>
def quick_sort(arr):
	less = []
	pivot_list = []
	more = []
	if len(arr) <= 1:
		return arr
	else:
		pass‎</syntaxhighlight>

<blockquote>See the documentation of the syntaxhighlight-extension here: [Syntax highlight](https://www.mediawiki.org/wiki/Extension:SyntaxHighlight)</blockquote>

### How to add TikZ-flowchart?

With the use of the special extension you can embed the TikZ-flowchart written in LaTex directly to your page within the tag <pre><PGTikZ></pre>.
For examle, the following code
<pre><PGFTikZ>


<PGFTikZPreamble>

\usepackage{tikz}
\usetikzlibrary{arrows}
\usetikzlibrary{intersections}
\usetikzlibrary{calc}

</PGFTikZPreamble>
\begin{tikzpicture}[scale=.8,every node/.style={minimum size=1cm}]
%
   \begin{scope}[
           yshift=-83,every node/.append style={
           yslant=0.5,xslant=-1},yslant=0.5,xslant=-1
           ]
       \draw[step=4mm, black] (0,0) grid (5,5); 
       \draw[black,thick] (0,0) rectangle (5,5);%borders
       \fill[green] (2.05,2.05) rectangle (2.35,2.35); % center pixel
       \fill[green] (1.65,2.05) rectangle (1.95,2.35); %left
       \fill[green] (2.45,2.05) rectangle (2.75,2.35); %right
       \fill[green] (2.05,2.45) rectangle (2.35,2.75); %top
       \fill[green] (2.05,1.95) rectangle (2.35,1.65); %bottom

   \end{scope}
%
% draw annotations
%
   \draw[-latex,thick,green](-3,-2)node[left]{1 patch}
       to[out=0,in=200] (-1,-.9);
\end{tikzpicture}
</PGFTikZ>
</pre>

<PGFTikZ>


<PGFTikZPreamble>

\usepackage{tikz}
\usetikzlibrary{arrows}
\usetikzlibrary{intersections}
\usetikzlibrary{calc}

</PGFTikZPreamble>
\begin{tikzpicture}[scale=.8,every node/.style={minimum size=1cm}]
%
   \begin{scope}[
           yshift=-83,every node/.append style={
           yslant=0.5,xslant=-1},yslant=0.5,xslant=-1
           ]
       \draw[step=4mm, black] (0,0) grid (5,5); 
       \draw[black,thick] (0,0) rectangle (5,5);%borders
       \fill[green] (2.05,2.05) rectangle (2.35,2.35); % center pixel
       \fill[green] (1.65,2.05) rectangle (1.95,2.35); %left
       \fill[green] (2.45,2.05) rectangle (2.75,2.35); %right
       \fill[green] (2.05,2.45) rectangle (2.35,2.75); %top
       \fill[green] (2.05,1.95) rectangle (2.35,1.65); %bottom

   \end{scope}
%
% draw annotations
%
   \draw[-latex,thick,green](-3,-2)node[left]{1 patch}
       to[out=0,in=200] (-1,-.9);
\end{tikzpicture}
</PGFTikZ>

<blockquote>See the instructions here: [PGTikZ](https://www.mediawiki.org/wiki/Extension:PGFTikZ)</blockquote>

### How to paste pictures?

Mediawiki supports the use of images in various formats. In order to be used in a wiki, image first needs to be uploaded. To upload the picture please use the link "Upload file" in the left menu column of the page and follow the certain instructions.

The following is an overview of placing images into pages, such images that have already been uploaded.

**Placing of images**

| Task | Markup | Default Frame | Note |
| --- | --- | --- | --- |
| Image | <nowiki></nowiki> | No | The image is shown in its full size as found in the file. |
| Image with thumb | <nowiki></nowiki> | Yes | Thumbs are always scaled down so as not to exceed an upper limit on the size. |
| Image without thumb, with restricted size | <nowiki></nowiki> | No |  |

<blockquote>To know about other feature please refer to: [MediaWiki User Guide: images](https://en.wikibooks.org/wiki/MediaWiki_User_Guide/Images)</blockquote>

### How to embed a Google document into mediawiki page?
Special extension allows to embed Google Docs' spreadsheets into the wiki page.

Supported parameters are:
| Name | Default |
| --- | --- |
| **width** | 500 |
| **height** | 300 |
| **style** | width:100% |

As an example using all of the parameters:

<pre><googlespreadsheet width="600" height="200" style="width:50%">Google Docs' key goes here</googlespreadsheet></pre>

To actually embed a spreadsheet, the spreadsheet needs to be published with Google's **File** > **Publish to Web...** option. It is not sufficient to just have a shareable link.

## Content import / export

### How to import content?

** From Latex file **

To upload your syllabus from Latex to MediaWiki use the toolkit developed by our students:

- [Syllabus in Latex: import ](https://dev.digitalprofile.innopolis.university/generator/eduwiki/upload)

### How to export content?

#### To PDF-file

To get a printable version of the certain page use the link **Printable version** at the left column of the page. After the page is generated you may print it as usually.

# Citations

1. [FAQInstructors](https://eduwiki.innopolis.university/index.php/FAQInstructors), revision 9681
