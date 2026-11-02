![](https://help.university.innopolis.ru/%D0%B7%D0%BD%D0%B0%D0%BA_%D0%B7%D0%B5%D0%BB%D0%B5%D0%BD%D1%8B%D0%B9.png)
ITHelp Wiki
/ sidebar.root
VPN
[VPN](https://help.university.innopolis.ru/ru/VPN)
Текущий каталог
VPN_Errors
[Подключение OpenVPN в Казанском офисе](https://help.university.innopolis.ru/ru/VPN/OpenVPN)
[Подключение VPN к MacOS](https://help.university.innopolis.ru/ru/VPN/VPN_MACOS)
Подключение VPN к Manjaro
[Подключение VPN к Ubuntu GUI](https://help.university.innopolis.ru/ru/VPN/VPN_Ubuntu)
[Подключение VPN к Windows10](https://help.university.innopolis.ru/ru/VPN/VPN_Windows)
[Подключение VPN к Windows7](https://help.university.innopolis.ru/ru/VPN/VPN_Windows7)
- /
[VPN](https://help.university.innopolis.ru/ru/VPN)
- /
VPN_Manjaro
Подключение VPN к Manjaro
Вам необходимо доустановить, либо переустановить пакеты
sudo pacman -S xl2tpd sudo yay -S strongswan networkmanager-l2tp sudo yay -S xl2tpd strongswan networkmanager-l2tp sudo systemctl restart NetworkManager
Далее необходимо настроить VPN по аналогии с пунктами из раздела [инструкции Ubuntu](https://help.university.innopolis.ru/ru/VPN/VPN_Ubuntu)
![](https://help.university.innopolis.ru/images/image_1697202905832.png)
Университет Иннополис | Powered by [Wiki.js](https://wiki.js.org)