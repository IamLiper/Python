import pygame
from config import *
from utils import load_spritesheet

class Player:
    def __init__(self):
        self.animations = {
            'idle': load_spritesheet('assets/images/player/idle.png', 128, 128, 6),
            'run': load_spritesheet('assets/images/player/run.png', 128, 128, 8),
            'jump': load_spritesheet('assets/images/player/jump.png', 128, 128, 12),
            'attack1': load_spritesheet('assets/images/player/attack1.png', 128, 128, 6),
            'attack2': load_spritesheet('assets/images/player/attack2.png', 128, 128, 4),
            'attack3': load_spritesheet('assets/images/player/attack3.png', 128, 128, 3),
            'die': load_spritesheet('assets/images/player/die.png', 128, 128, 3)
        }
        self.state = 'idle'
        self.last_state = 'idle'
        self.frame_index = 0
        self.frame_timer = 0
        self.image = self.animations[self.state][self.frame_index]
        self.rect = self.image.get_rect(topleft=(100, SCREEN_HEIGHT - GROUND_HEIGHT - 128))

        self.speed = PLAYER_SPEED
        self.vel_y = 0
        self.on_ground = False
        self.health = PLAYER_MAX_HEALTH
        self.score = 0
        self.facing_right = True

        self.attack_chain = ['attack1', 'attack2', 'attack3']
        self.attack_index = 0
        self.attack_cooldown = 0
        self.attack_ready = True

    def handle_input(self, attack_pressed=False):
        keys = pygame.key.get_pressed()
        moving = False

        if keys[pygame.K_LEFT]:
            self.rect.x -= self.speed
            self.facing_right = False
            moving = True
        if keys[pygame.K_RIGHT]:
            self.rect.x += self.speed
            self.facing_right = True
            moving = True
        if keys[pygame.K_UP] and self.on_ground:
            self.vel_y = -JUMP_STRENGTH
            self.on_ground = False
        if attack_pressed and self.attack_cooldown <= 0 and self.attack_ready:
            self.state = self.attack_chain[self.attack_index]
            self.attack_cooldown = 10
            self.attack_index = (self.attack_index + 1) % len(self.attack_chain)
            self.attack_ready = False

        if not keys[pygame.K_SPACE]:
            self.attack_ready = True

        if not self.on_ground:
            self.state = 'jump'
        elif self.attack_cooldown > 0:
            pass
        elif moving:
            self.state = 'run'
        else:
            self.state = 'idle'

    def apply_gravity(self):
        self.vel_y += GRAVITY
        self.rect.y += self.vel_y

        ground_y = SCREEN_HEIGHT - GROUND_HEIGHT - 128
        if self.rect.y >= ground_y:
            self.rect.y = ground_y
            self.vel_y = 0
            self.on_ground = True
        else:
            self.on_ground = False

    def update_animation(self):
        self.frame_timer += 1
        if self.frame_timer >= 6:
            self.frame_index = (self.frame_index + 1) % len(self.animations[self.state])
            self.frame_timer = 0

    def update(self, attack_pressed=False):
        if self.health <= 0:
            self.state = 'die'
        else:
            self.handle_input(attack_pressed)

        if self.state != self.last_state:
            self.frame_index = 0
            self.frame_timer = 0
            self.last_state = self.state

        self.apply_gravity()
        self.update_animation()
        self.image = self.animations[self.state][self.frame_index]
        if not self.facing_right:
            self.image = pygame.transform.flip(self.image, True, False)

        self.rect.x = max(0, min(self.rect.x, SCREEN_WIDTH - 128))
        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1

    def draw(self, surface):
        surface.blit(self.image, self.rect)

    def get_attack_rect(self):
        if self.state.startswith('attack'):
            offset = 40 if self.facing_right else -40
            return pygame.Rect(self.rect.centerx + offset, self.rect.y + 30, 30, 60)
        return None
