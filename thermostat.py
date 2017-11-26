import pygame
import os, sys
from time import sleep
import math

pygame.init()
if pygame.mixer.get_init() != None:
  print 'sound detected, quiting mixer'
  pygame.mixer.quit()
else: print 'no sound detected'
screen=0 # global var for display
# Get information about display
print 'display driver =', pygame.display.get_driver()
info = pygame.display.Info()
print info
display_modes = pygame.display.list_modes()
print display_modes
screen_resolution = 0
# set up the screen and device drivers per type of machine we are running on
machine_type = os.uname()[4]
desktop = 'x86_64'
if machine_type != desktop: # assume RPI ZeroW with patched kernel for ft6236
  os.putenv('SDL_FBDEV', '/dev/fb1')
  os.putenv('SDL_MOUSEDRV', 'TSLIB')
  os.putenv('SDL_MOUSEDEV', '/dev/input/event0')
  screen_resolution = display_modes[0] # pick highest/only res
  screen = pygame.display.set_mode(screen_resolution, pygame.FULLSCREEN)
  pygame.mouse.set_visible(False)
else: # desktop running in X11 windows
  screen_resolution = display_modes[len(display_modes)-1] # pick lowest res
  screen = pygame.display.set_mode(screen_resolution, pygame.RESIZABLE)
  pygame.display.set_caption('Thermostat (%d, %d)'%screen_resolution, 'Tstat')
  pygame.mouse.set_visible(True)
(W,H) = screen_resolution
print "screen size is (%d, %d)" % (W, H)
screen.fill((0,0,0))
pygame.display.update()

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
''' -- deprecated --
def getTemperature(sensor):
  sensor.trigger()
  sleep(0.2)
  return (sensor.temperature(), sensor.humidity())
'''
'''
Orientation of thermostat dial:
  The origin of dial is the center of the screen (W/2, H/2).  The bottom of the dial
  is 0 degrees and top is 180 degrees.  We set the temperature for 180 degrees to be
  70 degrees Farenheight, (T180 = 70).  The dial radius is H/2.
  
  Because the LCD screen top left coodinate is (0,0) and bottom right is (320,240),
  the cartesian system is mirrored about x-axis, therefore, coordinates are (x, -y).
  Polar system is rotated 270 degrees, to orient the polar axis pointing downward.
  Therefore the equations to translate from cartesian to polar coordinates are:
  (x, -y) = (r*cos(deg+270), r*sin(deg+270))
  x = r*cos(deg+270) = -r*sin(deg)
  y = - r*sin(deg+270) = r*cos(deg)
'''
#Thermostat params
TICK_MARGIN = 5
deg_degF = 8
T180 = 70
deg_intercept = 180 - T180 * deg_degF
target = 75
current = 68

def heat2degrees (T):
  return deg_degF * T + deg_intercept

class Dial(pygame.sprite.Sprite):
  def __init__(self, width, height):
    pygame.sprite.Sprite.__init__(self)
    self.image = pygame.Surface([width, height])
    self.rect = self.image.get_rect()
    self.radius = height / 2
    self.tick_length = self.radius * 5 / 24 #25 #H*5/48
    self.tick_width = 1
    self.tick_margin =  self.radius * 1 / 24 #5 #H*1/48
    self.deg_per_tick = 2
    self.color = Black
    self.update(self.color)
    
  def resize(self, (w, h)):
    self.image = pygame.transform.smoothscale(self.image, (w, h))
    self.rect = self.image.get_rect()
    self.radius = h/2
    self.tick_length = self.radius * 5 / 24
    self.tick_margin =  self.radius * 1 / 24
    self.update(self.color)

  def update(self, color=None):
    if color != None: self.color = color
    center = (x0, y0) = (self.rect.center)
    #draw circle with diameter of surface height, filled in
    self.image.fill((0,0,0))
    pygame.draw.circle(self.image, self.color, center, self.radius, 0)
    #draw tick lines
    r1 = self.radius - self.tick_margin
    r0 = r1 - self.tick_length
    for i in range(30, 330, self.deg_per_tick):
      p0 = (x0-r0*math.sin(math.radians(i)), y0+r0*math.cos(math.radians(i)))
      p1 = (x0-r1*math.sin(math.radians(i)), y0+r1*math.cos(math.radians(i)))
      if machine_type == desktop:
        pygame.draw.aaline(self.image, Gray, p0, p1, self.tick_width)
      else: pygame.draw.line(self.image, Gray, p0, p1, self.tick_width)

