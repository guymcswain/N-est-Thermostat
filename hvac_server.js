'use strict'
var net = require('net')
const COOLING=0, HEATING=1, COMBI=2, OFF=3
const SYSTEM_COOLING=0, SYSTEM_HEATING=1, SYSTEM_OFF=2, SYSTEM_FAN=3
var state = {'temperature': 66, 'setpoint': 62, 'mode': HEATING, 'relays': SYSTEM_OFF }
console.log("state =" + JSON.stringify(state))

// Supports multiple client chat application

// Keep a pool of sockets ready for everyone
// Avoid dead sockets by responding to the 'end' event
var sockets = [];

// Create a TCP socket listener
var s = net.Server(function (socket) {

    // Add the new client socket connection to the array of
    // sockets
    sockets.push(socket);
    
    // Greet new client with hvac state
    console.log('client connected')
    var str = JSON.stringify(state)
    socket.write(str.length + "\n" + str)
    socket.msg = ''
    socket.header = ''
    
    // Receiving data from client application
    socket.on('data', function (chunk) {
      console.log('client sent:' + chunk.toString())
      this.msg += chunk
      var length
      
      //wait for header
      if (this.header == '') {
        if (this.msg.indexOf('n') >= 0) {
          [this.header, this.msg] = this.msg.split('\n')
          console.log('this.header='+this.header)
          console.log('this.msg='+this.msg)
          length = parseInt(this.header, 10)
          if (this.msg.length >= length) {
            let msg = this.msg.substr(0, length)
            this.msg = this.msg.slice(length)
            console.log('msg='+msg)
            console.log('this.msg='+this.msg)
            process_the_message(msg)
            this.header = '' // reset for next message
            return
          }
          else return // wait for the message
        }
        else return // wait for the header
      }
      
      // else wait for the message
      console.log('this.msg='+this.msg)
      length = parseInt(this.header, 10)
      if (this.msg.length >= length) {
        let msg = this.msg.substr(0, length-1)
        this.msg = this.msg.slice(length)
        process_the_message(msg)
        this.header = '' // reset for next message
        return
      }
      
      function process_the_message(message) {
        //convert json object
        var obj
        try {
          obj = JSON.parse(message)
          console.log('obj recved=' + JSON.stringify(obj))
        }
        catch (e) {
          console.log(e)
          throw new Error("could not convert to json object")
        }
        
        //change state and update system
        for (let key in obj) {
          if (obj.hasOwnProperty(key)) {
            state[key] = obj[key]
            //broadcast({key: state[key]}) //ahhhh, this won't work
            console.log('key =' + key + ', new value =' + state[key])
          }
        }
        broadcast(obj) // let all clients sync their states
        console.log('about to update state')
        system_update()
      }
      
    });
    
    // The 'end' event means tcp client has disconnected.
    socket.on('end', function () {
        var i = sockets.indexOf(socket);
        sockets.splice(i, 1);
        console.log('client disconnected')
    });


});

s.listen(8999);
console.log('System waiting at http://localhost:8999');

function broadcast(obj) {
  //stringify obj before sending out to all clients
  var objStr = JSON.stringify(obj)
  
  // Broadcast state change to all clients
  for (var i = 0; i < sockets.length; i++) {
      // Don't send the data back to the original sender
      //if (sockets[i] == socket) // don't send the message to yourself
      //    continue;
      sockets[i].write(objStr.length + "\n" + objStr);
      console.log('sent' + objStr.length + "\n" + objStr)
  }
}

function system_update() {
  //global system, mode, current, target
  if (state.mode == COOLING) {
    if (state.temperature < (state.setpoint - 0.5) && state.relays == SYSTEM_COOLING)
      state.relays = SYSTEM_OFF
    if (state.temperature > (state.setpoint + 0.5) && state.relays == SYSTEM_OFF)
      state.relays = SYSTEM_COOLING
  }
  if (state.mode == HEATING) {
    if (state.temperature > (state.setpoint + 0.5) && state.relays == SYSTEM_HEATING)
      state.relays = SYSTEM_OFF
    if (state.temperature < (state.setpoint - 0.5) && state.relays == SYSTEM_OFF)
      state.relays = SYSTEM_HEATING
  }
  broadcast({'relays': state.relays}) //update all connected clients
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