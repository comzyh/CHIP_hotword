# CHIP_hotword
---

Hotword detector for C.H.I.P. Pro board

files:

- btagent.py: include all bluetooth control and error handling stuff
  - deal with bluetooth pairing
  - store/load paired device info
  - auto reconnect target phone
- bt.py: main: run snowboy hotword detect, and send message to phone
  - use for loop to read wave data from mic
  - deliver wave data to snowboy hotword detector
- main.py: deprecated, simple hotword detector with bluetooth support
- init.d/: start up script for hotword detector


## Base firmware
if you want the basic image for C.H.I.P board, refer to:

https://github.com/naturali/gadget-buildroot

this repository include:

- all packages that buildroot have
- python-gattlib: python library for BLE
- python-pybluez
- (working)libatlas binary: linear algebra library which snowboy depends on
