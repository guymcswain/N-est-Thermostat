import pygame
import os
from time import sleep
import math

# Try ensure using framebuffer and not X11 display even if it exists
ENV_VAR_DISPLAY = "DISPLAY"
if ENV_VAR_DISPLAY in os.environ:
  del os.environ[ENV_VAR_DISPLAY]
else:
  print "No display in os.environ"
# For Raspberry Pi ZeroW use screen size 640x480 and /dev/fb0
os.putenv('SDL_FBDEV', '/dev/fb1')
pygame.init()
pygame.mouse.set_visible(False)
#size = (pygame.display.Info().current_w, pygame.display.Info().current_h)
# For Raspberry Pi ZeroW use screen size 640x480 and /dev/fb0
(W,H) = (320, 240)
screen = pygame.display.set_mode((W,H), pygame.FULLSCREEN)
screen.fill((0,0,0))
pygame.display.update()
print 'display driver =', pygame.display.get_driver()
info = pygame.display.Info()
if info.hw:
  print 'display is hw accelerated'
else:
  print 'display is NOT hw accelerated'
print "%d KiB video memory detected" % info.video_mem
print "screen size is %d x %d" % (info.current_w, info.current_h)

#Colours
White = (255,255,255)
Gray = (160,160,160,255)
Black = 0x000000
Blue = 0x0000ff

#Thermostat params
Center = (X0,Y0) = (W/2,H/2)
R1 = H/2-5
R0 = H/2-20
Width = 1
target = 75
current = 78

def heat2degrees (t):
  return 360/60*t -240
  #return math.radians(degrees)

pygame.draw.circle(screen, Blue, Center, H/2, 0)
pygame.display.update()

for i in range(30,330,3):
  p0 = (X0-R0*math.sin(math.radians(i)), Y0+R0*math.cos(math.radians(i)))
  p1 = (X0-R1*math.sin(math.radians(i)), Y0+R1*math.cos(math.radians(i)))
  if i > heat2degrees(target) and i <= heat2degrees(current):
    pygame.draw.line(screen, White, p0, p1, Width*3)
  else:
    pygame.draw.line(screen, Gray, p0, p1, Width*3)

# draw target line
i = heat2degrees(target)
p0 = (X0-(R0-8)*math.sin(math.radians(i)), Y0+(R0-8)*math.cos(math.radians(i)))
p1 = (X0-R1*math.sin(math.radians(i)), Y0+R1*math.cos(math.radians(i)))
pygame.draw.line(screen, White, p0, p1, Width*4)
# draw current line
i = heat2degrees(current)
p0 = (X0-R0*math.sin(math.radians(i)), Y0+R0*math.cos(math.radians(i)))
p1 = (X0-R1*math.sin(math.radians(i)), Y0+R1*math.cos(math.radians(i)))
pygame.draw.line(screen, White, p0, p1, Width*4)
pygame.display.update()

# write Target and Current temperatures
font_big = pygame.font.Font(None, 100)
font_lil = pygame.font.Font(None, 40)
text_surface = font_big.render('%d'%target, True, White)
rect = text_surface.get_rect(center=(W/2,H/2))
screen.blit(text_surface, rect)
text_surface = font_lil.render('%d'%current, True, White)
rect = text_surface.get_rect()
rect.topleft = (p0[0]+2, p0[1]+2)
screen.blit(text_surface, rect)


pygame.display.update()
sleep(60)
#for i in range(1000):
#  pygame.display.flip()
#  sleep(0.001)

