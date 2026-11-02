![](https://help.university.innopolis.ru/%D0%B7%D0%BD%D0%B0%D0%BA_%D0%B7%D0%B5%D0%BB%D0%B5%D0%BD%D1%8B%D0%B9.png)
ITHelp Wiki
/ sidebar.root
Сервисы
AzureDevOps
Текущий каталог
[Ошибки при работе в AzureDevOps (SSH доступы)](https://help.university.innopolis.ru/ru/Сервисы/AzureDevOps/AzureDevOps_Error_SSH)
- /
[Сервисы](https://help.university.innopolis.ru/ru/Сервисы)
- /
[AzureDevOps](https://help.university.innopolis.ru/ru/Сервисы/AzureDevOps)
- /
[AzureDevOps_Error_SSH](https://help.university.innopolis.ru/ru/Сервисы/AzureDevOps/AzureDevOps_Error_SSH)
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
Университет Иннополис | Powered by [Wiki.js](https://wiki.js.org)