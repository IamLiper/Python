import pygame

pygame.init()
pygame.mixer.init()

pygame.mixer.music.load('Desafios/desafio021/music.mp3')
pygame.mixer.music.play()
pygame.event.wait()

while pygame.mixer.music.get_busy():
    pass