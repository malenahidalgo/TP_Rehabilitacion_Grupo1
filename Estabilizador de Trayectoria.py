import pygame
import sys
import math
import time
import csv
import os
from datetime import datetime

pygame.init()
pygame.mixer.init()

# -------- CONFIG --------
WIDTH, HEIGHT = 960, 640
FPS = 60

# Paleta clínica — limpia y clara
C_BG         = (235, 240, 245)
C_TRACK_OUT  = ( 80,  90, 100)   # borde oscuro del camino
C_TRACK_MID  = (255, 255, 255)   # interior blanco
C_TRACK_IN   = (210, 225, 240)   # relleno suave azulado
C_START      = ( 40, 180,  80)
C_END        = (210,  60,  60)
C_CURSOR_OK  = ( 50, 140, 220)
C_CURSOR_ERR = (220,  60,  60)
C_TEXT       = ( 30,  40,  50)
C_PANEL      = (255, 255, 255)
C_SHADOW     = (180, 190, 200)
C_ACCENT     = ( 50, 130, 210)

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Test de Control de Trayectoria")
clock = pygame.time.Clock()

font_lg = pygame.font.SysFont("Segoe UI", 36, bold=True)
font_md = pygame.font.SysFont("Segoe UI", 26)
font_sm = pygame.font.SysFont("Segoe UI", 20)

# -------- SONIDO (opcional) --------
try:
    success_sound = pygame.mixer.Sound("success.wav.mp3")
except Exception:
    success_sound = None


# -------- GEOMETRÍA --------
def dist_to_segment(p, a, b):
    px, py = p
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    if dx == dy == 0:
        return math.dist(p, a)
    t = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)
    t = max(0, min(1, t))
    return math.dist(p, (ax + t * dx, ay + t * dy))


# -------- DIBUJO DEL CAMINO --------
def draw_path_pro(surface, path, half_w):
    """Dibuja el camino con relleno, borde y sombra de calidad."""
    if len(path) < 2:
        return

    # --- Sombra (desplazada hacia abajo) ---
    shadow_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    shadow_pts_top = []
    shadow_pts_bot = []
    for i in range(len(path)):
        if i == 0:
            dx, dy = path[1][0] - path[0][0], path[1][1] - path[0][1]
        elif i == len(path) - 1:
            dx, dy = path[-1][0] - path[-2][0], path[-1][1] - path[-2][1]
        else:
            dx, dy = path[i+1][0] - path[i-1][0], path[i+1][1] - path[i-1][1]
        length = math.hypot(dx, dy) or 1
        nx, ny = -dy / length, dx / length
        ox, oy = path[i]
        shadow_pts_top.append((ox + nx * half_w + 4, oy + ny * half_w + 6))
        shadow_pts_bot.append((ox - nx * half_w + 4, oy - ny * half_w + 6))

    shadow_poly = shadow_pts_top + list(reversed(shadow_pts_bot))
    if len(shadow_poly) > 2:
        pygame.draw.polygon(shadow_surf, (160, 170, 180, 80), shadow_poly)
    surface.blit(shadow_surf, (0, 0))

    # --- Polígono principal (borde + relleno) ---
    pts_top = []
    pts_bot = []
    for i in range(len(path)):
        if i == 0:
            dx, dy = path[1][0] - path[0][0], path[1][1] - path[0][1]
        elif i == len(path) - 1:
            dx, dy = path[-1][0] - path[-2][0], path[-1][1] - path[-2][1]
        else:
            dx, dy = path[i+1][0] - path[i-1][0], path[i+1][1] - path[i-1][1]
        length = math.hypot(dx, dy) or 1
        nx, ny = -dy / length, dx / length
        ox, oy = path[i]
        pts_top.append((ox + nx * half_w, oy + ny * half_w))
        pts_bot.append((ox - nx * half_w, oy - ny * half_w))

    poly = pts_top + list(reversed(pts_bot))

    if len(poly) > 2:
        # Borde exterior oscuro
        pygame.draw.polygon(surface, C_TRACK_OUT, poly)
        # Borde interior (inset 4px)
        inner_top = [(x + 4 * (pts_bot[i][0] - pts_top[i][0]) / (half_w * 2),
                      y + 4 * (pts_bot[i][1] - pts_top[i][1]) / (half_w * 2))
                     for i, (x, y) in enumerate(pts_top)]
        inner_bot = [(x + 4 * (pts_top[i][0] - pts_bot[i][0]) / (half_w * 2),
                      y + 4 * (pts_top[i][1] - pts_bot[i][1]) / (half_w * 2))
                     for i, (x, y) in enumerate(pts_bot)]
        inner_poly = inner_top + list(reversed(inner_bot))
        pygame.draw.polygon(surface, C_TRACK_MID, inner_poly)

        # Relleno interior suave
        inner2_top = [(x + 10 * (pts_bot[i][0] - pts_top[i][0]) / (half_w * 2),
                       y + 10 * (pts_bot[i][1] - pts_top[i][1]) / (half_w * 2))
                      for i, (x, y) in enumerate(pts_top)]
        inner2_bot = [(x + 10 * (pts_top[i][0] - pts_bot[i][0]) / (half_w * 2),
                       y + 10 * (pts_top[i][1] - pts_bot[i][1]) / (half_w * 2))
                      for i, (x, y) in enumerate(pts_bot)]
        inner2_poly = inner2_top + list(reversed(inner2_bot))
        pygame.draw.polygon(surface, C_TRACK_IN, inner2_poly)

    # Línea central punteada (referencia)
    for i in range(0, len(path) - 1, 12):
        pygame.draw.line(surface, (180, 200, 220), path[i], path[min(i + 6, len(path)-1)], 1)


