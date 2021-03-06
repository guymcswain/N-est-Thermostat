import pygame
import os, sys
from time import sleep
import math

# set up the screen and device drivers per type of machine we are running on
machine_type = os.uname()[4]
desktop = 'x86_64'
if machine_type != desktop: # assume RPI ZeroW with patched kernel for ft6236
  os.putenv('SDL_FBDEV', '/dev/fb1')
  os.putenv('SDL_MOUSEDRV', 'TSLIB')
  os.putenv('SDL_MOUSEDEV', '/dev/input/touchscreen')

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

if machine_type != desktop: # assume RPI ZeroW with patched kernel for ft6236
  print "Raspberry Pi machine type assumed"
  screen_resolution = display_modes[0] # pick highest/only res
  screen = pygame.display.set_mode(screen_resolution, pygame.FULLSCREEN)
  pygame.mouse.set_visible(False)
else: # desktop running in X11 windows
  print "X86_64 desktop detected"
  screen_resolution = display_modes[len(display_modes)-1] # pick lowest res
  screen = pygame.display.set_mode(screen_resolution, pygame.RESIZABLE)
  pygame.display.set_caption('Thermostat (%d, %d)'%screen_resolution, 'Tstat')
  pygame.mouse.set_visible(True)

(W,H) = screen_resolution
print "screen size is (%d, %d)" % (W, H)
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
#Thermostat drawing params - constants
TICK_MARGIN = 5
deg_degF = 8
T180 = 70
deg_intercept = 180 - T180 * deg_degF
ring_outer_radius = H/2 - TICK_MARGIN
ring_inner_radius = H/2 - H/8
ring_width = ring_outer_radius - ring_inner_radius
ring_center_radius = ring_inner_radius + ring_width / 2

#Thermostat display settings
setpoint_options = {'low': 1, 'medium': 2, 'high': 4}
setpoint_divisor = setpoint_options['medium']

#Thermostat HVAC system part
target = 'target'
current = 'current'
rhum = 'rhum'
mode = 'mode'
relays = 'relays'
auto = 'auto'
(COOLING, HEATING, COMBI, OFF) = (0, 1, 2, 3)
SYSTEM_COOLING, SYSTEM_HEATING, SYSTEM_OFF, SYSTEM_FAN = (0, 1, 2, 3)
system = {target:None, current:None, mode:None, rhum:None, relays:None}

def system_update():
  global system, mode, current, target
  # Update system dict with hvac object
  system[mode] = hvac.mode
  system[current] = hvac.temperature
  system[rhum] = hvac.relative_humidity
  #print system[current]
  system[target] = hvac.setpoint
  system[relays] = hvac.relays
  system[auto] = hvac.autoMode

from hvac_client import HVAC_Client
serverhost = 'localhost'
port = 8999
hvac = HVAC_Client(serverhost, port)
system_update() # update system dict with hvac object

def heat2degrees (T):
  return deg_degF * T + deg_intercept

class Dial(pygame.sprite.DirtySprite):
  global system
  def __init__(self, width, height):
    pygame.sprite.DirtySprite.__init__(self)
    self.image = pygame.Surface((width, height))
    self.rect = self.image.get_rect()
    self.radius = height / 2
    self.relays = None
    self.update()
    
  def resize(self, (w, h)):
    self.image = pygame.transform.smoothscale(self.image, (w, h))
    self.rect = self.image.get_rect()
    self.radius = h/2
    self.update()

  def update(self):
    if self.relays != system[relays]: # changed?
      self.relays = system[relays]
      if system[relays] == SYSTEM_OFF:      color = Black
      if system[relays] == SYSTEM_COOLING:  color = Blue
      if system[relays] == SYSTEM_HEATING:  color = ORANGE
      #draw circle with diameter of surface height, filled in
      pygame.draw.circle(self.image, color, self.rect.center, self.radius, 0)
      self.dirty = 1
    
