import pygame
import random
import math
import sys
from dataclasses import dataclass

# ------------- CONFIG -------------

WIDTH, HEIGHT = 900, 600
FPS = 60

PLAYER_SIZE = 40
PLAYER_ACC = 0.8
PLAYER_FRICTION = 0.85
PLAYER_MAX_SPEED = 10

OBSTACLE_MIN_SIZE = 25
OBSTACLE_MAX_SIZE = 70
OBSTACLE_BASE_SPEED = 4
OBSTACLE_SPAWN_INTERVAL = 900  # ms

ORB_SIZE = 18
ORB_SPAWN_INTERVAL = 2200  # ms

SHAKE_DECAY = 0.85
PARTICLE_COUNT_ON_HIT = 25

pygame.init()
pygame.display.set_caption("Neon Dodger")
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()
font_big = pygame.font.SysFont("consolas", 64)
font_med = pygame.font.SysFont("consolas", 32)
font_small = pygame.font.SysFont("consolas", 20)

# ------------- UTILS -------------

def draw_text(surface, text, font, color, x, y, center=True):
    img = font.render(text, True, color)
    rect = img.get_rect()
    if center:
        rect.center = (x, y)
    else:
        rect.topleft = (x, y)
    surface.blit(img, rect)

def clamp(value, min_v, max_v):
    return max(min_v, min(max_v, value))

# ------------- DATA CLASSES -------------

@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    radius: float
    life: float
    color: tuple

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt
        self.radius = max(0, self.radius - 0.03 * dt)

    def draw(self, surface):
        if self.life > 0 and self.radius > 0:
            pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), int(self.radius))

# ------------- GAME OBJECTS -------------

