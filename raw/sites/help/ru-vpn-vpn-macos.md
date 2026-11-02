![](https://help.university.innopolis.ru/%D0%B7%D0%BD%D0%B0%D0%BA_%D0%B7%D0%B5%D0%BB%D0%B5%D0%BD%D1%8B%D0%B9.png)
ITHelp Wiki
/ sidebar.root
VPN
[VPN](https://help.university.innopolis.ru/ru/VPN)
Текущий каталог
VPN_Errors
[Подключение OpenVPN в Казанском офисе](https://help.university.innopolis.ru/ru/VPN/OpenVPN)
Подключение VPN к MacOS
[Подключение VPN к Manjaro](https://help.university.innopolis.ru/ru/VPN/VPN_Manjaro)
[Подключение VPN к Ubuntu GUI](https://help.university.innopolis.ru/ru/VPN/VPN_Ubuntu)
[Подключение VPN к Windows10](https://help.university.innopolis.ru/ru/VPN/VPN_Windows)
[Подключение VPN к Windows7](https://help.university.innopolis.ru/ru/VPN/VPN_Windows7)
- /
[VPN](https://help.university.innopolis.ru/ru/VPN)
- /
VPN_MACOS
Подключение VPN к MacOS
- 1 Подключение через L2TP
- 2.1 Подключение через SSTP терминал
- 2.2 Подключение через SSTP GUI
Заходим в Системные настройки; В открывшемся окне выбираем Сеть.
![](https://help.university.innopolis.ru/images/image_1697202994268.png)
Далее нажимаем на кнопку + чтобы добавить новое подключение;
![](https://help.university.innopolis.ru/images/image_1697203017538.png)
В открывшемся меню в пункте Интерфейс выбираем VPN;
![](https://help.university.innopolis.ru/images/image_1697203040859.png)
В Тип VPN указываем L2TP через IPSec,
Имя службы указываем University VPN
и нажимаем «Cоздать»
![](https://help.university.innopolis.ru/images/image_1697203070450.png)
В поле Адрес сервера пишем [vpn.university.innopolis.ru](http://vpn.university.innopolis.ru)
Имя учетной записи пишем свою доменную учетную запись
(пример заполнения на картинке) и нажимаем Настройки аутентификации
![](https://help.university.innopolis.ru/images/image_1697203106303.png)
В настройках аутентификации
в поле Пароль вводим пароль от доменной учетной записи
в поле Общий ключ (Shared Secret) вводим общий ключ q7J>k2%[Lx
и нажимаем OK;
![](https://help.university.innopolis.ru/images/image_1697203126797.png)
После выполненных действий нажимаем кнопку Подключить;
![](https://help.university.innopolis.ru/images/image_1697203153014.png)
Если все было введено верно, то статус подключения поменяется на подключено и будет указано время подключения и ip адрес;
![](https://help.university.innopolis.ru/images/image_1697203177451.png)
Мы не несем ответственности за установку и использование сторонних клиентов, все это вы используете на ваш страх и риск!
Штатный SSTP Client для Mac OS не существует. Установка только через сторонний репозиторий Brew.
[Ссылка на Brew](https://brew.sh/)
Если у вас не установлен Brew то: открываем терминал и вводим
/bin/bash -c “$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)”
Процесс добавления репозитория достаточно долгий. Необходимо дождаться полного завершения процесса.
В терминале вводим следующие команды:
brew update brew install wget brew install sstp-client
Создаём файл скрипта, используя текстовый редактор nano.
nano sstp.sh
Вставляем в этот файл следующее содержимое и изменяем следующие поля:
'Work Login' - пишем свою доменную учетную запись, например: ra.sabirov@innopolis.ru
'Work Password' - пишем свой пароль от доменной учетной записи.
Work Login и Work Password вводим БЕЗ КОВЫЧЕК!
#!/bin/bash sudo /usr/local/sbin/sstpc --cert-warn --tls-ext --user 'Work Login without quotes' --password 'Work Password without quotes' vpn.university.innopolis.ru usepeerdns require-mschap-v2 noauth noipdefault noccp refuse-eap refuse-pap refuse-mschap defaultroute --log-stderr
Сохраняем файл и закрываем файл
Делаем файл [sstp.sh](http://sstp.sh) исполняемым, изменив его разрешение на 755
chmod 755 sstp.sh
Подключаемся к SSTP серверу, запустив скрипт
./sstp.sh
При запуске скрипта будет запрошен пароль локального администратора Macbook.
Для разрыва соединения в окне терминала просто прекращаем выполнения скрипта, нажав сочетание клавиш на клавиатуре Ctrl+C
Если просто закрыть окно терминала соединение останется подключенным.
Если у вас возникают какие либо ошибки при запуске, попробуйте для начала проверить а установился ли пакет sstp, выполните в терминале:
sudo find / -type f -name sstpc 2>/dev/null
или используйте команду brew list для вывода списка всех установленных пакетов Homebrew. Посмотрите, есть ли среди них sstp-client:
brew list
Таким образом вам необходимо попробовать сменить путь до sstp клиента, из команды выше
Вот тут:
Вместо /usr/local/sbin/sstpc свой путь.
#!/bin/bash sudo /usr/local/sbin/sstpc ...остальной код
Мы не несем ответственности за установку и использование сторонних клиентов, все это вы используете на ваш страх и риск!
Сторонние клиенты SSTP:
[iSSTP - SSTP Client for Mac OSX](https://github.com/axot/isstp)
[SSTP-CLIENT BREW for Mac OSX](https://formulae.brew.sh/formula/sstp-client)
![](https://help.university.innopolis.ru/images/image_1705413210211.png)
Университет Иннополис | Powered by [Wiki.js](https://wiki.js.org)