import pygame
from config import *

def draw_ground(surface):
    ground_rect = pygame.Rect(0, SCREEN_HEIGHT - GROUND_HEIGHT, SCREEN_WIDTH, GROUND_HEIGHT)
    pygame.draw.rect(surface, GROUND_COLOR, ground_rect)
