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
'''
if info.hw:
  print 'display is hw accelerated'
else:
  print 'display is NOT hw accelerated'
print "%d KiB video memory detected" % info.video_mem
print "desktop size is %d x %d" % (info.current_w, info.current_h)
print "bitsize is %d" % info.bitsize
'''
pygame.mouse.set_visible(False)
(W,H) = (320, 240)
display_modes = pygame.display.list_modes()
print display_modes
screen = pygame.display.set_mode((W,H), pygame.FULLSCREEN)
screen.fill((0,0,0))
pygame.display.update()
'''
Orientation of thermostat dial:
  The origin of dial is bottom center, 0 degrees, and top center, at 180 degrees,
  is where we mark for 70 degree Farenheight (T180=70).
'''

#Thermostat params
Center = (X0,Y0) = (W/2,H/2)
R1 = H/2-5
R0 = H/2-30
#Width = 1
tick_width = 1
mark_width = 3
ticks_per_degree = 2
deg_degF = 8
T180 = 70
deg_intercept = 180 - T180 * deg_degF
target = 75
current = 78

def heat2degrees (T):
  #return 360/60*t -240
  return deg_degF * T + deg_intercept

def draw_thermostat():
  pygame.draw.circle(screen, Blue, Center, H/2, 0)
  for i in range(30,330,ticks_per_degree):
    p0 = (X0-R0*math.sin(math.radians(i)), Y0+R0*math.cos(math.radians(i)))
    p1 = (X0-R1*math.sin(math.radians(i)), Y0+R1*math.cos(math.radians(i)))
    if i > heat2degrees(target) and i <= heat2degrees(current):
      pygame.draw.line(screen, White, p0, p1, tick_width)
    else:
      pygame.draw.line(screen, Gray, p0, p1, tick_width)

def draw_target_temperature():
  #line
  i = heat2degrees(target)
  p0 = (X0-(R0-8)*math.sin(math.radians(i)), Y0+(R0-8)*math.cos(math.radians(i)))
  p1 = (X0-R1*math.sin(math.radians(i)), Y0+R1*math.cos(math.radians(i)))
  pygame.draw.line(screen, White, p0, p1, mark_width)
  #temperature
  text_surface = font_big.render('%d'%target, True, White)
  rect = text_surface.get_rect(center=(W/2,H/2))
  screen.blit(text_surface, rect)

def draw_current_temperature():
  #line
  i = heat2degrees(current)
  p0 = (X0-R0*math.sin(math.radians(i)), Y0+R0*math.cos(math.radians(i)))
  p1 = (X0-R1*math.sin(math.radians(i)), Y0+R1*math.cos(math.radians(i)))
  pygame.draw.line(screen, White, p0, p1, mark_width)
  #temperature
  text_surface = font_liler.render('%.1f'%current, True, White)
  rect = text_surface.get_rect()
  placeRect(rect, i, p0)
  screen.blit(text_surface, rect)

def placeRect(rect, angle, position):
  R = 22.5
  if 180-R < angle < 180+R:
    rect.midtop = position
  elif 225-R < angle < 225+R:
    rect.topright = position
  elif 270-R < angle < 270+R:
    rect.midright = position
  elif 315-R < angle < 315+R:
    rect.bottomright = position
  elif 360-R < angle < 0+R:
    rect.midbottom = position
  elif 45-R < angle < 45+R:
    rect.bottomleft = position
  elif 90-R < angle < 90+R:
    rect.midleft = position
  elif 135-R < angle < 135+R:
    rect.topleft = position
  else: rect.topleft = (0,0)

def landedRedX(position):
  # Red X in top right corner 25x25 pixels
  return rectRedX.collidepoint(position)

#Colours
White = (255,255,255)
Gray = (140,140,140,255)
Black = 0x000000
Blue = 0x0000ff
Red = (255,0,0)

#Fonts
font_big = pygame.font.Font(None, 100)
font_lil = pygame.font.Font(None, 40)
font_liler = pygame.font.Font(None, 30)
font_tiny = pygame.font.Font(None, 15)

# Touch red x to quit game
RedX = font_liler.render("X", False, Red)
rectRedX = RedX.get_rect()
rectRedX.move_ip(W-30,0) # top right corner
screen.blit(RedX, rectRedX)

#Logic
POLL_SENSOR = pygame.USEREVENT + 1
pygame.time.set_timer(POLL_SENSOR, READ_SENSOR_INTERVAL*1000)
running = True
if pygame.key.get_focused() == False:
  print "keyboard not in focus, trying to grab it"
  pygame.event.set_grab(True)
# start rendering
draw_thermostat()
draw_target_temperature()
pygame.display.update()
RH = '% RH'
while running == True:
  ev = pygame.event.wait()
  ''' Won't work because we are using X windows (no keyboard either)
  if ev.type == pygame.QUIT:
    running = False
  '''
  if ev.type == pygame.MOUSEBUTTONDOWN and landedRedX(pygame.mouse.get_pos()):
    running = False # quit the game
  #elif ev.type == pygame.MOUSEBUTTONUP or ev.type == pygame.MOUSEMOTION:
    # ignore for now
  elif ev.type == POLL_SENSOR:
    (current, rhum) = getTemperature(s)
    # round temperature up to nearest 0.25F
    current = round(current*4)/4
    screen.fill((0,0,0))
    screen.blit(RedX, rectRedX)
    draw_thermostat()
    draw_target_temperature()
    draw_current_temperature()
    text_surface = font_liler.render('%d%s'%(rhum,RH), True, White)
    rect = text_surface.get_rect()
    rect.bottomleft = (0,H)
    screen.blit(text_surface, rect)
    pygame.display.update()
  elif ev.type == pygame.KEYDOWN: #and ev.key in (pygame.K_ESCAPE, pygame.K_q):
    running = False
    print "ESC or Q key detected, exiting pygame"


pygame.quit()


s.cancel()
pi.stop()
