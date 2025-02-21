import os
os.environ["SDL_AUDIODRIVER"] = "dummy"  # Força driver de áudio fake

import pygame

pygame.init()
pygame.mixer.init()

pygame.mixer.music.load('Desafios/music.mp3')
pygame.mixer.music.play()
pygame.event.wait()

while pygame.mixer.music.get_busy():
    pass
