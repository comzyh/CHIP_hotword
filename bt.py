import subprocess
import signal
import sys

import CHIP_IO.GPIO as gpio
import alsaaudio
import snowboydetect
from btagent import start_agent

pinid = "CSID{0}"
pinmap = [1, 2, 3, 4, 5, 6, 7]
led_map_idle = [1, 0, 0, 0, 0, 0, 0, 0]
led_map_active = [0, 1, 0, 0, 0, 0, 0, 0]
led_map_detected = [0, 0, 0, 0, 1, 1, 1, 1]

# def set_bt():
#     name = '\xe8\xb6\x85\xe7\xba\xa7\xe6\x97\xa0\xe6\x95\x8c\xe5\xb0\x8f\xe4\xb8\x8d\xe7\x82\xb9\xe5\x94\xa4\xe9\x86\x92\xe5\x8a\xa9\xe6\x89\x8b'
#     eip = hex(len(name) + 1)[2:] + '09' + ''.join([hex(ord(c))[2:] for c in name])
#     # eip += "020a00" + "0910" + "02006b1d460217" + "05050300180118"
#     eip += "020a00" + "0910" + "02006b1d460217" + "090503001801180e110c11"
#     subprocess.call(['hciconfig', 'hci0', 'up'])
#     subprocess.call(['hciconfig', 'hci0', 'name', name])
#     subprocess.call(['hciconfig', 'hci0', 'inqdata', eip])


def main():
    subprocess.Popen('/usr/libexec/bluetooth/bluetoothd')
    gpio.cleanup()
    for x in range(0, 8):
        try:
            gpio.setup(pinid.format(x), gpio.OUT)
        except Exception as e:
            print(e)
    gpio.output(pinid.format(0), gpio.HIGH)
    detector = snowboydetect.SnowboyDetect(
        resource_filename="resources/common.res", model_str="resources/alexa.umdl,resources/snowboy.umdl")
    detector.SetAudioGain(3)

    inp = alsaaudio.PCM(alsaaudio.PCM_CAPTURE, alsaaudio.PCM_NORMAL, 'default')
    inp.setchannels(detector.NumChannels())
    inp.setrate(detector.SampleRate())
    inp.setformat(alsaaudio.PCM_FORMAT_S16_LE)
    inp.setperiodsize(2048)

    agent = start_agent()
    while True:
        l, data = inp.read()
        ans = detector.RunDetection(data)
        print(ans)
        if ans == 1:
            agent.send("Alexa")
        for pin in range(0, 8):
            if ans < 0:
                gpio.output(pinid.format(pin), gpio.HIGH if led_map_idle[pin] else gpio.LOW)
            elif ans == 0:
                gpio.output(pinid.format(pin), gpio.HIGH if led_map_active[pin] else gpio.LOW)
            elif ans >= 1:
                gpio.output(pinid.format(pin), gpio.HIGH if led_map_detected[pin] else gpio.LOW)
        if ans == 2:
            print('repair')
            agent.repair()


if __name__ == '__main__':
    def handler_stop_signals(signum, frame):
        gpio.cleanup()
        sys.exit(0)

    signal.signal(signal.SIGTERM, handler_stop_signals)
    main()
