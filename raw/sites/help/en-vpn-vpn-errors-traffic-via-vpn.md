![](https://help.university.innopolis.ru/%D0%B7%D0%BD%D0%B0%D0%BA_%D0%B7%D0%B5%D0%BB%D0%B5%D0%BD%D1%8B%D0%B9.png)
ITHelp Wiki
/ sidebar.root
VPN
VPN_Errors
Current Directory
[If there are problems with the VPN connection](https://help.university.innopolis.ru/en/VPN/VPN_Errors/Problems_with_VPN_connection)
When connecting to the VPN server, nothing is pingable.
- /
[VPN](https://help.university.innopolis.ru/en/VPN)
- /
[VPN_Errors](https://help.university.innopolis.ru/en/VPN/VPN_Errors)
- /
Traffic_via_VPN
When connecting to the VPN server, nothing is pingable.
The VPN connects, but computers, servers, databases, etc. do not ping.
## ¶ Send all traffic through VPN
If, when connecting to the VPN server, the client cannot see the computers in the local network behind it, including the router itself, and pings beyond the virtual network are not successful.
If the connection settings on the client specify to 'Send all traffic through the VPN,' the local network behind the router is visible. However, in this case, all traffic, including torrents and other unwanted traffic, is routed through the VPN.
## ¶ Linux:
![](https://help.university.innopolis.ru/images/image_1701070651241.png)
## ¶ Windows 10:
Windows 10 should, by default, 'wrap up' all traffic in the VPN channel when creating a connection. However, sometimes the checkbox is not active.
You can check this by opening the properties of the IPv4 protocol (TCP/IPv4) and in the additional TCP/IP settings, activate the option 'Use default gateway on remote network.'
![](https://help.university.innopolis.ru/images/image_1701070665209.png)
## ¶ MacOS:
![](https://help.university.innopolis.ru/images/image_1701411593146.png)
## ¶ Not sending all traffic through the VPN:
Typically, after connecting via VPN, all traffic is redirected through this connection.
If there were data downloads, client-server interactions, or access authorizations on the computer, they stop. Torrents and browsers also start working only through the VPN. To prevent this and use the VPN connection only for access to the corporate network:
In the VPN settings, uncheck the option: 'Use default gateway on remote network.'"
Университет Иннополис | Powered by [Wiki.js](https://wiki.js.org)