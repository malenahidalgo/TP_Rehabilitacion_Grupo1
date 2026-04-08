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
C_BG        = (245, 240, 228)
C_TRACK_OUT = ( 80,  90, 100)
C_TRACK_MID = (255, 255, 255)
C_TRACK_IN  = (210, 225, 240)
C_START     = ( 40, 180,  80)
C_END       = (210,  60,  60)
C_TEXT      = ( 30,  40,  50)
C_PANEL     = (255, 255, 255)
C_SHADOW    = (180, 190, 200)
C_ACCENT    = ( 20,  80, 180)
C_NARANJA   = (220,  90,  20)
C_VERDE     = ( 30, 170,  80)
C_VERDE_HOV = ( 20, 140,  60)
C_WHITE     = (255, 255, 255)

screen = pygame.display.set_mode((1280, 800), pygame.SCALED | pygame.FULLSCREEN)
WIDTH, HEIGHT = screen.get_size()
pygame.display.set_caption("Test Estabilizador de Trayectoria")
clock = pygame.time.Clock()

# -------- FUENTES --------
f_size      = int(HEIGHT * 0.046)
font        = pygame.font.SysFont("Arial", f_size, bold=True)
font_title  = pygame.font.SysFont("Arial", int(f_size * 1.4), bold=True)
font_large  = pygame.font.SysFont("Arial", int(f_size * 2.8), bold=True)
font_hud    = pygame.font.SysFont("Arial", int(f_size * 0.72), bold=True)
font_info   = pygame.font.SysFont("Arial", int(f_size * 0.60), bold=True)
font_button = pygame.font.SysFont("Arial", int(f_size * 0.82), bold=True)

# -------- SONIDOS --------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

try:
    success_sound = pygame.mixer.Sound(os.path.join(BASE_DIR, "docs", "success.wav.mp3"))
except Exception:
    success_sound = None

