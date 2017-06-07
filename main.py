import CHIP_IO.GPIO as gpio
import alsaaudio
import audioop
import snowboydetect

pinid = "CSID{0}"
pinmap = [1, 2, 3, 4, 5, 6, 7]
led_map_idle = [1, 0, 0, 0, 0, 0, 0, 0]
led_map_active = [0, 1, 0, 0, 0, 0, 0, 0]
led_map_detected = [0, 0, 0, 0, 1, 1, 1, 1]


def main():
    gpio.cleanup()
    for x in range(0, 8):
        try:
            gpio.setup(pinid.format(x), gpio.OUT)
        except Exception as e:
            print(e)
    gpio.output(pinid.format(0), gpio.HIGH)
    detector = snowboydetect.SnowboyDetect(
        resource_filename="resources/common.res", model_str="resources/alexa.umdl")
    detector.SetAudioGain(1)

    inp = alsaaudio.PCM(alsaaudio.PCM_CAPTURE, alsaaudio.PCM_NORMAL, 'default')
    inp.setchannels(detector.NumChannels())
    inp.setrate(detector.SampleRate())
    inp.setformat(alsaaudio.PCM_FORMAT_S16_LE)
    inp.setperiodsize(2048)

    while True:
        l, data = inp.read()
        ans = detector.RunDetection(data)
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
