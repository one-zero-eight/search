---
type: page
title: "Подключение VPN к Ubuntu GUI"
description: "sudo apt-get update sudo apt-get install network-manager-l2tp sudo apt-get install network-manager-l2tp-gnome"
resource: "https://help.university.innopolis.ru/ru/VPN/VPN_Ubuntu"
audience: ["staff"]
source_kind: website
language: ru
section: "site/help"
sources:
  - resource: "https://help.university.innopolis.ru/ru/VPN/VPN_Ubuntu"
    id: "fa76c7e40178"
    title: "Подключение VPN к Ubuntu GUI"
    last_modified: "2026-10-31T10:15:47+00:00"
generated:
  by: "catix-wiki/0.1 sites"
  at: "2026-10-31T10:15:47+00:00"
status: draft
---

# Подключение VPN к Ubuntu GUI

[VPN](/raw/sites/help/ru-vpn.md)

VPN_Errors

[Подключение OpenVPN в Казанском офисе](/raw/sites/help/ru-vpn-openvpn.md)

[Подключение VPN к MacOS](/raw/sites/help/ru-vpn-vpn-macos.md)

[Подключение VPN к Manjaro](/raw/sites/help/ru-vpn-vpn-manjaro.md)

Подключение VPN к Ubuntu GUI

[Подключение VPN к Windows10](/raw/sites/help/ru-vpn-vpn-windows.md)

[Подключение VPN к Windows7](/raw/sites/help/ru-vpn-vpn-windows7.md)

[VPN](/raw/sites/help/ru-vpn.md)

VPN_Ubuntu

Подключение VPN к Ubuntu GUI

- Для подключения через L2TP

- Для подключения через SSTP

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

Gateway (Шлюз, Сервер VPN) - [vpn.university.innopolis.ru](http://vpn.university.innopolis.ru)

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

Необходимо установить пакет sstp для network manager

В терминале вводим следующее:

sudo apt-get update sudo apt-get install sstp-client network-manager-sstp network-manager-sstp-gnome -y

В правом верхнем углу открываем выпадающее меню, в открывшемся окне выбираем Settings:

![](https://help.university.innopolis.ru/images/image_1697202482874.png)

Далее нажимаем на кнопку + чтобы добавить новое VPN подключение:

![](https://help.university.innopolis.ru/images/image_1697202505572.png)

В открывшемся окне выбираем SSTP

![image_1705471498912.png](https://help.university.innopolis.ru/images/image_1705471498912.png)

Заполняем поля согласно скриншоту, пишем в полях:

Name (имя подключения) - University VPN или SSTP

Gateway (Шлюз, Сервер VPN) - [vpn.university.innopolis.ru](http://vpn.university.innopolis.ru)

Type (тип) - Password

User name (ваша рабочая учетная запись) - user.login@innopolis.ru

Password (пароль) –Пароль от доменной учетной записи

![image_1705471691238.png](https://help.university.innopolis.ru/images/image_1705471691238.png)

Далее в этом же окне нажимаем на кнопку Advanced:

- Убираем галку с метода аутентификации MSCHAP. (Оставляем только MSCHAPv2.)

- Отключаем шифрование MPPE. Нажимаем кнопки ОК и Сохранить

![image_1705471738534.png](https://help.university.innopolis.ru/images/image_1705471738534.png)

Сохраняем настройки и перезагружаем устройство.

Далее в правом верхнем выпадающем меню в разделе VPN нажимаем Connect (Подключить);

![](https://help.university.innopolis.ru/images/image_1697202689727.png)

Если все настройки были введены верно, то иконка подключения сменится с [...] на VPN;

![](https://help.university.innopolis.ru/images/image_1697202717578.png)

_Меню, подвал и другие блоки, которые повторяются на страницах сайта, собраны в одном месте: [/raw/sites/help/_shared.md](/raw/sites/help/_shared.md)._

# Citations

1. [Подключение VPN к Ubuntu GUI](https://help.university.innopolis.ru/ru/VPN/VPN_Ubuntu), read 2026-10-31