class Tickmark(pygame.sprite.DirtySprite):
  '''Tickmark sprites are drawn onto dial surface as part of thermostat background
  and become highlighted when their temperature lies between current and target.
  Tickmarks shall not update until after other thermostat sprites are cleared.'''
  global dial, system
  radius = H / 2 - H*1/48 #TICK_MARGIN
  length = H * 5 / 48
  surface = pygame.Surface([1, length])
  def __init__(self, rotation):
    pygame.sprite.DirtySprite.__init__(self)
    self.color = None
    self.rotation = rotation
    self.temperature = deg2heat2(rotation)
    self.rect = pygame.transform.rotate(Tickmark.surface, -deg).get_rect()
    p0 = (W/2 - (Tickmark.radius-Tickmark.length)*math.sin(math.radians(rotation))\
         ,H/2 + (Tickmark.radius-Tickmark.length)*math.cos(math.radians(rotation)))
    if 0 <= rotation < 90:
      self.rect.topright = p0
    if 90 <= rotation <= 180:
      self.rect.bottomright = p0
    if 180 < rotation < 270:
      self.rect.bottomleft = p0
    if 270 <= rotation < 360:
      self.rect.topleft = p0
    self.image = dial.image.subsurface(self.rect)
    self.update()
  
  def update(self):
    if dial.dirty:
      for tick in tickmarklist: tick.color = None
    
    if system[current] < self.temperature < system[target]\
    or system[target] < self.temperature < system[current]:
      color = White
    else: color = Gray
    if system[mode] == OFF: color = Gray
    if 90 <= self.rotation < 180 or 270 <= self.rotation < 360:
      if self.color != color:
        pygame.draw.line(self.image, color, (0,0), (self.rect.w-1,self.rect.h-1))
        self.color = color
        self.dirty = 1
    else:
      if self.color != color:
        pygame.draw.line(self.image, color, (0,self.rect.h-1), (self.rect.w-1,0))
        self.color = color
        self.dirty = 1

class Tick(pygame.sprite.DirtySprite):
  global system
  #Draw a radial tick mark of length and places relative to the center of screen.
  def __init__(self, temperatureIndex, length, width, color):
    self.temperatureIndex = temperatureIndex # tracks this system temperature
    self.temperature = None
    pygame.sprite.DirtySprite.__init__(self)
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
    self.update()

  def update(self):
    if system[mode] == OFF and self.temperatureIndex == target:
      self.visible = 0
      self.dirty = 1
      return
    self.visible = 1
    #rotate tick line sprite
    if self.temperature != system[self.temperatureIndex]:
      self.temperature = system[self.temperatureIndex]
      if system[self.temperatureIndex] == -999:
        deg = 00
      else:
        deg = heat2degrees(system[self.temperatureIndex])
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
      self.dirty = 1

class Temperature_display(pygame.sprite.DirtySprite):
  global system
  #Display temperature on thermostat dial.  Radius varies from 0 to 120
  def __init__(self, radius, temperatureIndex, format, color):
    pygame.sprite.DirtySprite.__init__(self)
    self.temperatureIndex = temperatureIndex
    self.temperature = None
    self.adv = 0
    self.format = format
    self.color = color
    self.radius = radius
    self.center = (self.x0, self.y0) = (W/2, H/2)
    size = H*3/12 if temperatureIndex == target else ring_width
    self.font = pygame.font.SysFont(myFont, size)
    self.update(self.format, self.color)
  
  def resize(self, (w, h)):
    self.radius = self.radius * h/(2*self.y0)
    self.center = (self.x0, self.y0) = (w/2, h/2)
    self.update(self.format, self.color)

  def update(self, format=None, color=None):
    if system[mode] == OFF and self.temperatureIndex == target:
      self.visible = 0
      self.dirty = 1
      return
    self.visible = 1  
    if self.temperature != system[self.temperatureIndex]:

      self.temperature = system[self.temperatureIndex]
      if system[self.temperatureIndex] == -999: deg = 0
      else: deg = heat2degrees(system[self.temperatureIndex])
      if system[target] < system[self.temperatureIndex]:
        self.adv = 15 # advance or retard depending on system target
      elif system[target] > system[self.temperatureIndex]:
        self.adv = -15
      if format == None: format = self.format
      if color == None: color = self.color
      x = self.x0 - self.radius * math.sin(math.radians(deg+self.adv))
      y = self.y0 + self.radius * math.cos(math.radians(deg+self.adv))
      if changing_setpoint and self.temperatureIndex == target:
        format = "%.2f" if setpoint_divisor == 4 else "%.1f" if setpoint_divisor == 2 else "%d"
        self.image = font_big.render(format%system[self.temperatureIndex], True, color)
      else:
        temp = round(system[self.temperatureIndex])
        self.image = self.font.render(format%temp, True, color)
      self.rect = self.image.get_rect(center=(x,y))
      self.dirty = 1