try:
    fail_sound = pygame.mixer.Sound(os.path.join(BASE_DIR, "docs", "error.wav.mp3"))
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

        t1 = font_title.render("Test Estabilizador de Trayectoria", True, C_ACCENT)
        screen.blit(t1, t1.get_rect(centerx=WIDTH//2, top=int(HEIGHT * 0.12)))

        lbl = font.render("Nombre del Paciente:", True, C_TEXT)
        screen.blit(lbl, lbl.get_rect(centerx=WIDTH//2,
                                       top=box_rect.top - lbl.get_height() - int(HEIGHT*0.02)))

        pygame.draw.rect(screen, C_WHITE, box_rect, border_radius=12)
        pygame.draw.rect(screen, C_ACCENT, box_rect, 3, border_radius=12)

        cursor_timer += clock.get_time()
        if cursor_timer > 500:
            cursor_visible = not cursor_visible
            cursor_timer   = 0
        txt = font.render(name + ("|" if cursor_visible else " "), True, C_TEXT)
        screen.blit(txt, (box_rect.x + int(box_w * 0.03),
                          box_rect.y + (box_h - txt.get_height()) // 2))

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

        pill_txt = font_hud.render(
            f"NIVEL  {level_num}  DE  {total}  —  {dificultad[level_num-1]}", True, C_WHITE)
        pill_r = pill_txt.get_rect(centerx=WIDTH//2, top=int(HEIGHT * 0.06))
        pygame.draw.rect(screen, C_ACCENT,
                         pill_r.inflate(int(WIDTH*0.05), int(HEIGHT*0.03)),
                         border_radius=40)
        screen.blit(pill_txt, pill_r)

        num_surf = font_large.render(str(level_num), True, C_NARANJA)
        num_r    = num_surf.get_rect(centerx=WIDTH//2, top=int(HEIGHT * 0.15))
        screen.blit(num_surf, num_r)

        inst = font.render(instruccion, True, C_TEXT)
        screen.blit(inst, inst.get_rect(centerx=WIDTH//2,
                                         top=num_r.bottom + int(HEIGHT * 0.06)))

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
    if errors == 0:    return 5
    elif errors <= 2:  return 4
    elif errors <= 5:  return 3
    elif errors <= 9:  return 2
    elif errors <= 14: return 1
    else:              return 0

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


# -------- MÉTRICAS AVANZADAS --------

def calc_rmse(distances_while_active):
    """
    RMSE de trayectoria (píxeles).
    Recibe lista de distancias perpendiculares al path muestreadas
    a cada frame MIENTRAS el paciente está ejecutando el nivel.
    Mide la desviación continua promedio, capturando temblor y oscilación
    aunque el cursor no salga del canal.
    """
    if not distances_while_active:
        return 0.0
    mean_sq = sum(d * d for d in distances_while_active) / len(distances_while_active)
    return round(math.sqrt(mean_sq), 2)


def calc_mean_speed(path, elapsed):
    """
    Velocidad media de ejecución (px/s).
    Longitud total del camino ideal dividida por el tiempo de ejecución.
    Permite detectar bradiquinesia post-ACV comparando entre sesiones.
    """
    if elapsed <= 0:
        return 0.0
    path_length = sum(
        math.dist(path[i], path[i+1]) for i in range(len(path) - 1)
    )
    return round(path_length / elapsed, 1)


def calc_time_inside_pct(frames_inside, frames_total):
    """
    Porcentaje de tiempo dentro del canal (%).
    Complementa el conteo de errores: dos pacientes con igual número
    de salidas pueden diferir mucho en cuánto tiempo permanecen fuera,
    lo que refleja la severidad del déficit de corrección motora.
    """
    if frames_total == 0:
        return 0.0
    return round(100.0 * frames_inside / frames_total, 1)


def calc_fatigue_index(results):
    """
    Índice de fatiga — pendiente de regresión lineal sobre errores/min
    a lo largo de los niveles.
    Pendiente positiva  → fatiga neuromuscular progresiva.
    Pendiente negativa  → aprendizaje / calentamiento motor.
    Entre ±1.0 epm/nivel → rendimiento estable.
    """
    if len(results) < 2:
        return {"pendiente": None, "clasificacion": "incompleto"}

    x = list(range(1, len(results) + 1))
    y = [r["errors_per_min"] for r in results]

    x_mean = sum(x) / len(x)
    y_mean = sum(y) / len(y)

    num   = sum((xi - x_mean) * (yi - y_mean) for xi, yi in zip(x, y))
    denom = sum((xi - x_mean) ** 2 for xi in x)

    pendiente = round(num / denom, 3) if denom != 0 else 0.0

    if pendiente > 1.0:
        clasificacion = "fatiga"
    elif pendiente < -1.0:
        clasificacion = "aprendizaje"
    else:
        clasificacion = "estable"

    return {"pendiente_epm_por_nivel": pendiente, "clasificacion": clasificacion}


# -------- PANTALLA FINAL (solo muestra métricas para paciente) --------
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

    top = int(HEIGHT * 0.04)

    # Título
    title = font_title.render("¡Terminaste!", True, C_ACCENT)
    screen.blit(title, title.get_rect(centerx=WIDTH//2, top=top))
    top += title.get_height() + int(HEIGHT * 0.02)

    # Mensaje motivacional
    msg = font_large.render(msg_map[global_stars], True, msg_col_map[global_stars])
    screen.blit(msg, msg.get_rect(centerx=WIDTH//2, top=top))
    top += msg.get_height() + int(HEIGHT * 0.02)

    # Estrellas globales
    draw_stars(screen, global_stars, WIDTH//2, top + int(f_size * 0.9))
    top += int(f_size * 1.8) + int(HEIGHT * 0.02)

    pygame.draw.line(screen, C_SHADOW, (int(WIDTH*0.06), top), (int(WIDTH*0.94), top), 2)
    top += int(HEIGHT * 0.02)

    # Encabezados tabla — solo columnas para paciente
    # Errores | Tiempo | Salidas/min | Estrellas
    col_x = [int(WIDTH * p) for p in [0.06, 0.25, 0.44, 0.63, 0.80]]
    headers = ["Nivel", "Errores", "Tiempo (s)", "Sal./min", "★"]
    for i, h in enumerate(headers):
        t = font_hud.render(h, True, C_ACCENT)
        screen.blit(t, (col_x[i], top))
    top += font_hud.get_height() + int(HEIGHT * 0.01)
    pygame.draw.line(screen, C_SHADOW, (int(WIDTH*0.06), top), (int(WIDTH*0.94), top), 1)
    top += int(HEIGHT * 0.01)

    lh    = font.get_height()
    row_h = int(lh * 1.5)

    for row, r in enumerate(results):
        level, errors, elapsed = r["level"], r["errors"], r["time"]
        spm       = round(errors / (elapsed / 60), 1) if elapsed > 0 else 0
        stars_row = calc_stars(errors)

        if row % 2 == 0:
            pygame.draw.rect(screen, (235, 230, 215),
                             (int(WIDTH*0.05), top - 4, int(WIDTH*0.90), row_h),
                             border_radius=8)

        vals = [f"Nivel {level}", str(errors), f"{elapsed:.1f}", str(spm)]
        for i, v in enumerate(vals):
            col = C_END if (i == 1 and errors > 5) else C_TEXT
            t = font.render(v, True, col)
            screen.blit(t, (col_x[i], top + (row_h - lh)//2))

        # Estrellitas por fila
        draw_stars(screen, stars_row, col_x[4] + int(WIDTH * 0.06),
                   top + row_h//2, size=int(f_size * 0.42))
        top += row_h

    # Totales
    top += int(HEIGHT * 0.01)
    pygame.draw.line(screen, C_SHADOW, (int(WIDTH*0.06), top), (int(WIDTH*0.94), top), 2)
    top += int(HEIGHT * 0.015)

    total_spm = round(total_errors / (total_time / 60), 1) if total_time > 0 else 0
    totals = ["TOTAL", str(total_errors), f"{total_time:.1f}", str(total_spm)]
    for i, v in enumerate(totals):
        t = font_hud.render(v, True, C_ACCENT)
        screen.blit(t, (col_x[i], top))
    top += font_hud.get_height() + int(HEIGHT * 0.015)

    # Hint
    hint = font_hud.render("ESC para salir    R para repetir", True, C_TEXT)
    screen.blit(hint, hint.get_rect(centerx=WIDTH//2,
                                     top=HEIGHT - hint.get_height() - int(HEIGHT*0.03)))

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
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    folder = os.path.join(BASE_DIR, "resultados")

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

    fatigue = calc_fatigue_index(results)

    data = {
        "paciente":  patient_name,
        "fecha":     datetime.now().isoformat(),
        "tipo_test": "Control de Trayectoria",
        # ---- Resultados por nivel (incluye métricas clínicas avanzadas) ----
        "resultados": [
            {
                "nivel":              r["level"],
                "errores":            r["errors"],
                "tiempo_s":           r["time"],
                "errores_por_minuto": r["errors_per_min"],
                # Tiempo de reacción: latencia entre aparición del estímulo
                # y primer contacto con el punto de inicio (iniciación motora voluntaria)
                "tiempo_reaccion_s":  r["reaction_time"],
                # RMSE: desviación cuadrática media de la trayectoria real respecto
                # al camino ideal (captura temblor y oscilación continua en px)
                "rmse_px":            r["rmse_px"],
                # Velocidad media de ejecución: longitud del path / tiempo (px/s)
                # Permite detectar bradiquinesia comparando entre sesiones
                "velocidad_media_px_s": r["mean_speed_px_s"],
            }
            for r in results
        ],
        # ---- Resumen global ----
        "resumen": {
            "niveles_completados":    len(results),
            "errores_totales":        sum(r["errors"] for r in results),
            "tiempo_total_s":         round(sum(r["time"] for r in results), 2),
            "tiempos_reaccion_s":     [r["reaction_time"] for r in results],
            "errores_por_minuto":     [r["errors_per_min"] for r in results],
            "rmse_por_nivel_px":      [r["rmse_px"] for r in results],
            "velocidad_media_px_s":   [r["mean_speed_px_s"] for r in results],
            # Índice de fatiga: pendiente de regresión lineal de errores/min
            # sobre niveles. >1.0 = fatiga, <-1.0 = aprendizaje, ±1.0 = estable
            "indice_fatiga":          fatigue,
        }
    }

    with open(filename, "w") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

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

        errors        = 0
        was_inside    = True
        started       = False
        start_time    = None
        appear_time   = time.time()
        reaction_time = None

        # --- Acumuladores para métricas avanzadas ---
        distances_sample  = []   # distancias perpendiculares (para RMSE)
        frames_inside     = 0    # frames dentro del canal
        frames_total      = 0    # frames totales desde que empezó

        while True:
            screen.fill(C_BG)

            draw_path_pro(screen, path, half_w)

            # Punto de inicio — verde con halo amarillo
            pygame.draw.circle(screen, (255, 220, 0),   path[0],  32)
            pygame.draw.circle(screen, (0,   210,  80), path[0],  26)
            pygame.draw.circle(screen, (255, 255, 255), path[0],  26, 4)

            # Punto final — rojo con halo naranja
            pygame.draw.circle(screen, (255, 120,  0),  path[-1], 32)
            pygame.draw.circle(screen, (220,  30,  30), path[-1], 26)
            pygame.draw.circle(screen, (255, 255, 255), path[-1], 26, 4)

            mouse_pos = pygame.mouse.get_pos()

            # Distancia perpendicular mínima al path (para inside y RMSE)
            min_dist = min(
                dist_to_segment(mouse_pos, path[i], path[i+1])
                for i in range(len(path) - 1)
            )
            inside = min_dist <= half_w

            # Detectar inicio del movimiento
            if not started and math.dist(mouse_pos, path[0]) < 16:
                started       = True
                start_time    = time.time()
                reaction_time = round(start_time - appear_time, 2)

            if started:
                frames_total += 1
                # Registrar distancia para RMSE en cada frame
                distances_sample.append(min_dist)
                if inside:
                    frames_inside += 1

            # Contar errores (transición dentro → fuera)
            if started and not inside and was_inside:
                errors += 1
                if fail_sound:
                    fail_sound.stop()
                    fail_sound.play()

            was_inside = inside

            # Cursor
            cur_col  = (0, 180, 255) if inside else (220, 30, 30)
            halo_col = (180, 230, 255) if inside else (255, 160, 120)
            pygame.draw.circle(screen, halo_col, mouse_pos, 28)
            pygame.draw.circle(screen, cur_col,  mouse_pos, 20)
            pygame.draw.circle(screen, (255, 255, 255), mouse_pos, 20, 3)
            pygame.draw.circle(screen, (255, 255, 255), mouse_pos, 5)

            elapsed = (time.time() - start_time) if start_time else 0
            draw_hud(screen, level_idx + 1, errors, elapsed, inside)

            # Llegada al punto final
            if started and math.dist(mouse_pos, path[-1]) < 18:
                if success_sound:
                    success_sound.play()

                rmse           = calc_rmse(distances_sample)
                mean_speed     = calc_mean_speed(path, elapsed)
                time_inside_p  = calc_time_inside_pct(frames_inside, frames_total)

                self.results.append({
                    "level":            level_idx + 1,
                    "errors":           errors,
                    "time":             round(elapsed, 2),
                    "reaction_time":    reaction_time if reaction_time else 0,
                    "errors_per_min":   round(errors / (elapsed / 60), 2) if elapsed > 0 else 0,
                    "rmse_px":          rmse,
                    "mean_speed_px_s":  mean_speed,
                    "time_inside_pct":  time_inside_p,
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