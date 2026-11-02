---
type: page
title: "Ошибки при работе в AzureDevOps (SSH доступы)"
description: "Ошибки при работе в AzureDevOps (SSH доступы)"
resource: "https://help.university.innopolis.ru/ru/%D0%A1%D0%B5%D1%80%D0%B2%D0%B8%D1%81%D1%8B/AzureDevOps/AzureDevOps_Error_SSH"
audience: ["staff"]
source_kind: website
language: ru
section: "site/help"
sources:
  - resource: "https://help.university.innopolis.ru/ru/%D0%A1%D0%B5%D1%80%D0%B2%D0%B8%D1%81%D1%8B/AzureDevOps/AzureDevOps_Error_SSH"
    id: "db1c87a22970"
    title: "Ошибки при работе в AzureDevOps (SSH доступы)"
    last_modified: "2026-10-31T10:19:07+00:00"
generated:
  by: "catix-wiki/0.1 sites"
  at: "2026-10-31T10:19:07+00:00"
status: draft
---

# Ошибки при работе в AzureDevOps (SSH доступы)

Сервисы

AzureDevOps

[Сервисы](https://help.university.innopolis.ru/ru/Сервисы)

[AzureDevOps](https://help.university.innopolis.ru/ru/Сервисы/AzureDevOps)

[AzureDevOps_Error_SSH](/raw/sites/help/ru-azuredevops-azuredevops-error-ssh.md)

Ошибки при работе в AzureDevOps (SSH доступы)

## ¶ Ошибка: no matching key exchange method found

Например при клонировании репозитория в AzureDevOps может возникнуть ошибка

Unable to negotiate with port 22: no matching key exchange method found

Скриншот ошибки:

![image_1699598945619.png](https://help.university.innopolis.ru/images/image_1699598945619.png)

## ¶ Решение ошибки для Linux:

Для решения этой проблемы необходимо корректно создать пару ключей в Azure DevOps

Создайте пару ключей id_rsa и id_rsa.pub.

Откройте файл конфигурации ssh

sudo nano /etc/ssh/ssh_config

- Добавьте следующие строки:

Host code.university.innopolis.ru HostkeyAlgorithms +ssh-rsa PubkeyAcceptedAlgorithms +ssh-rsa IdentityFile ~/.ssh/id_rsa IdentitiesOnly yes KexAlgorithms +diffie-hellman-group1-sha1

или на старом TFS

Host tfs.university.innopolis.ru HostkeyAlgorithms +ssh-rsa PubkeyAcceptedAlgorithms +ssh-rsa IdentityFile ~/.ssh/id_rsa IdentitiesOnly yes KexAlgorithms +diffie-hellman-group1-sha1

- Сохраните

## ¶ Решение ошибки для Windows:

Создайте id_rsa и id_rsa.pub. [Инструкция для Azure DevOps(TFS)](https://learn.microsoft.com/en-us/azure/devops/repos/git/use-ssh-keys-to-authenticate?view=azure-devops)

По сути, эти файлы можно найти в ~/.ssh каталоге.

Создайте каталог config в ~/.ssh и вставьте эти атрибуты.

Host code.university.innopolis.ru HostkeyAlgorithms +ssh-rsa PubkeyAcceptedAlgorithms +ssh-rsa IdentityFile ~/.ssh/id_rsa IdentitiesOnly yes KexAlgorithms +diffie-hellman-group1-sha1

или на старом TFS

Host tfs.university.innopolis.ru HostkeyAlgorithms +ssh-rsa PubkeyAcceptedAlgorithms +ssh-rsa IdentityFile ~/.ssh/id_rsa IdentitiesOnly yes KexAlgorithms +diffie-hellman-group1-sha1

- Сохраните

## ¶ Ошибка: fatal: Authentication failed

Например при клонировании репозитория в TFS может возникнуть ошибка

fatal: Authentication failed for '[https://tfs.university.innopolis.ru](https://tfs.university.innopolis.ru)

Скриншот ошибки:

![image_1699600189276.png](https://help.university.innopolis.ru/images/image_1699600189276.png)

## ¶ Решение ошибки для Linux:

Для решения этой проблемы необходимо корректно создать пару ключей в Azure DevOps

Создайте пару ключей id_rsa и id_rsa.pub.

Откройте файл конфигурации ssh

sudo nano /etc/ssh/ssh_config

- Добавьте следующие строки:

Host code.university.innopolis.ru HostkeyAlgorithms +ssh-rsa PubkeyAcceptedAlgorithms +ssh-rsa IdentityFile ~/.ssh/id_rsa IdentitiesOnly yes KexAlgorithms +diffie-hellman-group1-sha1

или на старом TFS

Host tfs.university.innopolis.ru HostkeyAlgorithms +ssh-rsa PubkeyAcceptedAlgorithms +ssh-rsa IdentityFile ~/.ssh/id_rsa IdentitiesOnly yes KexAlgorithms +diffie-hellman-group1-sha1

- Сохраните

## ¶ Решение ошибки для Windows:

Создайте id_rsa и id_rsa.pub. [Инструкция для Azure DevOps(TFS)](https://learn.microsoft.com/en-us/azure/devops/repos/git/use-ssh-keys-to-authenticate?view=azure-devops)

По сути, эти файлы можно найти в ~/.ssh каталоге.

Создайте каталог config в ~/.ssh и вставьте эти атрибуты.

Host code.university.innopolis.ru HostkeyAlgorithms +ssh-rsa PubkeyAcceptedAlgorithms +ssh-rsa IdentityFile ~/.ssh/id_rsa IdentitiesOnly yes KexAlgorithms +diffie-hellman-group1-sha1

или на старом TFS

Host tfs.university.innopolis.ru HostkeyAlgorithms +ssh-rsa PubkeyAcceptedAlgorithms +ssh-rsa IdentityFile ~/.ssh/id_rsa IdentitiesOnly yes KexAlgorithms +diffie-hellman-group1-sha1

- Сохраните

_Меню, подвал и другие блоки, которые повторяются на страницах сайта, собраны в одном месте: [/raw/sites/help/_shared.md](/raw/sites/help/_shared.md)._

# Citations

1. [Ошибки при работе в AzureDevOps (SSH доступы)](https://help.university.innopolis.ru/ru/%D0%A1%D0%B5%D1%80%D0%B2%D0%B8%D1%81%D1%8B/AzureDevOps/AzureDevOps_Error_SSH), read 2026-10-31
