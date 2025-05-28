# main.py
import pygame
from config import *
from player import Player
from level import draw_ground
import os

pygame.init()

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("RPG Plataforma 2D")
clock = pygame.time.Clock()

# Música
sound_path = os.path.join("assets", "sounds", "bg_music.mp3")
if os.path.exists(sound_path):
    pygame.mixer.music.load(sound_path)
    pygame.mixer.music.play(-1)
else:
    print("⚠️ bg_music.ogg não encontrado. Coloque o arquivo em assets/sounds/")

player = Player()
running = True

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    player.update()

    screen.fill(BACKGROUND_COLOR)
    draw_ground(screen)
    player.draw(screen)

    pygame.display.flip()
    clock.tick(FPS)

pygame.quit()
