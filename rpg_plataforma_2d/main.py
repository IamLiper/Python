import pygame
from config import *
from player import Player
from enemy import Enemy
from item import Item
from level import draw_ground
from attack import check_attack_hit

pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("RPG Plataforma 2D")
clock = pygame.time.Clock()

player = Player()
enemies = [Enemy(400, SCREEN_HEIGHT - GROUND_HEIGHT - 128, 400, 600)]
items = [Item(300, SCREEN_HEIGHT - GROUND_HEIGHT - 30)]

running = True
while running:
    attack_pressed = False

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
            attack_pressed = True

    player.update(attack_pressed)
    check_attack_hit(player, enemies)

    alive_enemies = []
    for enemy in enemies:
        if enemy.update(player):
            alive_enemies.append(enemy)

        attack_rect = enemy.get_attack_rect()
        if attack_rect and attack_rect.colliderect(player.rect):
            player.health -= 1
            if player.health <= 0:
                print("💀 GAME OVER")
                running = False
    enemies = alive_enemies

    for item in items:
        item.check_collision(player)

    screen.fill(BACKGROUND_COLOR)
    draw_ground(screen)
    player.draw(screen)
    for enemy in enemies:
        enemy.draw(screen)
    for item in items:
        item.draw(screen)

    font = pygame.font.SysFont(None, 24)
    hud = font.render(f"Vida: {player.health}  Pontos: {player.score}", True, (255, 255, 255))
    screen.blit(hud, (10, 10))

    pygame.display.flip()
    clock.tick(FPS)

pygame.quit()