# -------- PANEL HUD --------
def draw_hud(surface, level, errors, elapsed, inside):
    panel_w, panel_h = 200, 110
    px, py = 16, 16
    # sombra
    pygame.draw.rect(surface, C_SHADOW, (px+3, py+3, panel_w, panel_h), border_radius=12)
    # panel
    pygame.draw.rect(surface, C_PANEL, (px, py, panel_w, panel_h), border_radius=12)
    pygame.draw.rect(surface, C_ACCENT, (px, py, panel_w, panel_h), 2, border_radius=12)

    surface.blit(font_md.render(f"Nivel  {level}", True, C_ACCENT), (px+14, py+10))
    surface.blit(font_sm.render(f"Errores:  {errors}", True, C_TEXT), (px+14, py+44))
    surface.blit(font_sm.render(f"Tiempo:  {elapsed:.1f} s", True, C_TEXT), (px+14, py+68))

    estado_txt = "✓ Dentro" if inside else "✗ Fuera"
    estado_col = C_START if inside else C_END
    surface.blit(font_sm.render(estado_txt, True, estado_col), (px+14, py+90))


# -------- PANTALLA DE INTRO --------
def draw_intro(level_num, total):
    screen.fill(C_BG)
    titles = ["Nivel 1", "Nivel 2", "Nivel 3"]
    descs  = [
        "Seguí el camino con el mouse\ndesde el punto verde hasta el rojo.",
        "El camino es más sinuoso.\nMantené el cursor dentro.",
        "Trayectoria irregular.\nConcentrate en la precisión.",
    ]
    idx = level_num - 1

    # Tarjeta central
    cx, cy = WIDTH // 2, HEIGHT // 2
    pygame.draw.rect(screen, C_SHADOW, (cx-215, cy-145, 430, 290), border_radius=20)
    pygame.draw.rect(screen, C_PANEL,  (cx-218, cy-148, 430, 290), border_radius=20)
    pygame.draw.rect(screen, C_ACCENT, (cx-218, cy-148, 430, 290), 3, border_radius=20)

    lbl = font_sm.render(f"NIVEL {level_num} DE {total}", True, C_ACCENT)
    screen.blit(lbl, lbl.get_rect(centerx=cx, top=cy-130))

    title = font_lg.render(titles[idx], True, C_TEXT)
    screen.blit(title, title.get_rect(centerx=cx, top=cy-90))

    for j, line in enumerate(descs[idx].split("\n")):
        t = font_sm.render(line, True, C_TEXT)
        screen.blit(t, t.get_rect(centerx=cx, top=cy-30 + j * 30))

    hint = font_sm.render("Presioná cualquier tecla o clic para comenzar", True, C_SHADOW)
    screen.blit(hint, hint.get_rect(centerx=cx, top=cy+100))

    pygame.display.flip()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                return


