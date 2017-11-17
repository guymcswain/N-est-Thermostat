import pygame
import os
from time import sleep
import math
import pigpio
import DHT11

# Intervals of about 2 seconds or less will eventually hang the DHT22.
READ_SENSOR_INTERVAL = 3

pi = pigpio.pi("10.0.0.105")  #surveyor pi
if not pi.connected:
  print "can't connect to pi @ 10.0.0.105, exiting"
  exit(0)
print 'connected to pi @ 10.0.0.105'

s = DHT11.sensor(pi, 22)
def getTemperature(sensor):
  sensor.trigger()
  sleep(0.2)
  return (sensor.temperature(), sensor.humidity())

os.putenv('SDL_FBDEV', '/dev/fb1')
os.putenv('SDL_MOUSEDRV', 'TSLIB')
os.putenv('SDL_MOUSEDEV', '/dev/input/event0')
pygame.init()
# Get information about display
print 'display driver =', pygame.display.get_driver()
info = pygame.display.Info()
print info

pygame.mouse.set_visible(False)
(W,H) = (320, 240)
display_modes = pygame.display.list_modes()
print display_modes
screen = pygame.display.set_mode((W,H), pygame.FULLSCREEN)
screen.fill((0,0,0))
pygame.display.update()
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
    self.image.fill((0,0,0))
    self.rect = self.image.get_rect()
    self.tick_length = 25
    self.tick_len = 25
    self.tick_width = 1
    self.tick_margin = 5
    self.deg_per_tick = 2
    
  def update(self, color):
    center = (x0, y0) = (self.rect.center)
    print "x0=%d, y0=%d"%(x0,y0)
    radius = self.rect.height/2
    print "radius=%d"%radius
    #draw circle with diameter of surface height, filled in
    pygame.draw.circle(self.image, color, center, radius, 0)
    #draw tick lines
    r1 = radius - self.tick_margin
    r0 = r1 - self.tick_length
    for i in range(30, 330, self.deg_per_tick):
      p0 = (x0-r0*math.sin(math.radians(i)), y0+r0*math.cos(math.radians(i)))
      p1 = (x0-r1*math.sin(math.radians(i)), y0+r1*math.cos(math.radians(i)))
      pygame.draw.line(self.image, Gray, p0, p1, self.tick_width)

class Tick(pygame.sprite.Sprite):
  #Draw a radial tick mark of length and places relative to the center of screen.
  def __init__(self, length, width, color):
    pygame.sprite.Sprite.__init__(self)
    #self.image = pygame.Surface([length, length])
    self.surface = pygame.Surface([width, length]).convert_alpha()
    self.surface.fill(color)
    self.image = self.surface
    self.rect = self.image.get_rect()
  
  def update(self, temperature):
    #rotate tick line sprite
    if temperature == -999:
      deg = 00
    else:
      deg = heat2degrees(temperature)
    #round to nearest dial tick mark
    deg = round(deg/2)*2
    #print "deg=%d" % deg
    self.image = pygame.transform.rotate(self.surface, -deg)
    self.rect = self.image.get_rect()
    #place tick line sprite on dial
    r = H / 2 - TICK_MARGIN
    (x0, y0) = (W/2, H/2) # screen center
    len = self.surface.get_rect().height
    #print "len=%d" % len
    p0 = (x0-(r-len)*math.sin(math.radians(deg)), y0+(r-len)*math.cos(math.radians(deg)))
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
    self.color = color
    self.format = format
    self.radius = radius
    self.font = pygame.font.Font(None, 100 - radius * 60/90)
    #self.update(temperature)
    
  def update(self, temperature, format='%d', color=(255,255,255)):
    if temperature == -999:
      deg = 0
    else: deg = heat2degrees(temperature + 1.5) # add offset to keep above tick mark
    self.image = self.font.render(format%temperature, True, color)
    x = W/2 - self.radius * math.sin(math.radians(deg))
    y = H/2 + self.radius * math.cos(math.radians(deg))
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
    self.font = pygame.font.Font(None, fontsize)
    self.xy = xy
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
  return rectRedX.collidepoint(position)

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
POLL_SENSOR = pygame.USEREVENT + 1
pygame.time.set_timer(POLL_SENSOR, READ_SENSOR_INTERVAL*1000)
running = True

# start rendering
dial = Dial(W, H)
dial.update(Blue)
screen.blit(dial.image, (0,0))
pygame.display.flip()

# Touch red x to quit game
RedX = font_lil.render("X", False, Red)
rectRedX = RedX.get_rect()
rectRedX.move_ip(W-rectRedX.width-20,20) # top right corner
screen.blit(RedX, rectRedX)
pygame.display.flip()

# initialize sprites
target_tick = Tick(33 , 3, White)
current_tick = Tick(25, 3, White)
target_temp = Temperature_display(0, 0, '%d', White)
current_temp = Temperature_display(100, 78, '%.1f', White)
humidity = Humidity_display((0,240), 30)
target_temp.update(75)
current_temp.update(78)
humidity.update(10)

thermostat = pygame.sprite.RenderUpdates()
thermostat.add(target_tick, current_tick, target_temp, current_temp, humidity)
target_tick.update(target)
current_tick.update(current)
rectlist = thermostat.draw(screen)
pygame.display.update(rectlist)

while running == True:
  ev = pygame.event.wait()
  if ev.type == pygame.MOUSEBUTTONDOWN and landedRedX(pygame.mouse.get_pos()):
    running = False # quit the game
  #elif ev.type == pygame.MOUSEBUTTONUP or ev.type == pygame.MOUSEMOTION:
    # ignore for now

  elif ev.type == POLL_SENSOR:
    (current, rhum) = getTemperature(s)
    # round temperature up to nearest 0.25F
    current = round(current*4)/4
    thermostat.clear(screen, dial.image)
    current_tick.update(current)
    current_temp.update(current, '%.1f')
    humidity.update(rhum)
    rectlist = thermostat.draw(screen)
    #print "dirty rectangles = %d" % len(rectlist)
    pygame.display.update(rectlist)

pygame.quit()
s.cancel()
pi.stop()
