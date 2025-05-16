from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController
import random
import json
import os

app = Ursina()

# === ENVIRONMENT ===
ground = Entity(model='plane', scale=Vec3(100, 1, 100), texture='grass', texture_scale=(50, 50), collider='box')
for i in range(-5, 6, 2):
    for j in range(-5, 6, 2):
        height = random.uniform(2, 8)
        Entity(model='cube', position=Vec3(i, height/2, j), scale=Vec3(1, height, 1),
               texture='brick', collider='box')
Sky()
sun = DirectionalLight(shadows=True)
sun.look_at(Vec3(1, -1, -1))
sun.color = color.rgb(255, 244, 214)
AmbientLight(color=color.rgba(100, 100, 100, 0.5))

# === PLAYER ===
player = Entity(model='cube', scale_y=2, color=color.red, collider='box', position=Vec3(0, 1, 0))
velocity = Vec3(0, 0, 0)
gravity = -9.8
on_ground = True
energy = 100
max_energy = 100
health = 100

# === CAMERA ===
camera_mode = 'third_person'
def set_camera(mode):
    global camera_mode
    camera_mode = mode
    camera.parent = player
    if mode == 'first_person':
        camera.position = Vec3(0, 1.6, 0)
        camera.rotation = Vec3(0, 0, 0)
        camera.fov = 90
    else:
        camera.position = Vec3(0, 3, -8)
        camera.rotation = Vec3(10, 0, 0)
        camera.fov = 75
set_camera(camera_mode)

# === HUD ===
health_bar = Entity(parent=camera.ui, model='quad', color=color.red, scale=(0.4, 0.03), position=(-0.5, 0.45))
energy_bar = Entity(parent=camera.ui, model='quad', color=color.cyan, scale=(0.4, 0.03), position=(-0.5, 0.40))
crosshair = Entity(parent=camera.ui, model='quad', color=color.white, scale=(0.01, 0.01))

# === FERRIS WHEEL ===
ferris_wheels = []
for pos in [Vec3(10, 0, 10), Vec3(-10, 0, -10)]:
    wheel = Entity(model='torus', color=color.azure, scale=3, position=pos)
    ferris_wheels.append(wheel)

# === CHECKPOINT ===
def create_checkpoint(pos):
    cp = Entity(model='cube', color=color.orange, scale=1.5, position=pos, collider='box')
    cp.tag = 'checkpoint'
    checkpoints.append(cp)
checkpoints = []
create_checkpoint(Vec3(5,1,5))

# === POWER-UP ===
powerups = []
def create_powerup(pos):
    p = Entity(model='cube', color=color.yellow, scale=0.5, position=pos, collider='box', tag='powerup')
    powerups.append(p)
create_powerup(Vec3(3,1,3))
create_powerup(Vec3(-3,1,-4))

# === DRONES ===
class Drone(Entity):
    def __init__(self, position):
        super().__init__(model='cube', color=color.green, position=position, scale=1, collider='box')
        self.speed = 2
    def update(self):
        if distance(self.position, player.position) < 15:
            self.look_at(player.position)
            self.position += self.forward * self.speed * time.dt
drones = [Drone(Vec3(10,3,10)), Drone(Vec3(-8,5,-6))]

# === SHOOTING ===
bullets = []
shoot_sound = Audio('shoot.wav', autoplay=False)
def shoot():
    direction = camera.forward
    bullet = Entity(model='sphere', color=color.cyan, scale=0.2, position=player.position + direction * 1.5)
    bullet.collider = 'box'
    bullet.direction = direction
    bullet.speed = 20
    bullet.lifetime = 2
    bullets.append(bullet)
    shoot_sound.play()

# === PARTICLE EFFECT ===
particles = []
def create_jet_flame():
    flame = Entity(model='sphere', color=color.orange, scale=0.3, position=player.position + Vec3(0, -1, 0), duration=0.2)
    flame.fade_out(duration=0.2)
    particles.append(flame)

# === BOSS BATTLE ===
boss = Entity(model='cube', color=color.violet, scale=Vec3(3,3,3), position=Vec3(20,3,20), collider='box')
boss_health = 200
boss_bar = Entity(parent=camera.ui, model='quad', color=color.magenta, scale=(0.6, 0.03), position=(-0.5, 0.5))

# === SAVE/LOAD ===
def save_game():
    with open('save.json', 'w') as f:
        json.dump({'position': list(player.position)}, f)

def load_game():
    if os.path.exists('save.json'):
        with open('save.json', 'r') as f:
            data = json.load(f)
            player.position = Vec3(*data['position'])

# === MENU ===
def toggle_menu():
    application.pause() if not application.paused else application.resume()
    menu.enabled = not menu.enabled
menu = Entity(enabled=False, parent=camera.ui)
Text(parent=menu, text='PAUSED\nPress ESC to Resume', origin=(0,0), scale=2)

# === INPUT ===
def input(key):
    if key == 'c':
        new_mode = 'first_person' if camera_mode == 'third_person' else 'third_person'
        set_camera(new_mode)
    if key == 'left mouse down':
        shoot()
    if key == 'escape':
        toggle_menu()
    if key == 'f5':
        save_game()
    if key == 'f9':
        load_game()

# === UPDATE ===
def update():
    global velocity, energy, on_ground, health, boss_health

    direction = Vec3(held_keys['d'] - held_keys['a'], 0, held_keys['w'] - held_keys['s']).normalized()
    boost = held_keys['shift'] * 2
    flight = held_keys['space'] and energy > 0
    speed = 5 + boost

    if not on_ground:
        velocity.y += gravity * time.dt

    if flight:
        velocity.y = 5
        energy -= 20 * time.dt
        create_jet_flame()
        on_ground = False
    else:
        if player.y > 1.01:
            on_ground = False
        else:
            velocity.y = 0
            on_ground = True
            energy = min(max_energy, energy + 10 * time.dt)

    player.position += direction * speed * time.dt
    player.y += velocity.y * time.dt
    if player.y < 1:
        player.y = 1
        velocity.y = 0
        on_ground = True

    for wheel in ferris_wheels:
        wheel.rotation_z += 10 * time.dt

    for b in bullets:
        b.position += b.direction * b.speed * time.dt
        b.lifetime -= time.dt
        if b.lifetime <= 0:
            destroy(b)
        for d in drones:
            if b.intersects(d).hit:
                explosion = Entity(model='sphere', scale=1, color=color.orange, position=d.position)
                destroy(b)
                destroy(d)
                invoke(destroy, explosion, delay=0.5)
        if b.intersects(boss).hit:
            boss_health -= 10
            destroy(b)
            if boss_health <= 0:
                Text(text='Boss Defeated!', origin=(0,0), color=color.violet, position=(0.4,0.55), duration=2)
                destroy(boss)

    for d in drones:
        d.update()

    for p in powerups:
        if player.intersects(p).hit:
            health = min(100, health + 10)
            Text(text='+10 HP', origin=(0,0), color=color.lime, position=(0.4,0.4), duration=1)
            destroy(p)

    for cp in checkpoints:
        if player.intersects(cp).hit:
            Text(text='Checkpoint!', origin=(0,0), color=color.azure, position=(0.4,0.5), duration=1)

    health_bar.scale_x = 0.4 * (health / 100)
    energy_bar.scale_x = 0.4 * (energy / max_energy)
    boss_bar.scale_x = 0.6 * (boss_health / 200)

app.run()
