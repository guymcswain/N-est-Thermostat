class Sensor:
  def __init__(self, i_temperature=None, i_humidity=None):
    self.temp = i_temperature
    self.rhum = i_humidity
    self.bump = 0.25
    self.rhumbump = 1
  def trigger(self):
    self.temp += self.bump
    if self.temp >= 88: self.bump = -0.25
    if self.temp <= 51: self.bump = 0.5
    self.rhum += self.rhumbump
    if self.rhum >=100: self.rhumbump = -1
    if self.rhum <=0: self.rhumbump = 2
    return False #does nothing here
  def temperature(self):
    return self.temp
  def humidity(self):
    return self.rhum
  def cancel(self):
    return False
