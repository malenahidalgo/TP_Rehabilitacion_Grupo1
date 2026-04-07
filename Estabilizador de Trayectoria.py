import pygame
import sys
import math
import time
import os
import json
from datetime import datetime

pygame.init()
pygame.mixer.init()

# -------- CONFIG --------
FPS = 60

# Paleta — crema + colores vivos
C_BG        = (245, 240, 228)   # crema suave
C_TRACK_OUT = ( 80,  90, 100)
C_TRACK_MID = (255, 255, 255)
C_TRACK_IN  = (210, 225, 240)
C_START     = ( 40, 180,  80)
C_END       = (210,  60,  60)
C_TEXT      = ( 30,  40,  50)
C_PANEL     = (255, 255, 255)
C_SHADOW    = (180, 190, 200)
C_ACCENT    = ( 20,  80, 180)   # azul fuerte
C_NARANJA   = (220,  90,  20)
C_VERDE     = ( 30, 170,  80)
C_VERDE_HOV = ( 20, 140,  60)
C_WHITE     = (255, 255, 255)

screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
WIDTH, HEIGHT = screen.get_size()
pygame.display.set_caption("Test de Control de Trayectoria")
clock = pygame.time.Clock()

# -------- FUENTES escaladas a la pantalla --------
f_size      = int(HEIGHT * 0.046)
font        = pygame.font.SysFont("Arial", f_size, bold=True)
font_title  = pygame.font.SysFont("Arial", int(f_size * 1.4), bold=True)
font_large  = pygame.font.SysFont("Arial", int(f_size * 2.8), bold=True)   # número nivel grande
font_hud    = pygame.font.SysFont("Arial", int(f_size * 0.72), bold=True)
font_info   = pygame.font.SysFont("Arial", int(f_size * 0.60), bold=True)
font_button = pygame.font.SysFont("Arial", int(f_size * 0.82), bold=True)

# -------- SONIDOS --------
try:
    success_sound = pygame.mixer.Sound("success.wav.mp3")
except Exception:
    success_sound = None

try:
    fail_sound = pygame.mixer.Sound("error.wav.mp3")
except Exception:
    fail_sound = None

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
    if len(path) < 2:
        return

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
        pygame.draw.polygon(surface, C_TRACK_OUT, poly)
        inner_top = [(x + 4 * (pts_bot[i][0] - pts_top[i][0]) / (half_w * 2),
                      y + 4 * (pts_bot[i][1] - pts_top[i][1]) / (half_w * 2))
                     for i, (x, y) in enumerate(pts_top)]
        inner_bot = [(x + 4 * (pts_top[i][0] - pts_bot[i][0]) / (half_w * 2),
                      y + 4 * (pts_top[i][1] - pts_bot[i][1]) / (half_w * 2))
                     for i, (x, y) in enumerate(pts_bot)]
        inner_poly = inner_top + list(reversed(inner_bot))
        pygame.draw.polygon(surface, C_TRACK_MID, inner_poly)

        inner2_top = [(x + 10 * (pts_bot[i][0] - pts_top[i][0]) / (half_w * 2),
                       y + 10 * (pts_bot[i][1] - pts_top[i][1]) / (half_w * 2))
                      for i, (x, y) in enumerate(pts_top)]
        inner2_bot = [(x + 10 * (pts_top[i][0] - pts_bot[i][0]) / (half_w * 2),
                       y + 10 * (pts_top[i][1] - pts_bot[i][1]) / (half_w * 2))
                      for i, (x, y) in enumerate(pts_bot)]
        inner2_poly = inner2_top + list(reversed(inner2_bot))
        pygame.draw.polygon(surface, C_TRACK_IN, inner2_poly)

    for i in range(0, len(path) - 1, 12):
        pygame.draw.line(surface, (180, 200, 220), path[i], path[min(i + 6, len(path)-1)], 1)


