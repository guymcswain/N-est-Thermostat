'use strict'
var hvac = require('./hvac_server.js')

function Sensor(i_temperature, i_humidity) {
  
  const Kloss = 0.00008
  const Kgain = 0.00016
  const Tcoldair = 45
  const Thotair = 100
  
  this.triggered = false
  this.temp = i_temperature
  this.rhum = i_humidity
  this.bump = 0.25
  this.rhumbump = 0.01
  
  /* init system simulation */
  // use the global var 'state'
  
  this.trigger = function() {
    if (hvac.state.mode == hvac.HEATING)   this.Toutside = 95
    else if (hvac.state.mode == hvac.COOLING) this.Toutside = 50
    else this.Toutside = Math.random() * (50 - 95) + 50
    this.rhum += this.rhumbump
    if (this.rhum >=100) this.rhumbump = -this.rhumbump
    if (this.rhum <=0) this.rhumbump = -this.rhumbump
    
    this.Tloss = Kloss * (this.Toutside - this.temp)
    if (hvac.state.relays == hvac.SYSTEM_COOLING)
      this.Tgain = Kgain * (Tcoldair - this.temp)
    if (hvac.state.relays == hvac.SYSTEM_OFF)
      this.Tgain = 0
    if (hvac.state.relays == hvac.SYSTEM_HEATING)
      this.Tgain = Kgain * (Thotair - this.temp)
    
    this.temp += this.Tgain - this.Tloss
    this.triggered = true
  }
  this.temperature = function() {
    //return Math.round(this.temp*4)/4
    return this.temp
  }
  this.humidity = function() {
    return Math.round(this.rhum)
  }
  this.cancel = function() {
    return False
  }
  this.type = function() {
    return 'demo'
  }
}
module.exports = Sensor
  





