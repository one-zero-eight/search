---
type: page
title: "Past exam papers: System and Network Administration"
description: "Past exams and tests of System and Network Administration at Innopolis University (3 papers, 2021–2025), collected by students: tasks, formats, points."
resource: "https://glebpopov.notion.site/4ef3de0c7e68495b89ef086301361603"
tags: ["past-papers", "exams", "bachelor", "system-and-network-administration"]
audience: ["student"]
source_kind: community
language: en
section: "notion/past-papers"
subject: "System and Network Administration"
sources:
  - resource: "https://glebpopov.notion.site/4ef3de0c7e68495b89ef086301361603"
    title: "IU B23 Academic Materials: Past Papers [EN programs]"
generated:
  by: "catix-wiki/0.1 past-papers (code only, no model)"
status: draft
---

# Past exam papers: System and Network Administration

Exams and tests of **System and Network Administration** from previous years, as the students collected them in [IU B23 Academic Materials: Past Papers [EN programs]](https://glebpopov.notion.site/4ef3de0c7e68495b89ef086301361603). Not an official source: a paper may be one variant of several, or written down from memory. Newest first.

## 2025: Midterm

Files: [SNA Midterm 2025.pdf](https://glebpopov.notion.site/1c7e746cceef80c9a77bf04d7b8bc5b5)


Оставшееся время 0:33:25
Вопрос 1
Ответ сохранен
Балл: 1,00

Consider the following log:

What will be the result when you run the following command: cat log.txt | cut -d" " -f6

a. TLS
b. girafalez/202.202.202.202:1194
c.

Error

d. openvpn[76395]:

Очистить мой выбор

Оставшееся время 0:33:11
Вопрос 2
Ответ сохранен
Балл: 1,00

Which of these cron jobs will execute at 04:00, 05:00, and 06:00 every day?
a. 4-6 0 * * * /home/user/job.sh
b. 0 4-6 * * * /home/user/job.sh
c.

* 4-6 * * * /home/user/job.sh

d. 4-6 * * * * /home/user/job.sh

Очистить мой выбор

Оставшееся время 0:33:04
Вопрос 3
Ответ сохранен
Балл: 1,00

How many bytes are we going to extract in total from /dev/sda with the following command?

a. 1024
b. 1536
c.

2048

d. 512

Очистить мой выбор

Оставшееся время 0:32:59
Вопрос 4
Ответ сохранен
Балл: 1,00

Consider the following log

Which of these regexes will match the string “girafalez/202.202.202.202:1194”

a. \w+\/\d+\.\d+\.\d+\.\d+:\d+
b. \w\/\d+\.\d+\.\d+\.\d+:.+
c.

\w+\/\d\.\d\.\d\.\d:\d

d. \w\/\d+\.\d+\.\d+\.\d+:\d+

Очистить мой выбор

Оставшееся время 0:32:53
Вопрос 5
Ответ сохранен
Балл: 1,00

Consider the following SELinux configuration file /etc/selinux/config:

Which of these commands will modify only the sixth line and change it to “SELINUX=enforcing”?
a. sed -i 's/SELINUX=enforcing/SELINUX=disabled/g' /etc/selinux/config
b. sed -i '/SELINUX=disabled/SELINUX=enforcing/' /etc/selinux/config
c.

sed -i 's/disabled/enforcing/g' /etc/selinux/config

d. sed -i 's/SELINUX=disabled/SELINUX=enforcing/g' /etc/selinux/config

Очистить мой выбор

Оставшееся время 0:32:47
Вопрос 6
Ответ сохранен
Балл: 1,00

Which of the options will you consider to run a job only once at 07:00
a. Create an anacron job to execute @daily at 07:00
b. Use the at utility to create the job with the command “at 07:00 -f /home/job.sh”
c.

All the options are valid

d. Run “crontab -e” and schedule the job “0 7 * * * /home/job.sh”

Очистить мой выбор

Оставшееся время 0:32:42
Вопрос 7
Ответ сохранен
Балл: 1,00

The provided docker-compose.yml file contains problems that may cause issues when running Docker Compose,
preventing the services from running. Identify the correct option to fix the issues.

a. Add a blank line between the services keyword and the first service definition.
b. Indent the image, ports, volumes, and environment keys under each service definition correctly.
c.

Ensure all service names are aligned with the services keyword.

d. The secrets are hardcoded.
e. Use double quotes (") consistently for all string values in the YAML file.

Очистить мой выбор

Оставшееся время 0:32:36
Вопрос 8
Ответ сохранен
Балл: 1,00

Consider the following bash script:

Which of the following statements IS TRUE when the bash script is executed?
a. The script will exit when you press Ctrl + C
b. The script will print "Script is running…" on the terminal output every 5 mins
c.

The trap command sets the sig_x function to be called when a SIGKILL signal is received

d. The script will be suspended when you press Ctrl + Z

Очистить мой выбор

Оставшееся время 0:32:30
Вопрос 9
Ответ сохранен
Балл: 1,00

Which of the following is NOT TRUE when you run the following command on a bash shell?
$ sudo sh -c "mv /home/user/file.txt /home/user/newfile.txt"
Note: You have both /bin/bash and /bin/sh on the computer.

a. The command renames file.txt to newfile.txt
b. The only new process created by this command is the mv process
c.

The command spawns a new shell to execute the mv command

d. The mv command is executed with super user privileges

Очистить мой выбор

Оставшееся время 0:32:26
Вопрос 10
Ответ сохранен
Балл: 1,00

A GPT drive is prevented from being overwritten by older systems by all of the following except?
a. The MBR header contains a flag that indicates the disk is not MBR bootable
b. All the options are valid
c.

By labeling the entire GPT disk as one partition with protective MBR

d. The last block of the disk contains the protective MBR

Очистить мой выбор

Оставшееся время 0:32:22
Вопрос 11
Ответ сохранен
Балл: 1,00

All of these options are TRUE for UEFI booting on Ubuntu except one:
a. Shim loads GRUB bootloader
b. The firmware validates and loads the shim binary
c.

GRUB gives users the privilege to make changes during boot time

d. All the options are true

Очистить мой выбор

Оставшееся время 0:32:17
Вопрос 12
Ответ сохранен
Балл: 1,00

Consider the following systemd service “test1.service”

Which of the following is FALSE?
a. test1.service will fail if test3.service fails to start
b. test1.service and test2.service can be started in parallel
c.

All the statements are true

d. test1.service will fail if test2.service fails to start

Очистить мой выбор

Оставшееся время 0:32:13
Вопрос 13
Ответ сохранен
Балл: 1,00

Which of these Bash variables contain the exit code of the last command you executed?
a. $$
b. !!
c.

$!

d. $?

Очистить мой выбор

Оставшееся время 0:32:09
Вопрос 14
Ответ сохранен
Балл: 1,00

Which of these options will you consider to manage process resource allocation?
a. free
b. cgtop
c.

top

d. cgroup

Очистить мой выбор

Оставшееся время 0:32:05
Вопрос 15
Ответ сохранен
Балл: 1,00

You can install a package via these options except one:
a. Download the package from the maintainer’s official website and install it
b. Install the package with your package manager
c.

All the options are valid

d. Build the package from the source code, and then install it

Очистить мой выбор

Оставшееся время 0:32:00
Вопрос 16
Ответ сохранен
Балл: 1,00

You have been given a task to completely erase a disk in a manner that will make it impossible to recover files from the
disk afterwards. Which of these options will you consider?
a. Use dd to write bit stream of zeros (/dev/zero) to the disk
b. This is not possible
c.

Use lsblk to view available devices and then mkfs to format

d. Use the fdisk utility

Очистить мой выбор

Оставшееся время 0:31:56
Вопрос 17
Ответ сохранен
Балл: 1,00

You're responsible for setting up a CI/CD pipeline for a project hosted on GitLab. The pipeline should include stages for
building the application, running tests, and deploying to multiple environments based on GitLab branches. Which of the
following steps would be essential in configuring this pipeline using GitLab CI/CD?
a. Configure GitLab project settings to enable CI/CD and specify triggers such as branch updates or merge
requests to start pipeline runs.
b. Use Docker containers as runners to execute pipeline jobs and ensure consistent build environments across
different stages.
c.

Install and configure Jenkins on a dedicated server to serve as the CI/CD orchestrator for the GitLab
repository.

d. Define a .gitlab-ci.yml file in the root directory of the GitLab repository to specify the pipeline stages and jobs.

Очистить мой выбор

Оставшееся время 0:31:51
Вопрос 18
Ответ сохранен
Балл: 1,00

What is the primary difference between the docker-compose up and docker-compose start commands in Docker
Compose?
a. docker-compose up starts and initializes containers for all services defined in the Docker Compose file,
including building images if necessary, while docker-compose start only starts containers that are already
created but stopped.
b. docker-compose up is a deprecated command, and docker-compose start should be used instead for
starting Docker containers defined in a Docker Compose file.
c.

docker-compose up and docker-compose start are interchangeable commands that both start Docker
containers defined in a Docker Compose file.

d. docker-compose up is used to start containers defined in a Docker Compose file, whereas dockercompose start is used to scale the number of running instances for a particular service.

Очистить мой выбор

Оставшееся время 0:31:47
Вопрос 19
Ответ сохранен
Балл: 1,00

What will be the output when you run the following bash script?

a. Vlad in class later
b. class
c.

Vlad

d. late

Очистить мой выбор

Оставшееся время 0:31:42
Вопро

(the rest is in the file)

## 2021: Final

Files: [SNA Final 2021.pdf](https://glebpopov.notion.site/14ee746cceef8067be34dd3355161449)


Project Assignment: System and Network
administration
Project description
In this group project, you will work on the idea, which should be related to the materials
covered in the course. This is the time where you can apply your system and
administration skills.

Dividing into groups
Firstly, group your teammates (3-4) people. Then use this link where you fill the project
details. The deadline for project approval is by Thursday 02.11.2021. Once the project is
approved you can start to work on it.

Project Report
The report should contain the following sections:
I.
Goal/Tasks of the Project - what are you going to solve
II.
Execution plan/Methodology - plan for the solution
III.
Utilization of solution/Tests - explanation of the solution
IV.
Difficulties faced
V.
Your conclusion, your contemplations and judgement
Be aware to include all important links to open repos as the proof of concept and
demonstration video. Long appendixes are ok in the report

Deliverables
The report should be uploaded in the Moodle by each member of the group (the same
pdf file and a demo). The demo should contain proof of concepts, to demonstrate what
has been done, implemented solution.
Also, you can use open repos such as GitHub, Docker hub etc. for storing scripts,
configurations files, dockerfiles/containers etc.
● Summary
○ Project proposal deadline - by December, 2nd
○ No more than 3 or 4 members per group
○ Project reports deadline - by December, 13th
○ Report + demo should be submitted

Some examples of project ideas that can be taken
The following is a list of common projects that can be implemented within the project:
● Deployment of VPC with firewall rules to VM in AWS
● Deployment of VPC with firewall rules to VM in GCP
● Deployment of VPC with firewall rules to VM in Yandex
● Implementation load-balancer with backend in VM (DB, web server) in AWS
● Implementation load-balancer with backend in VM (DB, web server) in GCP
● Implementation load-balancer with backend in VM (DB, web server) in Yandex
● Implementation PostgreSQL cluster using Patroni (link for repo will be provided)
● Implementations of Nginx load balancer with backends
● Implementations of HAproxy load balancer with backends
● Using Docker-Compose to deploy your application with frontend and backend
● Implementations of Nginx as a proxy for backends
Note: You can choose only one topic per group

## 2021: Midterm

Files: [SNA Midterm 2021.pdf](https://glebpopov.notion.site/14ee746cceef80a89dbee982bad8a306)


Dashboard / My courses / [F21]S&NA / Week 04 / Midterm Exam

Question 1
Not yet answered
Marked out of 2.00

How do you create a crontab entry in order to run the script?
a. crontab -c
b. crontab -e
c. crontab --help
d. crontab -open

Question 2
Not yet answered
Marked out of 2.00

Which of the following commands return the exit status of the last command?
a. $$
b. $#
c. $!
d. $?

Question 3
Not yet answered
Marked out of 2.00

Which command is used to delete a user along with its home directory?
a.

userdel -R username

b.

userdel -r username

c. userdel -D username
d. userdel -d username

Time left 0:59:55

Question 4
Not yet answered
Marked out of 5.00

What is a daemon? What is a service?

Maximum file size: 100MB, maximum number of files:
2









Files

You can drag and drop files here to add them.

Question 5
Not yet answered
Marked out of 2.00

Which command is used to check the Linux version?
a. uname -n
b. uname -s
c. uname -p
d.

uname -a

Question 6
Not yet answered
Marked out of 5.00

Describe the essential DNS records?

Maximum file size: 100MB, maximum number of files:
1









Files

You can drag and drop files here to add them.

Question 7
Not yet answered
Marked out of 2.00

How we can see hidden files in the directory
a. ls -l
b. ls
c. ls -a
d. ls -h

Question 8
Not yet answered
Marked out of 2.00

Assume you want to add executable permission for the group on the file. What type of command below is appropriate to use
a. chmod 766 file1
b. chmod 010 file1
c. chown 777 file1
d. chown u+g file1

Question 9
Not yet answered
Marked out of 2.00

The process which terminates before the parent process exits is known as
a. Zombie

b. None of the above
c. Child
d. Orphan

Question 10
Not yet answered
Marked out of 5.00

Describe the key components of an email system

Maximum file size: 100MB, maximum number of files:
1









Files

You can drag and drop files here to add them.

Question 11
Not yet answered
Marked out of 2.00

Which directory in Linux contains all the config file of the system
a. /etc
b. /tmp
c. /var
d. /lib

Question 12
Not yet answered
Marked out of 5.00

Describe identity and access management in Linux

Maximum file size: 100MB, maximum number of files:
1









Files

You can drag and drop files here to add them.

Question 13
Not yet answered
Marked out of 2.00

You have a range of IP addresses 10.90.100.0/24:
1. Identify subnet range
2. How many usable IP addresses?
3. Identify starting IP and ending IP

Question 14
Not yet answered
Marked out of 5.00

Describe how the DNS translation works?

Maximum size for new files: 100MB









Files

You can drag and drop files here to add them.

Question 15
Not yet answered
Marked out of 2.00

file permission with -wxrwx--x is equivalent to numeric
a. 572
b. 371
c. 675
d. 567

◄ Lecture 07
Jump to...

Data retention summary
Get the mobile app

# Citations

1. [IU B23 Academic Materials: Past Papers [EN programs]](https://glebpopov.notion.site/4ef3de0c7e68495b89ef086301361603)
