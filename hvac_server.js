'use strict'
const assert = require('assert')
var net = require('net')
const COOLING=0, HEATING=1, COMBI=2, OFF=3
const SYSTEM_COOLING=0, SYSTEM_HEATING=1, SYSTEM_OFF=2, SYSTEM_FAN=3
var state = {'temperature': 66, 'setpoint': 62, 'mode': HEATING, 'relays': SYSTEM_OFF }
//console.log("state =" + JSON.stringify(state))

//Share state as global variable - currently used by demosensor.
module.exports = {
  state,
  COOLING,
  HEATING,
  COMBI,
  OFF,
  SYSTEM_HEATING,
  SYSTEM_COOLING,
  SYSTEM_OFF,
  SYSTEM_FAN
}

// Support connections for multiple clients
var sockets = []; // pool of connected clients

// Create a TCP socket listener
var s = net.Server(function (socket) {

    // Add the new client socket connection to the array of sockets
    sockets.push(socket);
    
    // Greet new client with hvac state
    console.log('client connected')
    var str = JSON.stringify(state)
    socket.write(str.length + "\n" + str)
    
    var data = ''
    // Receiving data from client application
    socket.on('data', function (chunk) {
      console.log(`received:${chunk.toString().replace(/\n/g, '')} from ${socket.localAddress}`)
      data += chunk
      //console.log('data='+data)
      
      while (data.indexOf('\n') > 0) {
        let [header, ...rest] = data.split('\n')
        rest = rest.join('\n')
        let length = parseInt(header, 10) // FIXME use re and handle error case
        assert(length != NaN && length > 1, 'Failed to parse length!')
        if (length > rest.length) break // return
        process_the_message(rest.slice(0, length))
        data = rest.slice(length)
        //console.log('remaining data='+data)
      }

    });
    
    // Avoid dead sockets by responding to the 'end' event
    socket.on('end', function () {
        var i = sockets.indexOf(socket);
        sockets.splice(i, 1);
        console.log('client disconnected')
    });
    
    function process_the_message(message) {
      //convert json object
      var obj
      try {
        obj = JSON.parse(message)
        //console.log('obj recved=' + JSON.stringify(obj))
      }
      catch (e) {
        console.log(e)
        throw new Error("message="+message)
      }
      
      //change state and update system
      for (let key in obj) {
        if (obj.hasOwnProperty(key)) {
          state[key] = obj[key]
          //broadcast({key: state[key]}) //ahhhh, this won't work
          //console.log('key =' + key + ', new value =' + state[key])
        }
      }
      broadcast(obj, socket) // let other clients sync their states
      system_update()
    }

});

s.listen(8999);
console.log('System waiting at http://localhost:8999');

function broadcast(obj, except) {
  //stringify obj and prefix with length and newline
  var message = JSON.stringify(obj)
  message = message.length + '\n' + message
  console.log('broadcasting: ' + message.replace('\n', ''))
  for (let i = 0; i < sockets.length; i++) {
      if (sockets[i] == except) continue //dont' send to self
      sockets[i].write(message)
  }
}

function system_update() {
  //global system, mode, current, target
  let relays = state.relays
  if (state.mode == COOLING) {
    if (state.temperature < (state.setpoint - 0.5) && relays == SYSTEM_COOLING)
      relays = SYSTEM_OFF
    if (state.temperature > (state.setpoint + 0.5) && relays == SYSTEM_OFF)
      relays = SYSTEM_COOLING
  }
  if (state.mode == HEATING) {
    if (state.temperature > (state.setpoint + 0.5) && relays == SYSTEM_HEATING)
      relays = SYSTEM_OFF
    if (state.temperature < (state.setpoint - 0.5) && relays == SYSTEM_OFF)
      relays = SYSTEM_HEATING
  }
  if (state.relays != relays) {
    state.relays = relays
    broadcast({'relays': state.relays}) //update all connected clients
  }
  //if (s.type() == 'dummy') s.systemState(state.relays)
}

/*
# Set up sensor if on RPI, else use dummy if on pc
s = 0 # sensor instance, eventually
import pigpio
import Dummy_sensor
import DHT11
import socket
try:
  sock = socket.create_connection(('10.0.0.105', 8888), timeout=3)
  print 'got sock connection!'
  pi = pigpio.pi("10.0.0.105")  #surveyor pi
  if not pi.connected: #use dummy sensor
    print 'not connected, wtf?  exiting ...'
    sys.exit()
  print 'connected to surveyor!' 
  s = DHT11.sensor(pi, 22)
except:
  print 'no connection to surveyor sensor, using dummy'
  s = Dummy_sensor.Sensor(68, 51)

READ_SENSOR_INTERVAL = 3 # Intervals <=2 seconds will eventually hang the DHT22.
*/

// Setup demo sensor for now
var Sensor = require('./demosensor')
var s = new Sensor(68, 51)
const READ_SENSOR_INTERVAL = 3
setInterval(readSensor, READ_SENSOR_INTERVAL*33)

function readSensor() {
  if (s.triggered) {
    state.temperature = s.temperature()
    state.humidity = s.humidity()
    s.trigger() // start next aquisition
    s.triggered = false
    broadcast({'temperature': state.temperature, 'humidity': state.humidity})
    system_update()
  }
  else s.trigger() // start aquisition
}