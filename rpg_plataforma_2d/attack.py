def check_attack_hit(player, enemies):
    attack_rect = player.get_attack_rect()
    if attack_rect:
        for enemy in enemies:
            if enemy.alive and attack_rect.colliderect(enemy.rect):
                enemy.kill()
