# InNoHassle browser extension

## Where do I get the extension?

https://innohassle.ru/extension, for Chrome, Edge and Firefox.

## What can the extension do?

- Moodle autologin, useful links.
- A search field: the same catix search as `/search`.
- Downloading a whole course as a ZIP, from the popup or the "Download course" button on a Moodle course page.
- A toggle between in-progress and all courses.

## How do I send Moodle data to InNoHassle?

- The popup has a toggle labelled "Send Moodle data to InNoHassle".
- It sends the calendar, deadlines, grades, progress, and the text and files of your courses. These feed your InNoHassle calendar, recommendations, and catix search over your course materials.
- Course files, pages, announcements and assignment dates are also shared with the students of your verified study group. Grades, submissions and progress never are.
- Turning the toggle off stops sending new data. Data already sent stays.

## Which files are read?

- `.pdf .doc .docx .rtf .odt .ppt .pptx .odp .xls .xlsx .ods .txt .md .png .jpg .jpeg .webp`, up to 100 MiB.
- PDFs over 150 pages are skipped. Scans over 40 pages are skipped.

## How do I see the sync status?

The popup shows per-course states: Waiting, Syncing, Sent, Up to date, Some files not uploaded, Failed. Failed and incomplete courses are retried at the next sync.