class Humidity_display(pygame.sprite.DirtySprite):
  #Display humidity value with color scaled to value
  def __init__(self, sysindex, xy, fontsize):
    pygame.sprite.DirtySprite.__init__(self)
    self.sysindex = sysindex
    self.fontsize = fontsize
    self.font = pygame.font.SysFont(myFont, fontsize)
    self.xy = xy
    self.value = None
  def resize(self, (w, h)):
    self.fontsize = int(self.fontsize * h/float(self.xy[1]))
    self.font = pygame.font.SysFont(myFont, self.fontsize)
    self.xy = (0, h)
  def update(self):
    value = system[self.sysindex]
    if self.value != value: # changed?
      self.value = value
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
      self.dirty = 1

class AutoMode_display(pygame.sprite.DirtySprite):
  #Display autoMode 
  def __init__(self, sysindex, xy, fontsize):
    pygame.sprite.DirtySprite.__init__(self)
    self.sysindex = sysindex
    self.fontsize = fontsize
    self.font = pygame.font.SysFont(myFont, fontsize)
    self.xy = xy
    self.value = None
  def resize(self, (w, h)):
    self.fontsize = int(self.fontsize * h/float(self.xy[1]))
    self.font = pygame.font.SysFont(myFont, self.fontsize)
    self.xy = (0, h)
  def update(self):
    value = system[self.sysindex]
    if self.value != value: # changed?
      self.value = value
      text = "COOLING" if value==0 else "HEATING" if value==1 else "SYSTEM OFF" if value==3 else "?"
      self.image = self.font.render(text, True, White)
      self.rect = self.image.get_rect(center=self.xy)
      self.dirty = 1

class Heaticon(pygame.sprite.DirtySprite):
  global system
  def __init__(self, (w,h), position):
    pygame.sprite.DirtySprite.__init__(self)
    self.image = pygame.Surface((w,h))
    self.rect = pygame.Rect(position,(w,h))
    self.position = position
    self.mode = None
    self.update()
  def update(self):
    if self.mode != system[mode]:
      self.mode = system[mode]
      pxarray = pygame.PixelArray(self.image)
      (a,b) = pxarray.shape
      #print "a=%d, b=%d" %(a,b)
      if system[mode] == COOLING:
        color1, color2, color3 = (Blue, Blue, Blue)
      elif system[mode] == HEATING:
        color1, color2, color3 = (ORANGE, ORANGE, ORANGE)
      elif system[mode] == COMBI:
        color1, color2, color3 = (ORANGE, White, Blue)
      else:
        color1, color2, color3 = (White, White, White)
      h = self.rect.height
      lines = [(h/4, color1), (h/2, color2), (h*3/4, color3)]
      for (line, color) in lines:
        for x in range(0,a):
          y = line - int(round(math.sin(2*math.pi*x/a) * b/8))
          pxarray[x,y]   = color
          pxarray[x,y-1] = color
          pxarray[x,y+1] = color
      self.image = pxarray.make_surface()
      self.rect = self.image.get_rect()
      self.rect.topleft = self.position
      self.dirty = 1

class ResizableGroup(pygame.sprite.Group):
  def resize(self, size):
    for sprite in self.sprites():
      sprite.resize(size)

def distance((x,y)):
  return math.sqrt((W/2-x)**2 + (H/2-y)**2)

def angle((x,y)):
  return (math.degrees(math.atan2((y-H/2), (x-W/2))) + 270) % 360

def deg2heat(deg):
  return deg / deg_degF


#Colours
White = (255, 255, 255)
Gray =  (140, 140, 140, 255)
Black = (0  , 0  , 0  ) #0x000000
Blue =  (0  , 0  , 255)
Red =   (255, 0  , 0)
ORANGE =(255, 128, 0)

#Fonts
listOfFonts = pygame.font.get_fonts()
print listOfFonts
myFont = listOfFonts[0]
font_big = pygame.font.SysFont(myFont, 100)
font_lil = pygame.font.SysFont(myFont, 40)
font_liler = pygame.font.SysFont(myFont, 30)
font_tiny = pygame.font.SysFont(myFont, 15)