# -------- PANTALLA FINAL --------
def draw_summary(results):
    screen.fill(C_BG)

    # Encabezado
    title = font_lg.render("Resumen del Test", True, C_TEXT)
    screen.blit(title, title.get_rect(centerx=WIDTH//2, top=40))

    col_x = [120, 350, 560, 730]
    headers = ["Nivel", "Errores", "Tiempo (s)", "Salidas/min"]
    for i, h in enumerate(headers):
        t = font_sm.render(h, True, C_ACCENT)
        screen.blit(t, (col_x[i], 120))

    pygame.draw.line(screen, C_SHADOW, (80, 148), (WIDTH - 80, 148), 2)

    total_errors = 0
    total_time = 0

    for row, r in enumerate(results):
        level, errors, elapsed = r["level"], r["errors"], r["time"]
        total_errors += errors
        total_time   += elapsed
        spm = round(errors / (elapsed / 60), 1) if elapsed > 0 else 0

        y = 160 + row * 52
        # fila alternada
        if row % 2 == 0:
            pygame.draw.rect(screen, (240, 245, 250), (80, y - 4, WIDTH - 160, 44), border_radius=8)

        vals = [f"Nivel {level}", str(errors), f"{elapsed:.1f}", str(spm)]
        for i, v in enumerate(vals):
            col = C_END if (i == 1 and errors > 3) else C_TEXT
            t = font_md.render(v, True, col)
            screen.blit(t, (col_x[i], y + 4))

    # Línea totales
    ty = 160 + len(results) * 52 + 16
    pygame.draw.line(screen, C_SHADOW, (80, ty), (WIDTH - 80, ty), 2)
    totals = ["TOTAL", str(total_errors), f"{total_time:.1f}", "—"]
    for i, v in enumerate(totals):
        t = font_md.render(v, True, C_ACCENT)
        screen.blit(t, (col_x[i], ty + 10))

    # Interpretación
    if total_errors <= 3:
        interp, col = "Excelente control de trayectoria", C_START
    elif total_errors <= 8:
        interp, col = "Control moderado — revisar desvíos", (200, 140, 30)
    else:
        interp, col = "Dificultad significativa en el recorrido", C_END

    it = font_md.render(interp, True, col)
    screen.blit(it, it.get_rect(centerx=WIDTH//2, top=ty + 60))

    hint = font_sm.render("Presioná ESC para salir  |  R para repetir", True, C_SHADOW)
    screen.blit(hint, hint.get_rect(centerx=WIDTH//2, top=HEIGHT - 40))

    pygame.display.flip()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit(); sys.exit()
                if event.key == pygame.K_r:
                    return "repeat"
        clock.tick(30)

# -------- GAME --------
class Game:

    HALF_W = 32  # mitad del ancho del camino

    def __init__(self):
        self.level_fns = [self.level_1, self.level_2, self.level_3]
        self.results = []

    def level_1(self):
        return [(x, int(320 + 90 * math.sin(x * 0.010))) for x in range(130, 830, 3)]

    def level_2(self):
        return [(x, int(320 + 130 * math.sin(x * 0.018))) for x in range(130, 830, 3)]

    def level_3(self):
        return [(x, int(320 + 110 * math.sin(x * 0.013) + 55 * math.sin(x * 0.044))) for x in range(130, 830, 3)]

    def play_level(self, level_idx):
        draw_intro(level_idx + 1, len(self.level_fns))

        path   = self.level_fns[level_idx]()
        half_w = self.HALF_W

        pygame.mouse.set_pos(path[0])

        errors     = 0
        was_inside = True
        started    = False
        start_time = None

        while True:
            screen.fill(C_BG)

            # Camino
            draw_path_pro(screen, path, half_w)

            # Marcadores inicio / fin
            pygame.draw.circle(screen, C_START, path[0],  14)
            pygame.draw.circle(screen, (255,255,255), path[0],  14, 3)
            pygame.draw.circle(screen, C_END,   path[-1], 14)
            pygame.draw.circle(screen, (255,255,255), path[-1], 14, 3)

            mouse_pos = pygame.mouse.get_pos()

            # Distancia al camino
            min_dist = min(
                dist_to_segment(mouse_pos, path[i], path[i+1])
                for i in range(len(path) - 1)
            )
            inside = min_dist <= half_w

            # Iniciar cuando toca el punto de inicio
            if not started and math.dist(mouse_pos, path[0]) < 16:
                started    = True
                start_time = time.time()

            # Contar errores
            if started and not inside and was_inside:
                errors += 1
            was_inside = inside

            # Cursor
            cur_col = C_CURSOR_OK if inside else C_CURSOR_ERR
            pygame.draw.circle(screen, cur_col, mouse_pos, 9)
            pygame.draw.circle(screen, (255,255,255), mouse_pos, 9, 2)

            # HUD
            elapsed = (time.time() - start_time) if start_time else 0
            draw_hud(screen, level_idx + 1, errors, elapsed, inside)

            # Llegada
            if started and math.dist(mouse_pos, path[-1]) < 18:
                if success_sound:
                    success_sound.play()
                self.results.append({
                    "level":  level_idx + 1,
                    "errors": errors,
                    "time":   elapsed,
                })
                pygame.time.wait(400)
                return

            pygame.display.flip()
            clock.tick(FPS)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    pygame.quit(); sys.exit()

    def run(self):
        while True:
            self.results = []
            for i in range(len(self.level_fns)):
                self.play_level(i)

            action = draw_summary(self.results)
            if action != "repeat":
                break


# -------- ENTRY POINT --------
if __name__ == "__main__":
    Game().run()