class Tick(pygame.sprite.Sprite):
  #Draw a radial tick mark of length and places relative to the center of screen.
  def __init__(self, length, width, color):
    pygame.sprite.Sprite.__init__(self)
    #self.image = pygame.Surface([length, length])
    self.surface = pygame.Surface([width, length]).convert_alpha()
    self.surface.fill(color)
    self.image = self.surface
    self.rect = self.image.get_rect()
    self.r = H / 2 - H*1/48 #TICK_MARGIN
    self.center = (self.x0, self.y0) = (W/2, H/2)
  
  def resize(self, (w, h)):
    self.r = h/2 - h/48
    self.image = pygame.transform.smoothscale(self.image, (w, h))
    #self.rect = self.image.get_rect() # doesn't matter?
    self.center = (self.x0, self.y0) = (w/2, h/2)
    self.update(self.temperature)

  def update(self, temperature):
    #rotate tick line sprite
    if temperature == -999:
      deg = 00
    else:
      deg = heat2degrees(temperature)
    self.temperature = temperature
    #round to nearest dial tick mark
    deg = round(deg/2)*2
    #print "deg=%d" % deg
    self.image = pygame.transform.rotate(self.surface, -deg)
    self.rect = self.image.get_rect()
    #place tick line sprite on dial
    #(x0, y0) = (W/2, H/2) # screen center
    len = self.surface.get_rect().height
    #print "len=%d" % len
    p0 = (self.x0-(self.r-len)*math.sin(math.radians(deg))\
         ,self.y0+(self.r-len)*math.cos(math.radians(deg)))
    if 0 <= deg < 90:
      self.rect.topright = p0
    if 90 <= deg < 180:
      self.rect.bottomright = p0
    if 180 <= deg < 270:
      self.rect.bottomleft = p0
    if 270 <= deg < 360:
      self.rect.topleft = p0

class Temperature_display(pygame.sprite.Sprite):
  #Display temperature on thermostat dial.  Radius varies from 0 to 120
  def __init__(self, radius, temperature, format, color):
    pygame.sprite.Sprite.__init__(self)
    self.temperature = temperature
    self.format = format
    self.color = color
    self.radius = radius
    self.center = (self.x0, self.y0) = (W/2, H/2)
    self.font = pygame.font.Font(None, H*5/12 - radius * H*3/12/(H/2-H/8))
    self.update(self.temperature, self.format, self.color)
  
  def resize(self, (w, h)):
    self.radius = self.radius * h/(2*self.y0)
    self.center = (self.x0, self.y0) = (w/2, h/2)
    self.update(self.temperature, self.format, self.color)

  def update(self, temperature, format='%d', color=(255,255,255)):
    self.temperature = temperature
    if temperature == -999: deg = 0
    else: deg = heat2degrees(temperature)
    if target <= temperature:
      adv = 12 # advance or retard depending on system mode
    else:
      adv = -12
    self.image = self.font.render(format%temperature, True, color)
    x = self.x0 - self.radius * math.sin(math.radians(deg+adv))
    y = self.y0 + self.radius * math.cos(math.radians(deg+adv))
    self.rect = self.image.get_rect(center=(x,y))
  #def move(self, scale): #zoom?

class Text_xy(pygame.sprite.Sprite):
  def __init__(self, xy, fontsize, color):
    pygame.sprite.Sprite.__init__(self)
    self.font = pygame.font.Font(None, fontsize)
    self.color = color
    self.xy = xy
  def update(self, text):
    self.image = self.font.render(text, True, self.color)
    self.rect = self.image.get_rect(bottomleft=self.xy)
  
class Humidity_display(pygame.sprite.Sprite):
  #Display humidity value with color scaled to value
  def __init__(self, xy, fontsize):
    pygame.sprite.Sprite.__init__(self)
    self.fontsize = fontsize
    self.font = pygame.font.Font(None, fontsize)
    self.xy = xy
  def resize(self, (w, h)):
    self.fontsize = int(self.fontsize * h/float(self.xy[1]))
    self.font = pygame.font.Font(None, self.fontsize)
    self.xy = (0, h)
  def update(self, value):
    if value < 0 or value > 100:
      (r,g,b) = (40,40,40)
    else:
      # scale blue to cyan
      r = round(100 * (1- float(value) / 100)**.25)
      g = round(255 * (1 - float(value) / 100)**0.33)
      b = 255 #round(255 * float(value) / 100)
      #print "r=%d, g=%d, b=%d" % (r,g,b)
    self.image = self.font.render('%d'%value+'%RH', True, (r,g,b))
    self.rect = self.image.get_rect(bottomleft=self.xy)

def landedRedX(position):
  # Red X in top right corner 25x25 pixels
  print "landed at %d,%d" % (position[0], position[1])
  landingRect = pygame.Rect(rectRedX.left-16, rectRedX.top-6, 50, 40)
  #print "RedX topleft=(%d,%d)" % landingRect.topleft
  #print "RedX bottomright=(%d,%d)" % landingRect.bottomright
  return landingRect.collidepoint(position)

class ResizableGroup(pygame.sprite.Group):
  def resize(self, size):
    for sprite in self.sprites():
      sprite.resize(size)

#Colours
White = (255,255,255)
Gray = (140,140,140,255)
Black = 0x000000
Blue = (0,0,255)
Red = (255,0,0)

#Fonts
font_big = pygame.font.Font(None, 100)
font_lil = pygame.font.Font(None, 40)
font_liler = pygame.font.Font(None, 30)
font_tiny = pygame.font.Font(None, 15)

