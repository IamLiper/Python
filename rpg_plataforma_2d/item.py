import pygame
from config import ITEM_WIDTH, ITEM_HEIGHT, ITEM_COLOR

class Item:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, ITEM_WIDTH, ITEM_HEIGHT)
        self.collected = False

    def check_collision(self, player):
        if not self.collected and self.rect.colliderect(player.rect):
            self.collected = True
            player.score += 1

    def draw(self, surface):
        if not self.collected:
            pygame.draw.rect(surface, ITEM_COLOR, self.rect)
