# PowerMeter Code for Reading ORNO WE-517 Power Meter Registers
## Hardware connectivity
To connect the Power Meter to a Linux box, one needs to convert the RS-485 Bus Protocol to an USB Protocol using an [RS-485 to USB Converter](https://www.amazon.de/gp/product/B083169369/ref=ppx_yo_dt_b_asin_title_o01_s00?ie=UTF8&psc=1).
## Hardware interface
To generate a unique device id for the USB port of the RS-485 to USB converter we have to define it's vendor and product id in the definition files for the udev daemon:

> cd /etc/udev/rules.d
>
> sudo nano 50-usb.rules

enter the following line into the editor

> SUBSYSTEM=="tty", ATTRS{idVendor}=="0403", ATTRS{idProduct}=="6001", SYMLINK+="ORNO", MODE="0666"

where the vendor id and the product id are the ones of the above mentioned converter. If you use a different product you'll need to inspect the output of

> dmesg

to identify which USB port the converter has been connected to and then

> lsusb

to get the vendor and product id of the respective device at this port.
After reboot the new symlink

> /dev/ORNO

has been created which is the default port the script is accessing.

Alternatively to a reboot one can issue

> sudo udevadm control --reload-rules && sudo udevadm trigger

According to [this forum](https://forum.ubuntuusers.de/topic/problem-mit-usb-seriell-wandler-geloest/) if the rule does not work one needs to uninstall the Braille tty driver with

> sudo apt remove brltty

then the named port ORNO should be linked correctly to a ttyUSBx port.

## Run script as service

Copy provided systemd service file 'powermeter.service.template' to systemd service file folder

> sudo cp powermeter.service.template /lib/systemd/system/powermeter.service

Enable and start service with

> sudo systemctl daemon-reload
> sudo systemctl enable powermeter.service
> sudo systemctl start powermeter.service

Check successful activation with

> sudo systemctl status powermeter.service