#Logic
fpsClock = pygame.time.Clock()
FPS = 10
POLL_SENSOR = pygame.USEREVENT + 1
TRIGGER_SENSOR = pygame.USEREVENT + 2
RESIZE_SCREEN = pygame.USEREVENT + 3
'''

  pygame.time.set_timer(POLL_SENSOR, READ_SENSOR_INTERVAL*1000)
else: pygame.time.set_timer(POLL_SENSOR, READ_SENSOR_INTERVAL*1000)
'''
if s.type() == 'DHT11':
  pygame.time.set_timer(TRIGGER_SENSOR, READ_SENSOR_INTERVAL*1000)
#elif s.type() == 'dummy':
#  pygame.time.set_timer(TRIGGER_SENSOR, READ_SENSOR_INTERVAL*1000)
running = True

# start rendering
dial = Dial(W, H)
dial.update(Blue)
screen.blit(dial.image, (0,0))
pygame.display.flip()

# Touch red x to quit game
RedX = font_lil.render("X", False, Red)
rectRedX = RedX.get_rect()
rectRedX.move_ip(W/16,H/12) # top left corner
screen.blit(RedX, rectRedX)
pygame.display.flip()

# initialize sprites
target_tick = Tick(H*33/240 , 3, White)
current_tick = Tick(H*5/48, 3, White)
target_temp = Temperature_display(0, 0, '%d', White)
current_temp = Temperature_display(H/2-H/12, 78, '%.1f', White)
humidity = Humidity_display((0,H), 30)
target_temp.update(75)
current_temp.update(current)
humidity.update(10)

# set up the sprite groups
ambient = pygame.sprite.Group(current_temp, current_tick)
setpoint = pygame.sprite.Group(target_temp, target_tick)
thermostat = pygame.sprite.RenderUpdates(ambient.sprites(), setpoint.sprites(), humidity)
all = ResizableGroup(thermostat.sprites(), dial)
#thermostat.add(target_tick, current_tick, target_temp, current_temp, humidity)

target_tick.update(target)
current_tick.update(current)
rectlist = thermostat.draw(screen)
pygame.display.update(rectlist)

while running == True:
  pygame.event.pump() # is this needed???
  for ev in pygame.event.get():
  #ev = pygame.event.wait()
    if ev.type == pygame.MOUSEBUTTONDOWN and landedRedX(pygame.mouse.get_pos()):
      running = False # quit the game

    if machine_type == desktop:
      if ev.type == pygame.MOUSEBUTTONDOWN:
        pygame.time.set_timer(POLL_SENSOR, 0)
      if ev.type == pygame.MOUSEBUTTONUP: #or ev.type == pygame.MOUSEMOTION:
        #pygame.time.set_timer(POLL_SENSOR, 100)
        print 'mouse up'

    if ev.type == pygame.QUIT: running = False # quit the game

    if ev.type == TRIGGER_SENSOR:
      s.trigger()
      if s.type() == 'DHT11':
        pygame.time.set_timer(POLL_SENSOR, 200)
      elif s.type() == 'dummy':
        pygame.event.post(pygame.event.Event(POLL_SENSOR))

    if ev.type == POLL_SENSOR:
      if s.type() == 'DHT11': pygame.time.set_timer(POLL_SENSOR, 0)
      #(current, rhum) = getTemperature(s) # WAIT 200 MSEC!!!!
      current = s.temperature()
      rhum = s.humidity()
      current = round(current*4)/4 # round temperature up to nearest 0.25F
      thermostat.clear(screen, dial.image)
      ambient.update(current)
      humidity.update(rhum)
      rectlist = thermostat.draw(screen)
      #print "dirty rectangles = %d" % len(rectlist)
      pygame.display.update(rectlist)

    if ev.type == pygame.VIDEORESIZE and machine_type == desktop:
      '''
      To ignore stream of events while dragging the mouse, reset a timer to generate
      a resize event.  No mouse up/down events are generated during screen resizing.
      '''
      pygame.time.set_timer(RESIZE_SCREEN, 0)
      newsize = ev.size
      pygame.time.set_timer(RESIZE_SCREEN, 500)

    if ev.type == RESIZE_SCREEN:
      pygame.time.set_timer(RESIZE_SCREEN, 0)
      pygame.display.set_mode(newsize, pygame.RESIZABLE)
      all.resize(newsize)
      (W,H) = newsize
      pygame.display.set_caption('Thermostat (%d, %d)'%newsize, 'Tstat')
      screen.blit(dial.image, (0,0))
      pygame.display.flip()

  fpsClock.tick(FPS)
  if s.type() == 'dummy':
    #print 'post event TRIGGER_SENSOR'
    pygame.event.post(pygame.event.Event(TRIGGER_SENSOR))

# terminate
pygame.quit()
s.cancel()
try:
  pi
  pi.stop()
except:
  pass
sys.exit()