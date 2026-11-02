---
type: page
title: "Connecting a VPN on OS Ubuntu"
description: "sudo apt-get update sudo apt-get install network-manager-l2tp sudo apt-get install network-manager-l2tp-gnome"
resource: "https://help.university.innopolis.ru/en/VPN/VPN_Ubuntu"
audience: ["staff"]
source_kind: website
language: en
section: "site/help"
sources:
  - resource: "https://help.university.innopolis.ru/en/VPN/VPN_Ubuntu"
    id: "d5e8bca39582"
    title: "Connecting a VPN on OS Ubuntu"
    last_modified: "2026-10-31T10:15:54+00:00"
generated:
  by: "catix-wiki/0.1 sites"
  at: "2026-10-31T10:15:54+00:00"
status: draft
---

# Connecting a VPN on OS Ubuntu

[VPN](/raw/sites/help/en-vpn.md)

VPN_Errors

[Connecting a VPN on OS MacOS](/raw/sites/help/en-vpn-vpn-macos.md)

Connecting a VPN on OS Ubuntu

[Connecting a VPN on OS Windows 10](/raw/sites/help/en-vpn-vpn-windows.md)

[Connecting a VPN on OS Windows 7](/raw/sites/help/en-vpn-vpn-windows7.md)

[OpenVPN connection](/raw/sites/help/en-vpn-openvpn.md)

[VPN](/raw/sites/help/en-vpn.md)

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

_The menu, footer and other blocks that the pages of the site repeat are kept in one place: [/raw/sites/help/_shared-en.md](/raw/sites/help/_shared-en.md)._

# Citations

1. [Connecting a VPN on OS Ubuntu](https://help.university.innopolis.ru/en/VPN/VPN_Ubuntu), read 2026-10-31