class Player:
    def __init__(self):
        self.reset()

    def reset(self):
        self.x = WIDTH / 2
        self.y = HEIGHT - 100
        self.vx = 0
        self.vy = 0
        self.size = PLAYER_SIZE
        self.alive = True
        self.invincible_time = 0

    def update(self, keys):
        if not self.alive:
            return

        ax = 0
        ay = 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            ax -= PLAYER_ACC
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            ax += PLAYER_ACC
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            ay -= PLAYER_ACC
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            ay += PLAYER_ACC

        self.vx += ax
        self.vy += ay

        self.vx *= PLAYER_FRICTION
        self.vy *= PLAYER_FRICTION

        speed = math.hypot(self.vx, self.vy)
        if speed > PLAYER_MAX_SPEED:
            scale = PLAYER_MAX_SPEED / speed
            self.vx *= scale
            self.vy *= scale

        self.x += self.vx
        self.y += self.vy

        self.x = clamp(self.x, self.size / 2, WIDTH - self.size / 2)
        self.y = clamp(self.y, self.size / 2, HEIGHT - self.size / 2)

        if self.invincible_time > 0:
            self.invincible_time -= 1

    def draw(self, surface, time_ms):
        flicker = 1 if self.invincible_time % 10 < 5 else 0
        base_color = (80, 220, 255)
        color = base_color if self.invincible_time == 0 or flicker else (255, 255, 255)

        angle = math.atan2(self.vy, self.vx) if (self.vx or self.vy) else -math.pi / 2
        size = self.size
        p1 = (self.x + math.cos(angle) * size,
              self.y + math.sin(angle) * size)
        p2 = (self.x + math.cos(angle + 2.5) * size * 0.7,
              self.y + math.sin(angle + 2.5) * size * 0.7)
        p3 = (self.x + math.cos(angle - 2.5) * size * 0.7,
              self.y + math.sin(angle - 2.5) * size * 0.7)

        pygame.draw.polygon(surface, color, [p1, p2, p3], width=2)

        glow_radius = int(size * 1.4 + 4 * math.sin(time_ms * 0.01))
        glow_color = (20, 120, 200, 40)
        glow_surface = pygame.Surface((glow_radius * 2, glow_radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(glow_surface, glow_color, (glow_radius, glow_radius), glow_radius)
        surface.blit(glow_surface, (self.x - glow_radius, self.y - glow_radius))

    def get_rect(self):
        return pygame.Rect(int(self.x - self.size / 2),
                           int(self.y - self.size / 2),
                           int(self.size),
                           int(self.size))

class Obstacle:
    def __init__(self, speed_multiplier):
        self.size = random.randint(OBSTACLE_MIN_SIZE, OBSTACLE_MAX_SIZE)
        self.x = random.randint(self.size, WIDTH - self.size)
        self.y = -self.size
        base_speed = OBSTACLE_BASE_SPEED + random.random() * 2
        self.vy = base_speed * speed_multiplier
        self.color = random.choice([
            (255, 80, 120),
            (255, 180, 60),
            (180, 80, 255),
            (80, 255, 160)
        ])

    def update(self):
        self.y += self.vy

    def draw(self, surface):
        rect = pygame.Rect(int(self.x - self.size / 2),
                           int(self.y - self.size / 2),
                           int(self.size),
                           int(self.size))
        pygame.draw.rect(surface, self.color, rect, border_radius=6)

    def off_screen(self):
        return self.y - self.size > HEIGHT

    def get_rect(self):
        return pygame.Rect(int(self.x - self.size / 2),
                           int(self.y - self.size / 2),
                           int(self.size),
                           int(self.size))

class Orb:
    def __init__(self):
        self.size = ORB_SIZE
        self.x = random.randint(self.size, WIDTH - self.size)
        self.y = -self.size
        self.vy = random.uniform(2.5, 4.5)
        self.color = (120, 255, 255)

    def update(self):
        self.y += self.vy

    def draw(self, surface, time_ms):
        radius = int(self.size / 2 + 2 * math.sin(time_ms * 0.02))
        glow_radius = radius + 8

        glow_surface = pygame.Surface((glow_radius * 2, glow_radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(glow_surface, (80, 200, 255, 60),
                           (glow_radius, glow_radius), glow_radius)
        surface.blit(glow_surface, (self.x - glow_radius, self.y - glow_radius))

        pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), radius)

    def off_screen(self):
        return self.y - self.size > HEIGHT

    def get_rect(self):
        return pygame.Rect(int(self.x - self.size / 2),
                           int(self.y - self.size / 2),
                           int(self.size),
                           int(self.size))

# ------------- MAIN GAME CLASS -------------

class Game:
    def __init__(self):
        self.running = True
        self.state = "menu"  # menu, playing, paused, gameover
        self.player = Player()
        self.obstacles = []
        self.orbs = []
        self.particles = []
        self.score = 0
        self.best_score = 0
        self.start_time = 0
        self.last_obstacle_spawn = 0
        self.last_orb_spawn = 0
        self.shake_strength = 0
        self.time_ms = 0

    def reset(self):
        self.player.reset()
        self.obstacles.clear()
        self.orbs.clear()
        self.particles.clear()
        self.score = 0
        self.start_time = pygame.time.get_ticks()
        self.last_obstacle_spawn = self.start_time
        self.last_orb_spawn = self.start_time
        self.shake_strength = 0

    def spawn_obstacle(self):
        elapsed = (self.time_ms - self.start_time) / 1000
        speed_multiplier = 1 + elapsed * 0.05
        self.obstacles.append(Obstacle(speed_multiplier))

    def spawn_orb(self):
        self.orbs.append(Orb())

    def add_particles(self, x, y, color, count=PARTICLE_COUNT_ON_HIT):
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(2, 10)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            radius = random.uniform(2, 5)
            life = random.uniform(15, 35)
            self.particles.append(Particle(x, y, vx, vy, radius, life, color))

    def update_particles(self):
        dt = 1
        for p in self.particles:
            p.update(dt)
        self.particles = [p for p in self.particles if p.life > 0 and p.radius > 0]

    def apply_screen_shake(self):
        if self.shake_strength <= 0:
            return 0, 0
        offset_x = random.uniform(-self.shake_strength, self.shake_strength)
        offset_y = random.uniform(-self.shake_strength, self.shake_strength)
        self.shake_strength *= SHAKE_DECAY
        if self.shake_strength < 0.5:
            self.shake_strength = 0
        return int(offset_x), int(offset_y)

    def handle_collisions(self):
        if not self.player.alive:
            return

        player_rect = self.player.get_rect()

        for obs in self.obstacles:
            if player_rect.colliderect(obs.get_rect()):
                if self.player.invincible_time <= 0:
                    self.player.alive = False
                    self.shake_strength = 20
                    self.add_particles(self.player.x, self.player.y, (255, 80, 120))
                    break

        for orb in self.orbs[:]:
            if player_rect.colliderect(orb.get_rect()):
                self.score += 50
                self.player.invincible_time = 60
                self.shake_strength = 8
                self.add_particles(orb.x, orb.y, (120, 255, 255), count=18)
                self.orbs.remove(orb)

    def update_score(self):
        if self.state == "playing" and self.player.alive:
            elapsed = (self.time_ms - self.start_time) / 1000
            self.score += int(elapsed * 10)
            self.start_time = self.time_ms

    def update(self):
        self.time_ms = pygame.time.get_ticks()
        keys = pygame.key.get_pressed()

        if self.state in ("menu", "paused", "gameover"):
            return

        self.player.update(keys)

        if self.time_ms - self.last_obstacle_spawn > OBSTACLE_SPAWN_INTERVAL:
            self.spawn_obstacle()
            self.last_obstacle_spawn = self.time_ms

        if self.time_ms - self.last_orb_spawn > ORB_SPAWN_INTERVAL:
            self.spawn_orb()
            self.last_orb_spawn = self.time_ms

        for obs in self.obstacles:
            obs.update()
        self.obstacles = [o for o in self.obstacles if not o.off_screen()]

        for orb in self.orbs:
            orb.update()
        self.orbs = [o for o in self.orbs if not o.off_screen()]

        self.handle_collisions()
        self.update_particles()

        if self.player.alive:
            self.update_score()
        else:
            if self.state == "playing":
                self.state = "gameover"
                self.best_score = max(self.best_score, self.score)

    def draw_background(self):
        for i in range(0, HEIGHT, 4):
            t = i / HEIGHT
            r = int(10 + 40 * t)
            g = int(10 + 20 * t)
            b = int(30 + 80 * t)
            pygame.draw.rect(screen, (r, g, b), (0, i, WIDTH, 4))

        grid_color = (40, 80, 120)
        spacing = 60
        offset = (self.time_ms // 10) % spacing

        for x in range(-spacing, WIDTH + spacing, spacing):
            pygame.draw.line(screen, grid_color,
                             (x + offset, 0),
                             (x - HEIGHT + offset, HEIGHT), 1)

        for y in range(0, HEIGHT, spacing):
            pygame.draw.line(screen, grid_color,
                             (0, y + offset),
                             (WIDTH, y + offset), 1)

    def draw_hud(self):
        draw_text(screen, f"Score: {self.score}", font_small, (220, 240, 255), 10, 10, center=False)
        draw_text(screen, f"Best: {self.best_score}", font_small, (180, 200, 220), 10, 35, center=False)
        draw_text(screen, "WASD / Arrows to move  |  P: Pause", font_small, (150, 180, 210),
                  WIDTH - 10, 10, center=False)

    def draw_menu(self):
        draw_text(screen, "NEON DODGER", font_big, (120, 230, 255), WIDTH // 2, HEIGHT // 2 - 80)
        draw_text(screen, "Move with WASD or Arrow Keys", font_med, (200, 220, 255),
                  WIDTH // 2, HEIGHT // 2)
        draw_text(screen, "Collect orbs, dodge everything else", font_med, (200, 220, 255),
                  WIDTH // 2, HEIGHT // 2 + 40)
        draw_text(screen, "Press ENTER to start", font_med, (255, 255, 255),
                  WIDTH // 2, HEIGHT // 2 + 110)

    def draw_paused(self):
        draw_text(screen, "PAUSED", font_big, (255, 255, 255), WIDTH // 2, HEIGHT // 2 - 40)
        draw_text(screen, "Press P to resume", font_med, (200, 220, 255),
                  WIDTH // 2, HEIGHT // 2 + 20)
        draw_text(screen, "Press ESC to quit", font_small, (180, 200, 220),
                  WIDTH // 2, HEIGHT // 2 + 60)

    def draw_gameover(self):
        draw_text(screen, "GAME OVER", font_big, (255, 120, 160), WIDTH // 2, HEIGHT // 2 - 80)
        draw_text(screen, f"Score: {self.score}", font_med, (220, 240, 255),
                  WIDTH // 2, HEIGHT // 2 - 10)
        draw_text(screen, f"Best: {self.best_score}", font_med, (200, 220, 255),
                  WIDTH // 2, HEIGHT // 2 + 30)
        draw_text(screen, "Press ENTER to play again", font_med, (255, 255, 255),
                  WIDTH // 2, HEIGHT // 2 + 100)
        draw_text(screen, "Press ESC to quit", font_small, (180, 200, 220),
                  WIDTH // 2, HEIGHT // 2 + 140)

    def draw(self):
        self.draw_background()
        offset_x, offset_y = self.apply_screen_shake()

        temp_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)

        for obs in self.obstacles:
            obs.draw(temp_surface)
        for orb in self.orbs:
            orb.draw(temp_surface, self.time_ms)
        self.player.draw(temp_surface, self.time_ms)
        for p in self.particles:
            p.draw(temp_surface)

        screen.blit(temp_surface, (offset_x, offset_y))

        if self.state == "playing":
            self.draw_hud()
        elif self.state == "menu":
            self.draw_menu()
        elif self.state == "paused":
            self.draw_hud()
            self.draw_paused()
        elif self.state == "gameover":
            self.draw_hud()
            self.draw_gameover()

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self.state == "playing":
                        self.state = "paused"
                    elif self.state in ("paused", "menu", "gameover"):
                        self.running = False

                if event.key == pygame.K_p:
                    if self.state == "playing":
                        self.state = "paused"
                    elif self.state == "paused":
                        self.state = "playing"

                if event.key == pygame.K_RETURN:
                    if self.state in ("menu", "gameover"):
                        self.reset()
                        self.state = "playing"

    def run(self):
        while self.running:
            dt = clock.tick(FPS)
            self.handle_events()
            self.update()
            self.draw()
            pygame.display.flip()

        pygame.quit()
        sys.exit()

# ------------- MAIN -------------

if __name__ == "__main__":
    Game().run()
