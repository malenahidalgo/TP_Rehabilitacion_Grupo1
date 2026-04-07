import pygame
import random
import time
import math
import json
import os
import re

# --- INICIALIZACIÓN ---
pygame.init()
pygame.mixer.init()

# Configuración de Pantalla Completa
screen_info = pygame.display.Info()
WIDTH, HEIGHT = screen_info.current_w, screen_info.current_h
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN | pygame.HWSURFACE | pygame.DOUBLEBUF)
pygame.display.set_caption("Test de Reacción Multimodal - Rehab Eng")

# --- COLORES ---
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 100, 100)
BLUE = (100, 150, 255)
GREEN = (100, 200, 100)
GRAY = (220, 220, 220)
DARK_BLUE = (25, 25, 112)
INFO_BLUE = (0, 102, 204)

# --- FUENTES ---
f_size = int(HEIGHT * 0.06)
font = pygame.font.SysFont("Helvetica", f_size)
font_title = pygame.font.SysFont("Georgia", int(f_size * 1.5), bold=True)
font_large = pygame.font.SysFont("Helvetica", int(f_size * 1.5), bold=True)
font_hud = pygame.font.SysFont("Helvetica", int(f_size * 0.8), bold=True)
font_info = pygame.font.SysFont("Helvetica", int(f_size * 0.60), bold=True)
font_button = pygame.font.SysFont("Helvetica", int(f_size * 0.7), bold=True)

# --- CONFIGURACIÓN DE CUADRANTES ---
CUADRANTES = {
    "Superior Izquierdo": (WIDTH * 0.25, HEIGHT * 0.25),
    "Superior Derecho":   (WIDTH * 0.75, HEIGHT * 0.25),
    "Inferior Izquierdo": (WIDTH * 0.25, HEIGHT * 0.50),
    "Inferior Derecho":   (WIDTH * 0.75, HEIGHT * 0.50)
}

