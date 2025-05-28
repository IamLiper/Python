import pygame

def load_spritesheet(path, frame_width, frame_height, num_frames):
    sheet = pygame.image.load(path).convert_alpha()
    frames = []
    for i in range(num_frames):
        frame = pygame.Surface((frame_width, frame_height), pygame.SRCALPHA)
        frame.blit(sheet, (0, 0), (i * frame_width, 0, frame_width, frame_height))
        frames.append(frame)
    return frames
