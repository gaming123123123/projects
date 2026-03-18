import pygame
import sys
import random
import math

# ---------------- CONFIG ----------------

WIDTH, HEIGHT = 960, 540
FPS = 60

GRAVITY = 0.6
JUMP_FORCE = -12
PLAYER_SPEED = 5

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Neon Platformer")
clock = pygame.time.Clock()

font_big = pygame.font.SysFont("consolas", 48)
font_med = pygame.font.SysFont("consolas", 28)
font_small = pygame.font.SysFont("consolas", 18)

# ---------------- UTILS ----------------

def draw_text(text, font, color, x, y, center=True):
    img = font.render(text, True, color)
    rect = img.get_rect()
    if center:
        rect.center = (x, y)
    else:
        rect.topleft = (x, y)
    screen.blit(img, rect)

# ---------------- CAMERA ----------------

class Camera:
    def __init__(self):
        self.offset_x = 0

    def apply(self, rect):
        return rect.move(-self.offset_x, 0)

    def update(self, target_rect):
        self.offset_x = target_rect.centerx - WIDTH // 2
        self.offset_x = max(0, self.offset_x)

# ---------------- PLAYER ----------------

class Player(pygame.sprite.Sprite):
    def __init__(self, x, y, platforms, enemies, coins, goal_rect):
        super().__init__()
        self.image = pygame.Surface((40, 60), pygame.SRCALPHA)
        pygame.draw.rect(self.image, (80, 220, 255), (0, 0, 40, 60), border_radius=8)
        self.rect = self.image.get_rect(topleft=(x, y))

        self.vx = 0
        self.vy = 0
        self.on_ground = False

        self.platforms = platforms
        self.enemies = enemies
        self.coins = coins
        self.goal_rect = goal_rect

        self.alive = True
        self.won = False
        self.score = 0
        self.invincible_timer = 0

    def handle_input(self, keys):
        self.vx = 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.vx = -PLAYER_SPEED
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.vx = PLAYER_SPEED

        if (keys[pygame.K_SPACE] or keys[pygame.K_UP] or keys[pygame.K_w]) and self.on_ground:
            self.vy = JUMP_FORCE
            self.on_ground = False

    def apply_gravity(self):
        self.vy += GRAVITY
        if self.vy > 20:
            self.vy = 20

    def move_and_collide(self):
        # Horizontal
        self.rect.x += self.vx
        for p in self.platforms:
            if self.rect.colliderect(p.rect):
                if self.vx > 0:
                    self.rect.right = p.rect.left
                elif self.vx < 0:
                    self.rect.left = p.rect.right

        # Vertical
        self.rect.y += self.vy
        self.on_ground = False
        for p in self.platforms:
            if self.rect.colliderect(p.rect):
                if self.vy > 0:
                    self.rect.bottom = p.rect.top
                    self.vy = 0
                    self.on_ground = True
                elif self.vy < 0:
                    self.rect.top = p.rect.bottom
                    self.vy = 0

    def check_enemies(self):
        if self.invincible_timer > 0:
            self.invincible_timer -= 1
            return

        for e in self.enemies:
            if self.rect.colliderect(e.rect):
                # Stomp enemy
                if self.vy > 0 and self.rect.bottom - e.rect.top < 20:
                    e.kill()
                    self.vy = JUMP_FORCE * 0.7
                    self.score += 100
                    self.invincible_timer = 20
                else:
                    self.alive = False

    def check_coins(self):
        for c in self.coins:
            if self.rect.colliderect(c.rect):
                self.score += 10
                c.kill()

    def check_goal(self):
        if self.rect.colliderect(self.goal_rect):
            self.won = True

    def update(self, keys):
        if not self.alive or self.won:
            return

        self.handle_input(keys)
        self.apply_gravity()
        self.move_and_collide()
        self.check_enemies()
        self.check_coins()
        self.check_goal()

    def draw(self, camera):
        img = pygame.Surface((40, 60), pygame.SRCALPHA)

        # Flicker when invincible
        color = (255, 255, 255) if self.invincible_timer > 0 and self.invincible_timer % 4 < 2 else (80, 220, 255)
        pygame.draw.rect(img, color, (0, 0, 40, 60), border_radius=8)

        # Simple face
        pygame.draw.rect(img, (0, 0, 0), (10, 15, 6, 8), border_radius=3)
        pygame.draw.rect(img, (0, 0, 0), (24, 15, 6, 8), border_radius=3)
        pygame.draw.rect(img, (0, 0, 0), (12, 35, 16, 4), border_radius=2)

        screen.blit(img, camera.apply(self.rect))