# --- CARGA DE ICONOS ---
try:
    sonido_icon_orig = pygame.image.load("docs/sonido.webp").convert_alpha() 
    icon_btn_size = int(HEIGHT * 0.12) 
    sonido_icon = pygame.transform.smoothscale(sonido_icon_orig, (icon_btn_size, icon_btn_size))
    
    figura_atlas = pygame.image.load("docs/formas.png").convert_alpha()
    atlas_w, atlas_h = figura_atlas.get_size()
    figura_sub = figura_atlas.subsurface((0, 0, atlas_w // 2, atlas_h // 2))
    figura_icon = pygame.transform.smoothscale(figura_sub, (icon_btn_size, icon_btn_size))
except Exception as e:
    print(f"Error cargando imágenes: {e}")
    sonido_icon = figura_icon = None

# --- FUNCIONES DE CÁLCULO MOTRIZ (NUEVAS) ---
def calculate_trajectory_metrics(points, target_pos, start_pos):
    if len(points) < 2: return 0, 0
    dist_real = sum(math.hypot(points[i+1][0]-points[i][0], points[i+1][1]-points[i][1]) for i in range(len(points)-1))
    dist_ideal = math.hypot(target_pos[0]-start_pos[0], target_pos[1]-start_pos[1])
    rectitud = round(dist_ideal / dist_real, 2) if dist_real > 0 else 0
    return rectitud, dist_real

# --- MÉTRICAS Y GUARDADO ---
def calculate_metrics(data_results, incorrect_details):
    all_times = data_results[0] + data_results[1]
    cv = fatiga = interferencia = impulsividad = discriminacion = 0
    if all_times:
        mean = sum(all_times) / len(all_times)
        std_dev = math.sqrt(sum((x - mean) ** 2 for x in all_times) / len(all_times))
        cv = round((std_dev / mean) * 100, 2)
    if len(all_times) >= 6:
        fatiga = round((sum(all_times[-3:]) / 3) - (sum(all_times[:3]) / 3), 2)
    avg_v = sum(data_results[0]) / len(data_results[0]) if data_results[0] else 0
    avg_a = sum(data_results[1]) / len(data_results[1]) if data_results[1] else 0
    interferencia = round(abs(avg_v - avg_a), 2)
    for err_time in incorrect_details:
        if err_time < 300: impulsividad += 1
        else: discriminacion += 1
    return cv, fatiga, interferencia, impulsividad, discriminacion

def save_results(patient_name, correctas, incorrectas, data_results, incorrect_details, lat_data, traj_metrics, incompleto=False):
    if not os.path.exists('results'): os.makedirs('results')
    p_id = "".join(ch for ch in patient_name.strip().replace(" ", "_") if ch.isalnum() or ch in ("_", "-"))
    if not p_id: p_id = "Paciente"
    
    cv, fatiga, interf, imp, disc = calculate_metrics(data_results, incorrect_details)
    avg_v = round(sum(data_results[0]) / len(data_results[0]), 2) if data_results[0] else 0
    avg_a = round(sum(data_results[1]) / len(data_results[1]), 2) if data_results[1] else 0
    
    analisis_espacial = {lado: (round(sum(tiempos)/len(tiempos), 2) if tiempos else 0) for lado, tiempos in lat_data.items()}
    avg_rect = round(sum(d['rectitud'] for d in traj_metrics)/len(traj_metrics), 2) if traj_metrics else 0
    avg_vel = round(sum(d['velocidad'] for d in traj_metrics)/len(traj_metrics), 2) if traj_metrics else 0

    final_data = {
        "id_paciente": patient_name,
        "estado": "INCOMPLETO" if incompleto else "COMPLETO",
        "comparativa_control": "700 ms y 1100 ms (umbral referencia)",
        "metricas_resumen": {
            "correctas": correctas, "incorrectas": incorrectas,
            "promedio_visual_ms": avg_v, "promedio_auditivo_ms": avg_a,
            "coeficiente_variacion_porcentaje": cv,
            "analisis_lateralidad_ms": analisis_espacial,
            "precision_movimiento_rectitud": avg_rect, # NUEVO
            "velocidad_ejecucion_avg_px_ms": avg_vel # NUEVO
        },
        "tiempos_reaccion_visual": data_results[0],
        "tiempos_reaccion_auditivo": data_results[1],
        "timestamp": time.ctime(),
        "_descripciones_clinicas": {
            "cv": "Estabilidad atencional (Alto % = mucha dispersion)",
            "fatiga": "Diferencia ms inicio-fin (Positivo = cansancio)",
            "interferencia": "Brecha entre procesamiento de vista y oido",
            "lateralidad": "Mide el tiempo de respuesta por zona de la pantalla",
            "rectitud": "Cercania a 1.0 indica trayectoria eficiente. Valores bajos indican falta de control motor.",
            "velocidad_ejecucion": "Eficiencia del movimiento hacia el objetivo segun Ley de Fitts (Fluidez del movimiento)"
        }
    }
    
    test_num = len([f for f in os.listdir("results") if f.startswith(p_id)]) + 1
    filename = os.path.join("results", f"{p_id}_ReaccionMultimodal_prueba{test_num}{'_INCOMPLETO' if incompleto else ''}.json")
    with open(filename, 'w') as f:
        json.dump(final_data, f, indent=4)

# --- GRÁFICOS Y SONIDO ---
def generate_tone(frequency, duration, volume=1.0):
    sample_rate = 44100
    num_samples = int(sample_rate * duration)
    buffer = [int(volume * 32767 * math.sin(2 * math.pi * frequency * i / sample_rate)) for i in range(num_samples)]
    sound_bytes = b''.join([s.to_bytes(2, byteorder='little', signed=True) for s in buffer])
    return pygame.mixer.Sound(buffer=bytes(sound_bytes))

stimulus_sounds = [generate_tone(f, 0.3, 1.0) for f in [220, 247, 262, 294, 330, 349, 392, 440, 494, 523]]
shapes, colors = ['circle', 'square', 'triangle', 'star'], [RED, BLUE, GREEN, (255, 255, 0), (255, 0, 255), (0, 255, 255)]

def draw_shape(shape, color, center, size):
    if shape == 'circle': pygame.draw.circle(screen, color, center, size)
    elif shape == 'square': pygame.draw.rect(screen, color, (center[0]-size, center[1]-size, size*2, size*2))
    elif shape == 'triangle': pygame.draw.polygon(screen, color, [(center[0], center[1]-size), (center[0]-size, center[1]+size), (center[0]+size, center[1]+size)])
    elif shape == 'star':
        pts = [(center[0] + (size if i%2==0 else size//2) * math.cos(i*36*math.pi/180), center[1] + (size if i%2==0 else size//2) * math.sin(i*36*math.pi/180)) for i in range(10)]
        pygame.draw.polygon(screen, color, pts)

def draw_info_icon(pos):
    m_pos = pygame.mouse.get_pos()
    rect = pygame.Rect(pos[0]-35, pos[1]-35, 70, 70)
    is_hover = rect.collidepoint(m_pos)
    color = (0, 150, 255) if is_hover else INFO_BLUE
    pygame.draw.circle(screen, (200, 200, 200), (pos[0]+2, pos[1]+2), 35)
    pygame.draw.circle(screen, WHITE, pos, 35)
    pygame.draw.circle(screen, color, pos, 35, 5)
    f_serif = pygame.font.SysFont("Georgia", int(HEIGHT * 0.06), italic=True, bold=True)
    txt = f_serif.render("i", True, color)
    screen.blit(txt, (pos[0] - txt.get_width()//2, pos[1] - txt.get_height()//2 - 2))
    return rect

def draw_info_box():
    box_w, box_h = 850, 550
    box_rect = pygame.Rect(WIDTH//2 - box_w//2, HEIGHT//2 - box_h//2, box_w, box_h)
    pygame.draw.rect(screen, WHITE, box_rect, border_radius=20)
    pygame.draw.rect(screen, INFO_BLUE, box_rect, 6, border_radius=20)
    inst = ["INSTRUCCIONES DEL TEST:", "Aparecerán estímulos como formas visuales o sonidos.", " - Si ves una FIGURA, hacé click en el botón VERDE.", " - Si escuchas un SONIDO, hacé click en el botón AZUL.", "Intentá responder a ellos lo más rápido que puedas.", "", "Muchos éxitos! Click en el icono para cerrar :)"]
    for i, line in enumerate(inst):
        color = DARK_BLUE if i == 0 else BLACK
        img = font_info.render(line, True, color)
        txt_x, txt_y = box_rect.x + 50, box_rect.y + 50 + (i * 65)
        screen.blit(img, (txt_x, txt_y))
        if i == 0: pygame.draw.line(screen, DARK_BLUE, (txt_x, txt_y + img.get_height() + 2), (txt_x + img.get_width(), txt_y + img.get_height() + 2), 4)


def show_final_notification(name, corr, incorr, results):
    waiting = True
    while waiting:
        screen.fill(GREEN)
        avg_v = sum(results[0])/len(results[0]) if results[0] else 0
        avg_a = sum(results[1])/len(results[1]) if results[1] else 0
        lines = ["¡PRUEBA FINALIZADA!", f"Paciente: {name}", f"Correctas: {corr}", f"Incorrectas: {incorr}", f"Promedio Visual: {avg_v:.2f} ms", f"Promedio Auditivo: {avg_a:.2f} ms", "Click para salir"]
        for i, text in enumerate(lines):
            f = font_large if i == 0 else font
            img = f.render(text, True, BLACK)
            screen.blit(img, (WIDTH//2 - img.get_width()//2, HEIGHT*0.1 + (i*HEIGHT*0.11)))
        pygame.display.flip()
        for e in pygame.event.get():
            if e.type in [pygame.QUIT, pygame.MOUSEBUTTONDOWN, pygame.KEYDOWN]: waiting = False

def show_menu_inicial():
    input_text, show_help = "", False
    while True:
        screen.fill(WHITE)
        title = font_title.render("Test de Reacción Multimodal", True, DARK_BLUE)
        screen.blit(title, (WIDTH//2 - title.get_width()//2, HEIGHT * 0.15))
        info_rect = draw_info_icon((WIDTH - 100, 100))
        input_label = font.render("Nombre del Paciente:", True, BLACK)
        screen.blit(input_label, (WIDTH//2 - input_label.get_width()//2, HEIGHT * 0.38))
        input_box = pygame.Rect(WIDTH//2 - 300, HEIGHT * 0.45, 600, 80)
        pygame.draw.rect(screen, GRAY, input_box, border_radius=15)
        screen.blit(font.render(input_text, True, BLACK), (input_box.x + 20, input_box.y + 10))
        start_btn = pygame.Rect(WIDTH//2 - 200, HEIGHT * 0.7, 400, 100)
        pygame.draw.rect(screen, GREEN, start_btn, border_radius=20)
        st_txt = font.render("COMENZAR", True, WHITE)
        screen.blit(st_txt, (start_btn.centerx - st_txt.get_width()//2, start_btn.centery - st_txt.get_height()//2))
        if show_help: draw_info_box()
        pygame.display.flip()
        for e in pygame.event.get():
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE: return None
                if e.key == pygame.K_BACKSPACE: input_text = input_text[:-1]
                elif e.unicode.isprintable(): input_text += e.unicode
            if e.type == pygame.MOUSEBUTTONDOWN:
                if info_rect.collidepoint(e.pos): show_help = not show_help
                elif start_btn.collidepoint(e.pos): return input_text if input_text else "Paciente"

# --- BUCLE PRINCIPAL ---
name = show_menu_inicial()
if name:
    res, lat_res = {0: [], 1: []}, {k: [] for k in CUADRANTES.keys()}
    traj_metrics, current_path, incorrect_details = [], [], []
    corr = incorr = count = 0
    waiting = False
    next_time = time.time() + 2
    btn_w, btn_h = 420, 140
    b_fig = pygame.Rect(WIDTH//2 - 470, HEIGHT - 220, btn_w, btn_h)
    b_son = pygame.Rect(WIDTH//2 + 50, HEIGHT - 220, btn_w, btn_h)
    
    running = True
    while running:
        screen.fill(WHITE)
        now = time.time()
        if waiting: current_path.append(pygame.mouse.get_pos())
        for e in pygame.event.get():
            if e.type == pygame.QUIT or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE):
                save_results(name, corr, incorr, res, incorrect_details, lat_res, traj_metrics, True)
                running = False
            if e.type == pygame.MOUSEBUTTONDOWN and waiting:
                is_f, is_s = b_fig.collidepoint(e.pos), b_son.collidepoint(e.pos)
                if is_f or is_s:
                    rt = (now - stim_time) * 1000
                    target = b_fig.center if is_f else b_son.center
                    rect, dist = calculate_trajectory_metrics(current_path, target, start_mouse_pos)
                    if (is_f and stim == 0) or (is_s and stim == 1):
                        corr += 1; res[stim].append(rt)
                        if stim == 0: lat_res[cur_quad].append(rt)
                        traj_metrics.append({"rectitud": rect, "velocidad": dist/rt if rt>0 else 0})
                    else: incorr += 1; incorrect_details.append(rt)
                    waiting = False; next_time = now + random.uniform(1.5, 3)
                    current_path = []

        if running:
            if not waiting and now >= next_time and count < 10:
                stim = random.randint(0, 1)
                stim_time, waiting, count = now, True, count + 1
                start_mouse_pos = pygame.mouse.get_pos()
                current_path = [start_mouse_pos]
                if stim == 1: random.choice(stimulus_sounds).play()
                else: 
                    cur_quad = random.choice(list(CUADRANTES.keys()))
                    cur_pos = CUADRANTES[cur_quad]
                    cur_shape, cur_col = random.choice(shapes), random.choice(colors)

            screen.blit(font_hud.render(f"Paciente: {name} | Aciertos: {corr}", True, DARK_BLUE), (40, 40))
            pygame.draw.rect(screen, GREEN, b_fig, border_radius=15)
            pygame.draw.rect(screen, BLUE, b_son, border_radius=15)
            
            if figura_icon and sonido_icon:
                screen.blit(figura_icon, (b_fig.x + 30, b_fig.centery - figura_icon.get_height()//2))
                screen.blit(font_button.render("FIGURA", True, WHITE), (b_fig.x + 160, b_fig.centery - 20))
                screen.blit(sonido_icon, (b_son.x + 30, b_son.centery - sonido_icon.get_height()//2))
                screen.blit(font_button.render("SONIDO", True, WHITE), (b_son.x + 160, b_son.centery - 20))
            
            if waiting and stim == 0: draw_shape(cur_shape, cur_col, (int(cur_pos[0]), int(cur_pos[1])), 120)
            if count == 10 and not waiting:
                save_results(name, corr, incorr, res, incorrect_details, lat_res, traj_metrics)
                show_final_notification(name, corr, incorr, res)
                running = False
            pygame.display.flip()

pygame.quit()