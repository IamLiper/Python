import pygame
from config import *
from utils import load_spritesheet

class Enemy:
    def __init__(self, x, y, range_start, range_end):
        self.animations = {
            'idle': load_spritesheet('assets/images/enemy/idle.png', 128, 128, 4),
            'run': load_spritesheet('assets/images/enemy/run.png', 128, 128, 6),
            'die': load_spritesheet('assets/images/enemy/die.png', 128, 128, 3),
            'attack1': load_spritesheet('assets/images/enemy/attack1.png', 128, 128, 6),
            'attack2': load_spritesheet('assets/images/enemy/attack2.png', 128, 128, 4),
            'attack3': load_spritesheet('assets/images/enemy/attack3.png', 128, 128, 3),
        }

        self.state = 'run'
        self.frame_index = 0
        self.frame_timer = 0
        self.image = self.animations[self.state][self.frame_index]
        self.rect = self.image.get_rect(topleft=(x, y))

        self.range_start = range_start
        self.range_end = range_end
        self.speed = 2
        self.facing_right = True
        self.alive = True

        self.health = 3
        self.attacking = False
        self.attack_chain = ['attack1', 'attack2', 'attack3']
        self.attack_index = 0

    def update_animation(self):
        self.frame_timer += 1
        if self.frame_timer >= 6:
            self.frame_index = (self.frame_index + 1) % len(self.animations[self.state])
            self.frame_timer = 0
            if self.state.startswith('attack') and self.frame_index == 0:
                self.attack_index = (self.attack_index + 1) % len(self.attack_chain)
                self.state = self.attack_chain[self.attack_index]

        self.image = self.animations[self.state][self.frame_index]
        if not self.facing_right:
            self.image = pygame.transform.flip(self.image, True, False)

    def update(self, player):
        if not self.alive:
            self.state = 'die'
            self.update_animation()
            return False

        dist = abs(player.rect.centerx - self.rect.centerx)
        if dist < 100:
            self.attacking = True
            self.state = self.attack_chain[self.attack_index]
            self.speed = 0
        else:
            self.attacking = False
            self.speed = 2
            self.state = 'run'

        if not self.attacking:
            self.rect.x += self.speed
            if self.rect.x < self.range_start:
                self.rect.x = self.range_start
                self.speed *= -1
                self.facing_right = not self.facing_right
            elif self.rect.x + self.rect.width > self.range_end:
                self.rect.x = self.range_end - self.rect.width
                self.speed *= -1
                self.facing_right = not self.facing_right

        self.update_animation()
        return True

    def draw(self, surface):
        surface.blit(self.image, self.rect)
        if self.alive:
            bar_width = 40
            bar_height = 6
            health_percent = self.health / 3
            bar_x = self.rect.centerx - bar_width // 2
            bar_y = self.rect.top - 10
            pygame.draw.rect(surface, (50, 50, 50), (bar_x, bar_y, bar_width, bar_height))
            pygame.draw.rect(surface, (255, 0, 0), (bar_x, bar_y, bar_width * health_percent, bar_height))

    def kill(self):
        self.health -= 1
        if self.health <= 0:
            self.alive = False
            self.frame_index = 0
            self.frame_timer = 0

    def get_attack_rect(self):
        if self.attacking:
            offset = 40 if self.facing_right else -40
            return pygame.Rect(self.rect.centerx + offset, self.rect.y + 30, 40, 60)
        return None