# ---------------- PLATFORMS ----------------

class Platform(pygame.sprite.Sprite):
    def __init__(self, x, y, w, h, color=(40, 40, 80)):
        super().__init__()
        self.image = pygame.Surface((w, h))
        self.image.fill(color)
        self.rect = self.image.get_rect(topleft=(x, y))

    def draw(self, camera):
        screen.blit(self.image, camera.apply(self.rect))

class MovingPlatform(Platform):
    def __init__(self, x, y, w, h, dx=0, dy=0, distance=100, speed=2, color=(60, 100, 140)):
        super().__init__(x, y, w, h, color)
        self.start_x = x
        self.start_y = y
        self.dx = dx
        self.dy = dy
        self.distance = distance
        self.speed = speed
        self.t = 0

    def update(self):
        self.t += self.speed
        offset = (self.t % (2 * self.distance))
        if offset > self.distance:
            offset = 2 * self.distance - offset

        self.rect.x = self.start_x + self.dx * offset
        self.rect.y = self.start_y + self.dy * offset

# ---------------- ENEMY ----------------

class Enemy(pygame.sprite.Sprite):
    def __init__(self, x, y, patrol_width=120):
        super().__init__()
        self.image = pygame.Surface((40, 40), pygame.SRCALPHA)
        pygame.draw.rect(self.image, (255, 80, 120), (0, 0, 40, 40), border_radius=8)
        pygame.draw.rect(self.image, (0, 0, 0), (10, 10, 6, 6), border_radius=3)
        pygame.draw.rect(self.image, (0, 0, 0), (24, 10, 6, 6), border_radius=3)
        pygame.draw.rect(self.image, (0, 0, 0), (10, 26, 20, 4), border_radius=2)

        self.rect = self.image.get_rect(topleft=(x, y))
        self.start_x = x
        self.patrol_width = patrol_width
        self.vx = 2

    def update(self):
        self.rect.x += self.vx
        if self.rect.x < self.start_x or self.rect.x > self.start_x + self.patrol_width:
            self.vx *= -1

    def draw(self, camera):
        screen.blit(self.image, camera.apply(self.rect))

# ---------------- COIN ----------------

