![](https://help.university.innopolis.ru/%D0%B7%D0%BD%D0%B0%D0%BA_%D0%B7%D0%B5%D0%BB%D0%B5%D0%BD%D1%8B%D0%B9.png)
ITHelp Wiki
/ sidebar.root
VPN
[VPN](https://help.university.innopolis.ru/en/VPN)
Current Directory
VPN_Errors
[Connecting a VPN on OS MacOS](https://help.university.innopolis.ru/en/VPN/VPN_MACOS)
Connecting a VPN on OS Ubuntu
[Connecting a VPN on OS Windows 10](https://help.university.innopolis.ru/en/VPN/VPN_Windows)
[Connecting a VPN on OS Windows 7](https://help.university.innopolis.ru/en/VPN/VPN_Windows7)
[OpenVPN connection](https://help.university.innopolis.ru/en/VPN/OpenVPN)
- /
[VPN](https://help.university.innopolis.ru/en/VPN)
- /
VPN_Ubuntu
Connecting a VPN on OS Ubuntu
В терминале выполняем последовательно следующие команды:
sudo apt-get update sudo apt-get install network-manager-l2tp sudo apt-get install network-manager-l2tp-gnome
В правом верхнем углу открываем выпадающее меню, в открывшемся окне выбираем Settings:
![](https://help.university.innopolis.ru/images/image_1697202482874.png)
Далее нажимаем на кнопку + чтобы добавить новое VPN подключение:
![](https://help.university.innopolis.ru/images/image_1697202505572.png)
В открывшемся окне выбираем L2TP
![](https://help.university.innopolis.ru/images/image_1697202531222.png)
Заполняем поля согласно скриншоту, пишем в полях:
Name (имя подключения) - University VPN,
Gateway (Шлюз, Сервер VPN) - vpn.university.innopolis.ru
User name (учетная запись) - ДоменнаяУчетнаяЗапись@innopolis.ru
Password (пароль) –Пароль от доменной учетной записи
(что бы можно было запомнить пароль необходимо в поле Password нажать на иконку вопросительного знака с права)
и выбрать store the password only for this user / храните пароль только для этого пользователя)
![](https://help.university.innopolis.ru/images/image_1697202630606.png)
Далее наживаем кнопку IPsec Settings;
В открывшемся окне заполняем поле Pre-shared key:
q7J>k2%[Lx
и нажимаем ОК, Apply (Применить);
![](https://help.university.innopolis.ru/images/image_1697202668892.png)
Далее в правом верхнем выпадающем меню в разделе VPN нажимаем Connect (Подключить);
![](https://help.university.innopolis.ru/images/image_1697202689727.png)
Если все настройки были введены верно, то иконка подключения сменится с [...] на VPN;
![](https://help.university.innopolis.ru/images/image_1697202717578.png)
Университет Иннополис | Powered by [Wiki.js](https://wiki.js.org)