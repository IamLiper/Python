# player.py
import pygame
from config import *

class Player:
    def __init__(self):
        self.rect = pygame.Rect(100, SCREEN_HEIGHT - GROUND_HEIGHT - PLAYER_HEIGHT, PLAYER_WIDTH, PLAYER_HEIGHT)
        self.speed = PLAYER_SPEED

    def handle_keys(self):
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:
            self.rect.x -= self.speed
        if keys[pygame.K_RIGHT]:
            self.rect.x += self.speed
        if keys[pygame.K_UP]:
            self.rect.y -= self.speed
        if keys[pygame.K_DOWN]:
            self.rect.y += self.speed

    def update(self):
        self.handle_keys()

        # Impede o jogador de sair da tela
        self.rect.x = max(0, min(self.rect.x, SCREEN_WIDTH - PLAYER_WIDTH))
        self.rect.y = max(0, min(self.rect.y, SCREEN_HEIGHT - PLAYER_HEIGHT))

        # Evita que desça abaixo do chão
        ground_y = SCREEN_HEIGHT - GROUND_HEIGHT - PLAYER_HEIGHT
        if self.rect.y > ground_y:
            self.rect.y = ground_y

    def draw(self, surface):
        pygame.draw.rect(surface, PLAYER_COLOR, self.rect)