class Coin(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.rect = pygame.Rect(x, y, 20, 20)
        self.t = random.randint(0, 1000)

    def update(self):
        self.t += 1

    def draw(self, camera):
        r = int(10 + 2 * (1 + math.sin(self.t * 0.1)))
        pos = camera.apply(self.rect).center
        pygame.draw.circle(screen, (255, 220, 80), pos, r)
        pygame.draw.circle(screen, (255, 255, 255), pos, max(2, r // 3), 2)

# ---------------- LEVEL CREATION ----------------

def create_level():
    platforms = pygame.sprite.Group()
    moving_platforms = pygame.sprite.Group()
    enemies = pygame.sprite.Group()
    coins = pygame.sprite.Group()

    # Ground
    platforms.add(Platform(0, HEIGHT - 40, 2000, 40, (30, 30, 60)))

    # Static platforms
    platforms.add(Platform(200, 400, 200, 20))
    platforms.add(Platform(500, 340, 180, 20))
    platforms.add(Platform(800, 280, 200, 20))
    platforms.add(Platform(1150, 360, 200, 20))
    platforms.add(Platform(1450, 300, 200, 20))

    # Moving platforms
    mp1 = MovingPlatform(400, 250, 120, 20, dx=1, dy=0, distance=150, speed=1.5)
    mp2 = MovingPlatform(1000, 200, 120, 20, dx=0, dy=1, distance=80, speed=1.8)
    moving_platforms.add(mp1, mp2)
    platforms.add(mp1, mp2)

    # Enemies
    enemies.add(Enemy(260, 360, patrol_width=120))
    enemies.add(Enemy(540, 300, patrol_width=80))
    enemies.add(Enemy(1180, 320, patrol_width=100))
    enemies.add(Enemy(1500, 260, patrol_width=100))

    # Coins
    for x, y in [(230,360),(320,360),(560,300),(860,240),(1040,160),(1180,320),(1500,260),(1600,260)]:
        coins.add(Coin(x, y))

    # Goal
    goal_rect = pygame.Rect(1800, HEIGHT - 120, 80, 80)

    return platforms, moving_platforms, enemies, coins, goal_rect

# ---------------- MAIN LOOP ----------------

def main():
    camera = Camera()
    platforms, moving_platforms, enemies, coins, goal_rect = create_level()
    player = Player(80, HEIGHT - 120, platforms, enemies, coins, goal_rect)

    state = "menu"
    running = True

    while running:
        dt = clock.tick(FPS)
        keys = pygame.key.get_pressed()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

                if event.key == pygame.K_RETURN:
                    if state in ("menu", "gameover", "win"):
                        platforms, moving_platforms, enemies, coins, goal_rect = create_level()
                        player = Player(80, HEIGHT - 120, platforms, enemies, coins, goal_rect)
                        state = "playing"

        # Update
        if state == "playing":
            player.update(keys)
            for mp in moving_platforms:
                mp.update()
            for e in enemies:
                e.update()
            for c in coins:
                c.update()

            camera.update(player.rect)

            if not player.alive:
                state = "gameover"
            if player.won:
                state = "win"

        # Draw background
        screen.fill((10, 10, 25))
        for i in range(0, HEIGHT, 4):
            t = i / HEIGHT
            pygame.draw.rect(screen, (10, int(10 + 40 * t), int(40 + 80 * t)), (0, i, WIDTH, 4))

        # Parallax stars
        for i in range(40):
            x = (i * 120 + (pygame.time.get_ticks() // 10)) % (WIDTH + 200) - 100
            y = (i * 37) % HEIGHT
            pygame.draw.circle(screen, (80, 120, 200), (x, y), 2)

        # Draw goal
        pygame.draw.rect(screen, (60, 10, 90), camera.apply(goal_rect))
        pygame.draw.rect(screen, (180, 80, 255), camera.apply(goal_rect).inflate(-10, -10), 3)

        # Draw objects
        for p in platforms:
            p.draw(camera)
        for e in enemies:
            e.draw(camera)
        for c in coins:
            c.draw(camera)
        player.draw(camera)

        # HUD
        draw_text(f"Score: {player.score}", font_small, (220, 240, 255), 10, 10, center=False)

        # State overlays
        if state == "menu":
            draw_text("NEON PLATFORMER", font_big, (120, 230, 255), WIDTH // 2, HEIGHT // 2 - 60)
            draw_text("Reach the portal on the far right", font_med, (220, 240, 255), WIDTH // 2, HEIGHT // 2)
            draw_text("Press ENTER to start", font_med, (255, 255, 255), WIDTH // 2, HEIGHT // 2 + 60)

        elif state == "gameover":
            draw_text("GAME OVER", font_big, (255, 120, 160), WIDTH // 2, HEIGHT // 2 - 60)
            draw_text(f"Score: {player.score}", font_med, (220, 240, 255), WIDTH // 2, HEIGHT // 2)
            draw_text("Press ENTER to try again", font_med, (255, 255, 255), WIDTH // 2, HEIGHT // 2 + 60)

        elif state == "win":
            draw_text("YOU WIN!", font_big, (120, 255, 180), WIDTH // 2, HEIGHT // 2 - 60)
            draw_text(f"Final Score: {player.score}", font_med, (220, 240, 255), WIDTH // 2, HEIGHT // 2)
            draw_text("Press ENTER to play again", font_med, (255, 255, 255), WIDTH // 2, HEIGHT // 2 + 60)

        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