#Logic
fpsClock = pygame.time.Clock()
FPS = 20
POLL_SENSOR = pygame.USEREVENT + 1
TRIGGER_SENSOR = pygame.USEREVENT + 2
RESIZE_SCREEN = pygame.USEREVENT + 3
initial_angle = 0
changing_setpoint = False

running = True
sensor_animate = True

# start rendering
dial = Dial(W, H)

# Touch hotbox to quit game (upper left corner of screen)
hotbox = pygame.Surface((W/8, H/8), 0, screen)
hotboxRect = hotbox.get_rect()

# Mode icon
modicon = Heaticon((W/8,W/8), (W-W/8, 0))

# initialize sprites
target_tick = Tick(target, H*33/240 , 3, White)
current_tick = Tick(current, H*5/48, 3, White)
target_temp = Temperature_display(0, target, '%d', White)
current_temp = Temperature_display(ring_center_radius, current, '%d', White)
humidity = Humidity_display(rhum, (0,H), 30)
autoMode = AutoMode_display(auto, (W/2,H/2-H/8-15), 20)
def deg2heat2(deg):
  temp = float(deg) / deg_degF + 47.5
  #round to nearest 1/4 degreeF
  temp = round(temp*4)/4
  return temp

tickmarklist = []
for deg in range(30, 332, 2):
  tickmarklist.append(Tickmark(deg))

# set up the sprite groups
thermostat = pygame.sprite.LayeredDirty( dial, tickmarklist
                                        , current_temp, current_tick
                                        , target_temp, target_tick
                                        , humidity, modicon, autoMode)

all = ResizableGroup(thermostat.sprites(), dial)
screenshots = 0
pygame.event.set_blocked(pygame.MOUSEMOTION)
while running == True:
  # Process events
  pygame.event.pump() # is this needed???
  for ev in pygame.event.get():
    if ev.type == pygame.MOUSEBUTTONDOWN and hotboxRect.collidepoint(pygame.mouse.get_pos()):
      if screenshots:
        pygame.image.save(screen, "screenshot"+str(screenshots)+".jpg")
        screenshots -= 1
      else:
        running = False

    if ev.type == pygame.MOUSEBUTTONDOWN:
      position = pygame.mouse.get_pos()
      #landed on ring?
      d = distance(position)
      print "distance=%d" % d
      if ring_inner_radius <= d <= ring_outer_radius:
        changing_setpoint = True
        initial_angle = angle(position)
        print "initial angle=%d" % initial_angle
        pygame.event.set_allowed(pygame.MOUSEMOTION) # needed for desktop
      elif modicon.rect.collidepoint(position):
        system[mode] = (system[mode] + 1) % 4
        hvac.mode = system[mode]

    if ev.type == pygame.MOUSEMOTION and changing_setpoint:
      ang = angle(pygame.mouse.get_pos())
      dt = deg2heat(ang - initial_angle)
      if abs(dt) >= float(1)/setpoint_divisor:
        initial_angle = ang
        #print "angle=%d, delta heat=%.2f" % (ang, dt)
        system[target] += dt
        #round to nearest setpoint divisor
        system[target] = round(system[target] * setpoint_divisor) / setpoint_divisor
        hvac.setpoint = system[target]

    if ev.type == pygame.MOUSEBUTTONUP and changing_setpoint:
      changing_setpoint = False
      system[target] += 0.001 #Work-around to temperature display logic ...
      target_temp.update()    #...to display with correct format
      system[current] += 0.001
      current_temp.update()   #FIXME: implement a forced-update method?
      pygame.event.set_blocked(pygame.MOUSEMOTION)

    if ev.type == pygame.QUIT: running = False # quit the game
    
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
      #screen.blit(dial.image, (0,0))
      #pygame.display.flip()

  # Render screen
  hvac.sync()
  system_update() #update the hvac system
  thermostat.update() #update sprites in thermostat group
  thermostat.clear(screen, dial.image) #clears only dirty sprites
  rectlist = thermostat.draw(screen) #redraws only dirty sprites
  #if len(rectlist) > 0:
  #  print "dirty rectangles = %d" % len(rectlist)
  pygame.display.update(rectlist)
  
  # Control timing (and generate new events)
  fpsClock.tick(FPS)

# terminate
pygame.quit()

try:
  pi
  pi.stop()
except:
  pass
sys.exit()