'use strict'
const assert = require('assert')
var net = require('net')
const COOLING=0, HEATING=1, COMBI=2, OFF=3
const SYSTEM_COOLING=0, SYSTEM_HEATING=1, SYSTEM_OFF=2, SYSTEM_FAN=3
var state = { 'temperature': 66
            , 'humidity': 50
            , 'setpoint': 70
            , 'setPointLow': 68
            , 'setPointHigh': 75
            , 'mode': HEATING
            , 'autoMode': HEATING
            , 'relays': SYSTEM_OFF
            , 'settings': { 'deadband': 4.0
                          , 'hysteresis': 1.0
                          , 'maxTemp': 85
                          , 'minTemp': 55
                          }
            }
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
    // Handle errors on sockets
    socket.on('error', function (e) {
      console.log(`got error on socket from client at address ${socket.localAddress}`)
      console.log('error = ' + e.message)
      if (e.message === 'This socket is closed') {
        socket.end()
      }
    })
    
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
      //system_update(obj, socket) Note: must broadcast secondary changes!
      system_update(obj, null)
    }

});

s.listen(8999);
console.log('System waiting at http://localhost:8999');


function system_update(changes, socket) {
  
  let nullObj = {}
  //changes = changes || nullObj
  if (Object.keys(changes).length === 0 && changes.constructor === Object)
    changes = nullObj
  
  //let mode = changes.mode || state.mode // fix!!! mode === 0 fails
  let mode = (changes.mode !== undefined)? changes.mode : state.mode
  let sp = (changes.setpoint !== undefined)? changes.setpoint : state.setpoint
  let temp = (changes.temperature !== undefined)? changes.temperature : state.temperature
  let relays = state.relays
  let auto = state.autoMode
  let deadband = state.settings.deadband
  let hysteresis = state.settings.hysteresis

  // Mode changes: update the setpoint and auto mode
  if (changes.mode !== undefined) {
    if (mode === HEATING) {
      sp = state.setPointLow
      auto = HEATING
      if (relays === SYSTEM_COOLING)
        relays = SYSTEM_OFF
    }
    if (mode === COOLING) {
      sp = state.setPointHigh
      auto = COOLING
      if (relays !== SYSTEM_HEATING)
        relays = SYSTEM_OFF
    }
    if (mode === OFF) {
      // FIXME:  In off mode, thermostat should not display setpoint.  (Current temp ok)
      auto = OFF
      relays = SYSTEM_OFF
    }
  }
  
  // Setpoint changes: FIXME - broadcast Hi, Lo setpoints?
  if (changes.setpoint !== undefined) {
    if (auto === HEATING) {
      state.setPointLow = sp
    }
    if (auto === COOLING) {
      state.setPointHigh = sp
    }
  }
  
  // In auto mode, do auto change-over
  if (mode === COMBI) {
    if (auto === COOLING)
      if (temp < (state.setPointLow + deadband/2 - hysteresis)) {
        auto = HEATING
        sp = state.setPointLow
      }
    if (auto === HEATING)
      if (temp > (state.setPointHigh - deadband/2 + hysteresis)) {
        auto = COOLING
        sp = state.setPointHigh
      }
  }

  // compute new relays based on setpoint or temperature change
  if (auto === COOLING) {
    if (temp <= (sp - hysteresis/2) && relays == SYSTEM_COOLING)
      relays = SYSTEM_OFF
    if (temp >= (sp + hysteresis/2) && relays == SYSTEM_OFF)
      relays = SYSTEM_COOLING
    if (relays === SYSTEM_HEATING) throw new Error("Bad hvac state!")
  }
  if (auto === HEATING) {
    if (temp >= (sp + hysteresis/2) && relays == SYSTEM_HEATING)
      relays = SYSTEM_OFF
    if (temp <= (sp - hysteresis/2) && relays == SYSTEM_OFF)
      relays = SYSTEM_HEATING
    if (relays === SYSTEM_COOLING) throw new Error("Bad hvac state!")
  }
  if (auto === OFF) relays = SYSTEM_OFF
  
  // update state and changes
  let next = { mode: mode, setpoint: sp, temperature: temp
             , humidity: changes.humidity || state.humidity
             , autoMode: auto, relays: relays}
  for (let key in next) {
    if (state[key] !== next[key]) {
      state[key] = next[key]
      changes[key] = next[key]
    }
  }

  //  broadcast changes to all clients
  if (changes !== nullObj) broadcast(changes, socket) // let other clients sync their states
  return
  
  function broadcast(obj, except) {
    //stringify obj and prefix with length and newline
    var message = JSON.stringify(obj)
    message = message.length + '\n' + message
    
    for (let i = 0; i < sockets.length; i++) {
        if (sockets[i] === except) {
          console.log(message.replace('\n', '')) // fixme: remove after debug
          continue //dont' send to self
        }
        console.log('broadcasting: ' + message.replace('\n', ''))
        sockets[i].write(message)
    }
  }

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
    let changes = {}
    let t = round2QuarterDegree(s.temperature())
    let h = s.humidity()
    s.trigger() // start next aquisition
    s.triggered = false
    
    if (state.temperature !== t) {
      //state.temperature = t
      changes.temperature = t
    }
    
    if (state.humidity !== h) {
      //state.humidity = h
      changes.humidity = h
    }
    
    system_update(changes, null)
    //broadcast({'temperature': state.temperature, 'humidity': state.humidity})
  }
  else s.trigger() // start aquisition

  function round2QuarterDegree(t) {
    // Depending on state.mode, round to nearest quarter degree
    if (state.mode === COOLING)
      return Math.ceil(t*4)/4
    else
      return Math.floor(t*4)/4
  }
  
}
