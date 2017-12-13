from jsonsocket.jsonsocket import Client

'''
This module returns an hvac_client object which communicates with an hvac_server.

IMPORTANT: jsonsocket client is modified to be non-blocking until partial message
is received then blocking until complete message is received.  If socket is not
readable, client.recv returns an empty json object.
'''
class HVAC_Client(object):
  keys = ('setpoint', 'temperature', 'mode', 'relays')
  
  #opens socket to hvac server and initialize state
  def __init__(self, host, port):
    self.client = Client()
    self.client.connect(host, port)
    self._state = {}
    
    #on connection, server sends hvac state object.  Block until recieved.
    while not self._state:
      self._state = self.client.recv()
    
    #sanity check the received object is a 'thermostat'
    for key in HVAC_Client.keys:
      if not key in self._state: print 'Error: invalid state recieved!'

  #properties to get, set self._state attributes
  #setters synchronize change with server
  
  @property
  def setpoint(self): return self._state['setpoint']
  @setpoint.setter
  def setpoint(self, value):
    self._state['setpoint'] = value
    self.client.send({'setpoint': value}) #update server state
  
  @property
  def temperature(self): return self._state['temperature']
  @property
  def relative_humidity(self): return self._state.relative_humidity
  
  @property
  def mode(self): return self._state['mode']
  @mode.setter
  def mode(self, value):
    self._state['mode'] = value
    self.client.send({'mode': value}) #update server state
  
  @property
  def relays(self): return self._state['relays']
  '''
    if _state.heater_relay and not _state.chiller_relay: return 'SYSTEM_HEATING'
    elif _state.chiller_relay and not _state.heater_relay: return 'SYSTEM_COOLING'
    # what about timer delay?
    else return 'unknown'
  '''
  
  @property
  def fan_state(self): return _state.fan_relay
  
  #sync method updates self._state to all messages recieved from server
  def sync(self):
    msg = self.client.recv()
    while msg != None:
      for k, v in msg.iteritems(): #message may contain more than one attribute
        self._state[k] = v
      msg = self.client.recv()

  def close(self):
    self.client.close()