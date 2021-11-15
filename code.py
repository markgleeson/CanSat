"""CircuitPython Essentials Storage logging example"""
import time
import board
import digitalio
import microcontroller
import neopixel

import array
import math
import audiobusio
import adafruit_apds9960.apds9960
import adafruit_bmp280
import adafruit_lis3mdl
import adafruit_lsm6ds.lsm6ds33
import adafruit_sht31d

from adafruit_ble import BLERadio
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
from adafruit_ble.services.nordic import UARTService

# We will use the onboard LED to indicate what our code is doing
# We create a reference to the NeoPixel Module called lednp
# From here on, we can access functions associated with the neopixel with lednp

lednp = neopixel.NeoPixel(board.NEOPIXEL, 1)

# We have set the brightness of the NeoPixel from 0.0 (Off) to 1.0 (Maximum Brightness)
lednp.brightness = 0.3

# Many of the sensors that are on the Feather Sense communicate using I2C
# We will setup the I2C communication with default parameters.
i2c = board.I2C()

# Each sensor is referenced, and will be accessed with I2C
# Although not all sensors are included in the output, they are initialised
apds9960 = adafruit_apds9960.apds9960.APDS9960(i2c)
bmp280 = adafruit_bmp280.Adafruit_BMP280_I2C(i2c)
lis3mdl = adafruit_lis3mdl.LIS3MDL(i2c)
lsm6ds33 = adafruit_lsm6ds.lsm6ds33.LSM6DS33(i2c)
sht31d = adafruit_sht31d.SHT31D(i2c)
microphone = audiobusio.PDMIn(board.MICROPHONE_CLOCK, board.MICROPHONE_DATA,
                              sample_rate=16000, bit_depth=16)

# This is a function that will be used to normalise the output of the microphone sensor.
def normalized_rms(values):
    minbuf = int(sum(values) / len(values))
    return int(math.sqrt(sum(float(sample - minbuf) *
                             (sample - minbuf) for sample in values) / len(values)))

# One of the sensors (APDS9960) can detect proximity and color
apds9960.enable_proximity = True
apds9960.enable_color = True

# We will use Bluetooth to communicate with an iPad
# setup Bluetooth, we will use UART (a serial connection) to send data
# we will 'advertise' that UART is available
ble = BLERadio()
uart_service = UARTService()
advertisement = ProvideServicesAdvertisement(uart_service)

# You will need to change the pressure to match your location
# Set this to sea level pressure in hectoPascals at your location for accurate altitude reading.
bmp280.sea_level_pressure = 1013.25

# the sampleDelay controls how quickly a new set of data is collected
sampleDelay = 0.5

# Depending on what mode you start the microcontroller in, it will either:
# Write to onboard storage
# Transmit data over bluetooth to an iPad

#Mode: Write to onboard storage
#try: except attempts to write to the onboard storage of the microcontroller.
#If the microcontroller can't write, it moves to line 121
try:
    #Open a file to write. There are two parameters:
    #The first, "/data.csv" will save the file as a comma-seperate value file
    #The second, 'w' replaces the file everytime the feather is booted
    with open("/data.csv", "w") as fp:
        while True:

            # The LED allows you to change the color using (R, G, B) with values of 0 to 255
            # The code below sets the first LED (LED Zero) to GREEN.
            lednp[0] = (0,255,0)

            # Set the variable 'temp' to the temperature collected with the bmp280 sensor
            # As with the variable 'pres' as presssure
            # And the variaable 'alt' as altitude
            temp = bmp280.temperature
            pres = bmp280.pressure
            alt = bmp280.altitude

            # Set the variable 'humid' to the humidity collected with the sht31d sensor
            humid = sht31d.relative_humidity

            # The following code outputs comma-seperated values on one line, for example
            # $,25.43,998.42,124.39,50.4,0.29,-0.12,10
            # $,temp,pres,alt,humid,x,y,z
            # temp = temperature in degrees celsius
            # pres = pressure in hecto pascals
            # alt = altitude in meters, approximate
            # humid = humidity as percentage 0-100%
            # *lsm6ds33.acceleration returns a pointer to the first item in a list with size three
            # *lsm6ds33.acceleration has a list that looks like (0.2, 0.2, 9.8) with (x, y, z) acceleration
            # x = acceleration in x in m/s^2
            # y = acceleration in y in m/s^2
            # z = acceleration in z in m/s^2

            fp.write('$,{0:.2f},'.format(temp))
            fp.write('{0:.2f},'.format(pres))
            fp.write('{0:.2f},'.format(alt))
            fp.write('{0:.2f},'.format(humid))
            fp.write('{:.2f},{:.2f},{:.2f}'.format(*lsm6ds33.acceleration))
            fp.write('\n')
            fp.flush()

            # Set the LED to off
            lednp[0] = (0,0,0)

            # Wait for the sampleDelay before continuining
            time.sleep(sampleDelay)

#Mode: Transmit data over bluetooth to an iPad
# As the microcontroller couldn't write to its onboard memory
# it will instead transmit over bluetooth
except OSError as e:  # Typically when the filesystem isn't writeable...
    delay = 0.5  # ...blink the LED every half second.
    if e.args[0] == 28:  # If the file system is full...
        delay = 0.25  # ...blink the LED faster!

    # until the microcontroller is reset, it will repeat while True
    while True:
        # Advertise that bluetooth is available
        ble.start_advertising(advertisement)

        # wait until a device connects to the microcontroller
        while not ble.connected:
            pass

        # stop advertising, as a device has connected to Bluetooth
        ble.stop_advertising()

        # while connected, the microcontroller will send data over bluetooth
        # the below code is very similar to the earlier block of code
        while ble.connected:

            #set the LED to Blue
            lednp[0] = (0,0,255)
            temp = bmp280.temperature
            pres = bmp280.pressure
            alt = bmp280.altitude
            humid = sht31d.relative_humidity

            # Write data over Bluetooth as a string
            # $ is a sentinal, the start of a new line containing sensor values
            # {0:.2f} says to write the first variable in .format as a float to two decimal places
            # {1:.2f} says to write the second variable in .format as a float to two decimal places
            # {2:.2f} etc.
            # .format takes the parameters, variables
            # *lsm6ds33.acceleration returns a pointer to the first item in a list with size three
            # *lsm6ds33.acceleration has a list that looks like (0.2, 0.2, 9.8) with (x, y, z) acceleration
            uart_service.write("${0:.2f},{1:.2f},{2:.2f},{3:.2f},{4:.2f},{5:.2f},{6:.2f}\n".format(temp,pres,alt,humid,*lsm6ds33.acceleration))

            # wait for half of the delay time, turn the LED off (set all values to zero), and wait for half of the delay time
            time.sleep(delay/2)
            lednp[0] = (0,0,0)
            time.sleep(delay/2)

            #repeat