# -------- PANEL HUD --------
def draw_hud(surface, level, errors, elapsed, inside):
    """Barra chica en la parte inferior — no tapa el laberinto."""
    bar_h = int(HEIGHT * 0.07)
    bar_y = HEIGHT - bar_h
    pygame.draw.rect(surface, (255, 255, 255), (0, bar_y, WIDTH, bar_h))
    pygame.draw.line(surface, C_SHADOW, (0, bar_y), (WIDTH, bar_y), 2)

    estado_txt = "✓  Dentro" if inside else "✗  Fuera"
    estado_col = C_VERDE if inside else C_END

    items = [
        (f"Nivel {level}",          C_ACCENT),
        (f"Errores: {errors}",      C_TEXT),
        (f"Tiempo: {elapsed:.0f}s", C_TEXT),
        (estado_txt,                estado_col),
    ]
    n      = len(items)
    slot_w = WIDTH // n
    cy     = bar_y + bar_h // 2

    for i, (txt, col) in enumerate(items):
        t = font_hud.render(txt, True, col)
        surface.blit(t, t.get_rect(centerx=slot_w * i + slot_w // 2, centery=cy))


# -------- HELPERS UI --------
def draw_button(surface, rect, text, hovered):
    color = C_VERDE_HOV if hovered else C_VERDE
    pygame.draw.rect(surface, (0, 80, 40), rect.move(4, 5), border_radius=16)
    pygame.draw.rect(surface, color, rect, border_radius=16)
    t = font_button.render(text, True, C_WHITE)
    surface.blit(t, t.get_rect(center=rect.center))


# -------- PANTALLA NOMBRE DE PACIENTE --------
def get_patient_name():
    name = ""
    cursor_visible = True
    cursor_timer   = 0

    # Proporcional a la pantalla
    box_w    = int(WIDTH * 0.45)
    box_h    = int(font.get_height() * 1.6)
    box_rect = pygame.Rect(WIDTH//2 - box_w//2, int(HEIGHT * 0.52), box_w, box_h)

    btn_w    = int(WIDTH * 0.28)
    btn_h    = int(font_button.get_height() * 1.8)
    btn_rect = pygame.Rect(WIDTH//2 - btn_w//2, int(HEIGHT * 0.68), btn_w, btn_h)

    while True:
        screen.fill(C_BG)
        mx, my = pygame.mouse.get_pos()
        btn_hover = btn_rect.collidepoint(mx, my)

        # Título
        t1 = font_title.render("Test de Trayectoria", True, C_ACCENT)
        screen.blit(t1, t1.get_rect(centerx=WIDTH//2, top=int(HEIGHT * 0.10)))

        # Línea naranja bajo título
        lw = t1.get_width()
        ly = int(HEIGHT * 0.10) + t1.get_height() + int(HEIGHT * 0.01)
        pygame.draw.line(screen, C_NARANJA,
                         (WIDTH//2 - lw//2, ly),
                         (WIDTH//2 + lw//2, ly), 5)

        # Label
        lbl = font.render("Nombre del Paciente:", True, C_TEXT)
        screen.blit(lbl, lbl.get_rect(centerx=WIDTH//2,
                                       top=box_rect.top - lbl.get_height() - int(HEIGHT*0.02)))

        # Input box
        pygame.draw.rect(screen, C_WHITE, box_rect, border_radius=12)
        pygame.draw.rect(screen, C_ACCENT, box_rect, 3, border_radius=12)

        cursor_timer += clock.get_time()
        if cursor_timer > 500:
            cursor_visible = not cursor_visible
            cursor_timer   = 0
        txt = font.render(name + ("|" if cursor_visible else " "), True, C_TEXT)
        screen.blit(txt, (box_rect.x + int(box_w * 0.03),
                          box_rect.y + (box_h - txt.get_height()) // 2))

        # Botón
        draw_button(screen, btn_rect, "COMENZAR", btn_hover)

        pygame.display.flip()
        clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN and name.strip():
                    return name.strip()
                elif event.key == pygame.K_BACKSPACE:
                    name = name[:-1]
                elif event.key == pygame.K_ESCAPE:
                    pygame.quit(); sys.exit()
                else:
                    if len(name) < 24:
                        name += event.unicode
            if event.type == pygame.MOUSEBUTTONDOWN:
                if btn_rect.collidepoint(event.pos) and name.strip():
                    return name.strip()


# -------- PANTALLA DE INTRO --------
def draw_intro(level_num, total):
    dificultad = ["Fácil", "Medio", "Difícil"]
    instruccion = "Seguí el camino del punto VERDE al ROJO"

    btn_w    = int(WIDTH * 0.30)
    btn_h    = int(font_button.get_height() * 2.0)
    btn_rect = pygame.Rect(WIDTH//2 - btn_w//2, int(HEIGHT * 0.75), btn_w, btn_h)

    while True:
        screen.fill(C_BG)
        mx, my = pygame.mouse.get_pos()
        btn_hover = btn_rect.collidepoint(mx, my)

        # Pastilla NIVEL X DE Y arriba
        pill_txt = font_hud.render(
            f"NIVEL  {level_num}  DE  {total}  —  {dificultad[level_num-1]}", True, C_WHITE)
        pill_r = pill_txt.get_rect(centerx=WIDTH//2, top=int(HEIGHT * 0.06))
        pygame.draw.rect(screen, C_ACCENT,
                         pill_r.inflate(int(WIDTH*0.05), int(HEIGHT*0.03)),
                         border_radius=40)
        screen.blit(pill_txt, pill_r)

        # Número grande naranja — bien centrado
        num_surf = font_large.render(str(level_num), True, C_NARANJA)
        num_r    = num_surf.get_rect(centerx=WIDTH//2, top=int(HEIGHT * 0.15))
        screen.blit(num_surf, num_r)

        # Instrucción — una sola línea clara debajo del número
        inst = font.render(instruccion, True, C_TEXT)
        screen.blit(inst, inst.get_rect(centerx=WIDTH//2,
                                         top=num_r.bottom + int(HEIGHT * 0.06)))

        # Botón
        draw_button(screen, btn_rect, "¡EMPEZAR!", btn_hover)

        pygame.display.flip()
        clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                if btn_rect.collidepoint(event.pos):
                    return
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit(); sys.exit()
                if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    return


# -------- ESTRELLAS --------
def calc_stars(errors):
    if errors == 0:   return 5
    elif errors <= 2: return 4
    elif errors <= 5: return 3
    elif errors <= 9: return 2
    elif errors <= 14:return 1
    else:             return 0

def draw_stars(surface, stars, cx, cy, size=None):
    if size is None:
        size = int(f_size * 0.9)
    total   = 5
    spacing = size + int(size * 0.3)
    start_x = cx - (total * spacing) // 2
    for i in range(total):
        color = (255, 200, 0) if i < stars else (210, 215, 220)
        border= (200, 160, 0) if i < stars else (170, 180, 190)
        cx2   = start_x + i * spacing + size // 2
        pts   = []
        for j in range(10):
            angle = math.pi / 2 + j * math.pi / 5
            r = size // 2 if j % 2 == 0 else size // 4
            pts.append((cx2 + r * math.cos(angle), cy - r * math.sin(angle)))
        pygame.draw.polygon(surface, color, pts)
        pygame.draw.polygon(surface, border, pts, 2)


# -------- IPT --------
def calc_ipt(errors, elapsed):
    if elapsed == 0: return 0
    base         = max(0, 100 - errors * 12)
    time_penalty = max(0, (elapsed - 60) * 0.3)
    return round(max(0, base - time_penalty), 1)


# -------- PANTALLA FINAL --------
def draw_summary(results):
    screen.fill(C_BG)

    total_errors = sum(r["errors"] for r in results)
    total_time   = sum(r["time"]   for r in results)
    global_stars = calc_stars(total_errors)

    msg_map = {
        5: "¡Excelente! ¡Muy bien hecho!",
        4: "¡Muy bien! ¡Casi perfecto!",
        3: "¡Bien! Seguí practicando.",
        2: "Buen intento. ¡Vamos de nuevo!",
        1: "Fue difícil. ¡No te rindas!",
        0: "Sigamos intentándolo juntos.",
    }
    msg_col_map = {
        5: C_VERDE, 4: C_VERDE, 3: C_NARANJA,
        2: C_NARANJA, 1: C_END, 0: C_END
    }

    # --- Layout proporcional ---
    top = int(HEIGHT * 0.04)
    lh  = font.get_height()

    # Título
    title = font_title.render("¡Terminaste!", True, C_ACCENT)
    screen.blit(title, title.get_rect(centerx=WIDTH//2, top=top))
    top += title.get_height() + int(HEIGHT * 0.02)

    # Mensaje
    msg = font_large.render(msg_map[global_stars], True, msg_col_map[global_stars])
    screen.blit(msg, msg.get_rect(centerx=WIDTH//2, top=top))
    top += msg.get_height() + int(HEIGHT * 0.02)

    # Estrellas globales
    draw_stars(screen, global_stars, WIDTH//2, top + int(f_size * 0.9))
    top += int(f_size * 1.8) + int(HEIGHT * 0.02)

    # Separador
    pygame.draw.line(screen, C_SHADOW, (int(WIDTH*0.06), top), (int(WIDTH*0.94), top), 2)
    top += int(HEIGHT * 0.02)

    # Encabezados tabla — 5 columnas
    col_x = [int(WIDTH * p) for p in [0.06, 0.22, 0.38, 0.54, 0.70]]
    headers = ["Nivel", "Errores", "Tiempo (s)", "Sal./min", "IPT (%)"]
    for i, h in enumerate(headers):
        t = font_hud.render(h, True, C_ACCENT)
        screen.blit(t, (col_x[i], top))
    top += font_hud.get_height() + int(HEIGHT * 0.01)
    pygame.draw.line(screen, C_SHADOW, (int(WIDTH*0.06), top), (int(WIDTH*0.94), top), 1)
    top += int(HEIGHT * 0.01)

    row_h = int(lh * 1.5)
    for row, r in enumerate(results):
        level, errors, elapsed = r["level"], r["errors"], r["time"]
        spm  = round(errors / (elapsed / 60), 1) if elapsed > 0 else 0
        ipt  = calc_ipt(errors, elapsed)
        stars_row = calc_stars(errors)

        if row % 2 == 0:
            pygame.draw.rect(screen, (235, 230, 215),
                             (int(WIDTH*0.05), top - 4, int(WIDTH*0.90), row_h),
                             border_radius=8)

        vals = [f"Nivel {level}", str(errors), f"{elapsed:.1f}", str(spm), f"{ipt}%"]
        for i, v in enumerate(vals):
            col = C_END if (i == 1 and errors > 5) else C_TEXT
            t = font.render(v, True, col)
            screen.blit(t, (col_x[i], top + (row_h - lh)//2))

        # Estrellitas pequeñas al costado
        draw_stars(screen, stars_row, int(WIDTH * 0.88),
                   top + row_h//2, size=int(f_size * 0.45))
        top += row_h

    # Totales
    top += int(HEIGHT * 0.01)
    pygame.draw.line(screen, C_SHADOW, (int(WIDTH*0.06), top), (int(WIDTH*0.94), top), 2)
    top += int(HEIGHT * 0.015)
    ipt_total = calc_ipt(total_errors, total_time)
    totals = ["TOTAL", str(total_errors), f"{total_time:.1f}", "—", f"{ipt_total}%"]
    for i, v in enumerate(totals):
        t = font_hud.render(v, True, C_ACCENT)
        screen.blit(t, (col_x[i], top))
    top += font_hud.get_height() + int(HEIGHT * 0.015)

    # Nota TO
    nota = font_info.render(
        "IPT: Índice de Precisión de Trayectoria  |  100 = sin errores", True, C_SHADOW)
    screen.blit(nota, nota.get_rect(centerx=WIDTH//2, top=top))

    # Hint
    hint = font_hud.render("ESC para salir    R para repetir", True, C_TEXT)
    screen.blit(hint, hint.get_rect(centerx=WIDTH//2, top=HEIGHT - hint.get_height() - int(HEIGHT*0.03)))

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


# -------- JSON --------
def save_results_json(results, patient_name):
    folder = "resultados"
    if not os.path.exists(folder):
        os.makedirs(folder)

    existing_files = [
        f for f in os.listdir(folder)
        if f.startswith(f"test_{patient_name}_") and f.endswith(".json")
    ]
    attempts = []
    for f in existing_files:
        try:
            num = int(f.split("_")[-1].replace(".json", ""))
            attempts.append(num)
        except:
            pass

    num_prueba = max(attempts) + 1 if attempts else 1
    filename   = f"{folder}/test_{patient_name}_{num_prueba}.json"

    # --- Tendencia de fatiga ---
    # Compara errores del primer nivel vs último nivel completado
    if len(results) >= 2:
        diff = results[-1]["errors"] - results[0]["errors"]
        if diff > 2:
            tendencia = "fatiga"        # empeora al avanzar
        elif diff < -2:
            tendencia = "aprendizaje"   # mejora al avanzar
        else:
            tendencia = "estable"
    else:
        tendencia = "incompleto"

    data = {
        "paciente":  patient_name,
        "fecha":     datetime.now().isoformat(),
        "tipo_test": "Control de Trayectoria",
        "resultados": results,
        "resumen": {
            "niveles_completados":  len(results),
            "errores_totales":      sum(r["errors"] for r in results),
            "tiempo_total_s":       round(sum(r["time"] for r in results), 2),
            "tiempo_reaccion_s":    [r["reaction_time"] for r in results],
            "errores_por_minuto":   [r["errors_per_min"] for r in results],
            "tendencia_fatiga":     tendencia,
            "ipt_global":           calc_ipt(
                                        sum(r["errors"] for r in results),
                                        sum(r["time"]   for r in results)
                                    ),
        }
    }

    with open(filename, "w") as f:
        json.dump(data, f, indent=4)

    print(f"Resultados guardados en {filename}")


# -------- GAME --------
class Game:

    HALF_W = 55

    def __init__(self):
        self.patient_name = get_patient_name()
        self.level_fns    = [self.level_1, self.level_2, self.level_3]
        self.results      = []

    def level_1(self):
        return [
            (x, int(HEIGHT/2 + 0.28 * HEIGHT * math.sin(x * 0.008)))
            for x in range(int(0.05 * WIDTH), int(0.95 * WIDTH), 3)
        ]

    def level_2(self):
        return [
            (x, int(HEIGHT/2 + 0.32 * HEIGHT * math.sin(x * 0.011)))
            for x in range(int(0.05 * WIDTH), int(0.95 * WIDTH), 3)
        ]

    def level_3(self):
        return [
            (x, int(HEIGHT/2 + 0.30 * HEIGHT * math.sin(x * 0.015)))
            for x in range(int(0.05 * WIDTH), int(0.95 * WIDTH), 3)
        ]

    def play_level(self, level_idx):
        draw_intro(level_idx + 1, len(self.level_fns))

        path   = self.level_fns[level_idx]()
        half_w = self.HALF_W

        pygame.mouse.set_pos(path[0])

        errors         = 0
        was_inside     = True
        started        = False
        start_time     = None
        appear_time    = time.time()   # para tiempo de reacción
        reaction_time  = None

        while True:
            screen.fill(C_BG)

            draw_path_pro(screen, path, half_w)

            # Inicio — verde con halo amarillo
            pygame.draw.circle(screen, (255, 220, 0),   path[0],  32)
            pygame.draw.circle(screen, (0,   210,  80), path[0],  26)
            pygame.draw.circle(screen, (255, 255, 255), path[0],  26, 4)

            # Llegada — rojo con halo naranja
            pygame.draw.circle(screen, (255, 120,  0),  path[-1], 32)
            pygame.draw.circle(screen, (220,  30,  30), path[-1], 26)
            pygame.draw.circle(screen, (255, 255, 255), path[-1], 26, 4)

            mouse_pos = pygame.mouse.get_pos()

            min_dist = min(
                dist_to_segment(mouse_pos, path[i], path[i+1])
                for i in range(len(path) - 1)
            )
            inside = min_dist <= half_w

            if not started and math.dist(mouse_pos, path[0]) < 16:
                started       = True
                start_time    = time.time()
                reaction_time = round(start_time - appear_time, 2)

            if started and not inside and was_inside:
                errors += 1
                if fail_sound:
                    fail_sound.stop()
                    fail_sound.play()

            was_inside = inside

            cur_col  = (0, 180, 255) if inside else (220, 30, 30)
            halo_col = (180, 230, 255) if inside else (255, 160, 120)
            pygame.draw.circle(screen, halo_col, mouse_pos, 28)
            pygame.draw.circle(screen, cur_col,  mouse_pos, 20)
            pygame.draw.circle(screen, (255, 255, 255), mouse_pos, 20, 3)
            pygame.draw.circle(screen, (255, 255, 255), mouse_pos, 5)

            elapsed = (time.time() - start_time) if start_time else 0
            draw_hud(screen, level_idx + 1, errors, elapsed, inside)

            if started and math.dist(mouse_pos, path[-1]) < 18:
                if success_sound:
                    success_sound.play()
                self.results.append({
                    "level":         level_idx + 1,
                    "errors":        errors,
                    "time":          round(elapsed, 2),
                    "reaction_time": reaction_time if reaction_time else 0,
                    "errors_per_min": round(errors / (elapsed / 60), 2) if elapsed > 0 else 0,
                })
                pygame.time.wait(400)
                return

            pygame.display.flip()
            clock.tick(FPS)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    raise SystemExit
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    raise SystemExit

    def run(self):
        while True:
            self.results = []
            try:
                for i in range(len(self.level_fns)):
                    self.play_level(i)
            except SystemExit:
                if self.results:
                    save_results_json(self.results, self.patient_name)
                pygame.quit()
                sys.exit()

            save_results_json(self.results, self.patient_name)
            action = draw_summary(self.results)
            if action != "repeat":
                break


# -------- ENTRY POINT --------
if __name__ == "__main__":
    Game().run()