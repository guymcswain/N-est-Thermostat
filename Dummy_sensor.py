COOLING, HEATING, COMBI, OFF = (0, 1, 2, 3)
SYSTEM_COOLING, SYSTEM_HEATING, SYSTEM_OFF, SYSTEM_FAN = (0, 1, 2, 3)
import random

class Sensor:
  Kloss = 0.00008
  Kgain = 0.00016
  Tcoldair = 45
  Thotair = 100
  
  def __init__(self, i_temperature=None, i_humidity=None):
    self.temp = i_temperature
    self.rhum = i_humidity
    self.bump = 0.25
    self.rhumbump = 0.01
    # init system simulation
    self.systemMode(OFF)
    self.systemState(SYSTEM_OFF)
  
  def trigger(self):
    '''self.temp += self.bump
    if self.temp >= 88: self.bump = -0.25
    if self.temp <= 51: self.bump = 0.5'''
    self.rhum += self.rhumbump
    if self.rhum >=100: self.rhumbump = -self.rhumbump
    if self.rhum <=0: self.rhumbump = -self.rhumbump
    
    Tloss = Sensor.Kloss * (self.Toutside - self.temp)
    if self.state == SYSTEM_COOLING:
      Tgain = Sensor.Kgain * (Sensor.Tcoldair - self.temp)
    if self.state == SYSTEM_OFF:
      Tgain = 0
    if self.state == SYSTEM_HEATING:
      Tgain = Sensor.Kgain * (Sensor.Thotair - self.temp)
    
    self.temp += Tgain - Tloss
    
  def temperature(self):
    return round(self.temp*4)/4
  
  def humidity(self):
    return int(self.rhum)
  
  def cancel(self):
    return False
  
  def type(self):
    return 'dummy'
  
  def systemMode(self, mode):
    if mode == HEATING:   self.Toutside = 95
    elif mode == COOLING: self.Toutside = 50
    else:                 self.Toutside = random.randint(50, 95)
  
  def systemState(self, state):
    self.state = state
  





