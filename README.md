# N-est-Thermostat
A home thermostat application constructed as client-server model and implemented on PiTFT touchscreen and Raspberry Pi.

This is WIP.  Running the application client and server runs a demo with a subset of features.

Client (thermostat.py) is implemented with Pygame/SDL.  It connects to the thermostat server (hvac-server.js) acquiring the thermostat
state, handles user inputs from the touch screen and displays a radial thermostat.  Other clients can connect to the same hvac and
clients can connect to different hvac servers within the home - ie upstairs and downstairs.  

The thermostat server (hvac-server.js) is implemented in NodeJs and uses Pigpio to control the hvac relays and a local
temperature sensor (DHT11 type).

MIT License, modified

Copyright (c) 2017 Guy McSwain

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, ~~and/or sell
copies~~ of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
