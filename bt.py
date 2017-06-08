import CHIP_IO.GPIO as gpio
import alsaaudio
import sys
import snowboydetect
from bluetooth import find_service, BluetoothSocket, RFCOMM

pinid = "CSID{0}"
pinmap = [1, 2, 3, 4, 5, 6, 7]
led_map_idle = [1, 0, 0, 0, 0, 0, 0, 0]
led_map_active = [0, 1, 0, 0, 0, 0, 0, 0]
led_map_detected = [0, 0, 0, 0, 1, 1, 1, 1]


def main():
    uuid = "abcd1234-ab12-ab12-ab12-abcdef123456"
    service_matches = find_service(uuid=uuid, address='C8:25:E1:C4:2E:CD')
    if len(service_matches) == 0:
        print("couldn't find the SampleServer service =(")
        sys.exit(0)
    first_match = service_matches[0]
    print first_match
    port = first_match["port"]
    name = first_match["name"]
    host = first_match["host"]

    sock = BluetoothSocket(RFCOMM)
    sock.connect((host, port))
    print
    gpio.cleanup()
    for x in range(0, 8):
        try:
            gpio.setup(pinid.format(x), gpio.OUT)
        except Exception as e:
            print(e)
    gpio.output(pinid.format(0), gpio.HIGH)
    detector = snowboydetect.SnowboyDetect(
        resource_filename="resources/common.res", model_str="resources/alexa.umdl")
    detector.SetAudioGain(3)

    inp = alsaaudio.PCM(alsaaudio.PCM_CAPTURE, alsaaudio.PCM_NORMAL, 'default')
    inp.setchannels(detector.NumChannels())
    inp.setrate(detector.SampleRate())
    inp.setformat(alsaaudio.PCM_FORMAT_S16_LE)
    inp.setperiodsize(2048)

    while True:
        l, data = inp.read()
        ans = detector.RunDetection(data)
        if ans == 1:
            sock.send("Alexa")
        for pin in range(0, 8):
            if ans < 0:
                gpio.output(pinid.format(pin), gpio.HIGH if led_map_idle[pin] else gpio.LOW)
            elif ans == 0:
                gpio.output(pinid.format(pin), gpio.HIGH if led_map_active[pin] else gpio.LOW)
            elif ans == 1:
                gpio.output(pinid.format(pin), gpio.HIGH if led_map_detected[pin] else gpio.LOW)
        print(ans)



if __name__ == '__main__':
    main()
