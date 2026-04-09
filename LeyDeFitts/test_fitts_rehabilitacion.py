import pygame
import time
import math
import numpy as np
import pygame.mixer
import json
import os
from datetime import datetime

pygame.mixer.pre_init(44100, -16, 1, 512)
pygame.init()

# ------------------------------- 
# VENTANA REDIMENSIONABLE
# -------------------------------
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
pygame.display.set_caption("Rehabilitación ACV - Test de Fitts")

clock = pygame.time.Clock()

# --- FUENTES ---
f_size = int(HEIGHT * 0.06)
font        = pygame.font.SysFont("Helvetica", f_size)
font_title  = pygame.font.SysFont("Georgia",   int(f_size * 1.5), bold=True)
font_large  = pygame.font.SysFont("Helvetica", int(f_size * 1.5), bold=True)
font_hud    = pygame.font.SysFont("Helvetica", int(f_size * 0.8))
font_info   = pygame.font.SysFont("Helvetica", int(f_size * 0.60), bold=True)
font_button = pygame.font.SysFont("Helvetica", int(f_size * 0.7), bold=True)

# Alias para compatibilidad con el resto del código
font_big   = font_large
font_small = font_info

# ------------------------------- 
# VARIABLES GLOBALES
# -------------------------------
intentos = 0
feedback_color = None
feedback_time = 0

# ------------------------------- 
# PARÁMETROS CLÍNICOS
# -------------------------------
bloques = 4           # 3 fijos + 1 con círculos móviles
repeticiones = 8
D_min, D_max = 100, 350
W_min, W_max = 20, 60

# Nivel 4 — target en posicion aleatoria por toda la pantalla
W_nivel4 = 25         # radio fijo (pequeño)

# ------------------------------- 
# FUNCIONES AUXILIARES
# -------------------------------

def get_size():
    return screen.get_width(), screen.get_height()

def calcular_ID(D, W):
    return math.log2((2 * D) / W)

def calcular_distancia_recorrida(path):
    dist = 0
    for i in range(1, len(path)):
        dist += math.sqrt(
            (path[i][0] - path[i-1][0])**2 +
            (path[i][1] - path[i-1][1])**2
        )
    return dist

def generar_target_alternado(bloque, lado):
    W, H = get_size()
    D = D_min + (D_max - D_min) * (bloque / (bloques - 1))
    w = W_max - (W_max - W_min) * (bloque / (bloques - 1))
    center_x, center_y = W // 2, H // 2
    x = int(center_x + lado * D)
    y = center_y
    return x, y, D, w

def generar_target_aleatorio():
    """Nivel 4: aparece en cualquier lugar de la pantalla visible."""
    import random
    W, H = get_size()
    hud_ancho = 355          # dejar libre el panel HUD izquierdo
    hud_alto  = 215
    margen = W_nivel4 + 10
    # evitar zona HUD (esquina superior izquierda)
    while True:
        x = random.randint(margen, W - margen)
        y = random.randint(margen, H - margen)
        en_hud = (x < hud_ancho and y < hud_alto)
        if not en_hud:
            break
    D = math.sqrt((x - W//2)**2 + (y - H//2)**2) or 1
    return x, y, D, W_nivel4

def dibujar_barra_progreso(surface, x, y, ancho, alto, progreso):
    pygame.draw.rect(surface, (200, 200, 200), (x, y, ancho, alto))
    color = color_progreso(progreso)
    ancho_progreso = int(ancho * progreso)
    pygame.draw.rect(surface, color, (x, y, ancho_progreso, alto))
    pygame.draw.rect(surface, (0, 0, 0), (x, y, ancho, alto), 2)

def generate_tone(frequency, duration, volume=0.5, sample_rate=44100):
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    wave = np.sin(2 * np.pi * frequency * t)
    audio = (wave * (2**15 - 1) * volume).astype(np.int16)
    audio_stereo = np.column_stack((audio, audio))
    return pygame.sndarray.make_sound(audio_stereo)

def generate_descending_tone(f_start, f_end, duration, volume=0.5, sample_rate=44100):
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    frequencies = np.linspace(f_start, f_end, t.size)
    wave = np.sin(2 * np.pi * frequencies * t)
    audio = (wave * (2**15 - 1) * volume).astype(np.int16)
    audio_stereo = np.column_stack((audio, audio))
    return pygame.sndarray.make_sound(audio_stereo)

def play_success_feedback(error, W, mt):
    precision = max(0, 1 - (error / W))
    velocidad = min(1, 1 / (mt + 0.001))
    score = 0.6 * precision + 0.4 * velocidad
    freq = 300 + (700 * score)
    sound = generate_tone(freq, 0.15, 0.4)
    sound.play()

def play_error_feedback(error, W):
    severity = min(1, error / (W * 2))
    freq_start = 400 - (200 * severity)
    freq_end = 150
    sound = generate_descending_tone(freq_start, freq_end, 0.2, 0.4)
    sound.play()

def color_progreso(p):
    p = max(0, min(1, p))
    if p < 0.5:
        r = 255
        g = int(255 * (p * 2))
        b = 0
    else:
        r = int(255 * (1 - (p - 0.5) * 2))
        g = 255
        b = 0
    return (r, g, b)

def calcular_metricas(data, puntaje, intentos):
    if len(data) == 0:
        return None
    MT        = data[:, 0]   # tiempo de movimiento
    errores   = data[:, 1]   # error espacial
    ID        = data[:, 2]   # indice de dificultad
    distancias= data[:, 3]   # trayectoria del cursor
    bloques_v = data[:, 5]   # bloque de cada intento
    coef = np.polyfit(ID, MT, 1)
    b = coef[0]
    validos = MT > 0
    TP = np.mean(ID[validos] / MT[validos]) if np.any(validos) else 0
    accuracy = (puntaje / intentos) * 100 if intentos > 0 else 0

    # detalle por intento
    intentos_detalle = []
    for i in range(len(MT)):
        tp_i = (ID[i] / MT[i]) if MT[i] > 0 else 0
        intentos_detalle.append({
            "intento": i + 1,
            "bloque": int(bloques_v[i]) + 1,
            "MT_s": round(float(MT[i]), 4),
            "error_espacial_px": round(float(errores[i]), 4),
            "ID_bits": round(float(ID[i]), 4),
            "TP_bits_s": round(float(tp_i), 4),
            "trayectoria_px": round(float(distancias[i]), 4)
        })

    return {
        "puntaje": puntaje,
        "intentos": intentos,
        "accuracy": accuracy,
        "mt": float(np.mean(MT)),
        "error": float(np.mean(errores)),
        "b": float(b),
        "tp": float(TP),
        "trayectoria_mean": float(np.mean(distancias)),
        "intentos_detalle": intentos_detalle
    }

def guardar_resultados_json(resultados, paciente_id):
    os.makedirs("results", exist_ok=True)
    datos = {
        "paciente_id": paciente_id,
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "modulo": "Ley de Fitts",
        "descripcion_metricas": {
            "tiempo_movimiento_MT": "Tiempo transcurrido entre la aparicion del objetivo y su seleccion (segundos).",
            "error_espacial": "Distancia en pixeles entre el punto de click y el centro del objetivo.",
            "indice_dificultad_ID": "Calculado como log2(2D/W), donde D es la distancia al objetivo y W su ancho (bits).",
            "throughput_TP": "Metrica que integra velocidad y precision: TP = ID / MT. Promedio de intentos validos, en bits por segundo.",
            "precision_accuracy": "Porcentaje de aciertos sobre el total de intentos realizados.",
            "trayectoria": "Distancia total recorrida por el cursor en pixeles. Indicador indirecto de control motor y eficiencia del movimiento."
        },
        "resumen": {
            "puntaje": resultados.get("puntaje", 0),
            "intentos_totales": resultados.get("intentos", 0),
            "precision_porcentaje": round(resultados.get("accuracy", 0), 2),
            "MT_promedio_s": round(resultados.get("mt", 0), 4),
            "error_espacial_promedio_px": round(resultados.get("error", 0), 4),
            "throughput_TP_promedio_bits_s": round(resultados.get("tp", 0), 4),
            "trayectoria_promedio_px": round(resultados.get("trayectoria_mean", 0), 4),
            "pendiente_b_fitts": round(resultados.get("b", 0), 4)
        },
        "intentos_detalle": resultados.get("intentos_detalle", [])
    }
    nombre_archivo = f"results/resultado_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(nombre_archivo, "w", encoding="utf-8") as f:
        json.dump(datos, f, indent=4, ensure_ascii=False)
    print("Archivo guardado en:", nombre_archivo)

# ------------------------------- 
# DIBUJAR ESTRELLAS
# -------------------------------
def dibujar_estrella(surface, cx, cy, radio_ext, radio_int, color):
    puntos = []
    for i in range(10):
        angulo = math.pi / 2 + i * (2 * math.pi / 10)
        r = radio_ext if i % 2 == 0 else radio_int
        puntos.append((cx + r * math.cos(angulo), cy + r * math.sin(angulo)))
    pygame.draw.polygon(surface, color, puntos)

def dibujar_estrellas_resultado(surface, accuracy):
    W, H = surface.get_width(), surface.get_height()
    if accuracy >= 80:
        num_estrellas = 3
        msg = "¡Excelente!"
        color_msg = (0, 160, 0)
    elif accuracy >= 50:
        num_estrellas = 2
        msg = "¡Muy bien!"
        color_msg = (200, 140, 0)
    else:
        num_estrellas = 1
        msg = "¡Seguí practicando!"
        color_msg = (180, 60, 0)

    # Dibujar estrellas
    AMARILLO = (255, 210, 0)
    GRIS = (200, 200, 200)
    total = 3
    radio_ext = 38
    radio_int = 16
    espaciado = 100
    inicio_x = W // 2 - (total - 1) * espaciado // 2
    y_estrella = H // 2 + 10

    for i in range(total):
        color = AMARILLO if i < num_estrellas else GRIS
        dibujar_estrella(surface, inicio_x + i * espaciado, y_estrella, radio_ext, radio_int, color)
        # borde
        dibujar_estrella(surface, inicio_x + i * espaciado, y_estrella, radio_ext, radio_int, (0,0,0))
        pygame.draw.polygon(surface, color,
            [(inicio_x + i * espaciado + radio_ext * math.cos(math.pi/2 + j*(2*math.pi/10)),
              y_estrella + radio_ext * math.sin(math.pi/2 + j*(2*math.pi/10))) for j in range(10)])
        # redibujar correctamente
        puntos = []
        for k in range(10):
            angulo = math.pi / 2 + k * (2 * math.pi / 10)
            r = radio_ext if k % 2 == 0 else radio_int
            puntos.append((inicio_x + i * espaciado + r * math.cos(angulo),
                           y_estrella + r * math.sin(angulo)))
        pygame.draw.polygon(surface, color, puntos)
        pygame.draw.polygon(surface, (80, 80, 80), puntos, 2)

    return msg, color_msg, num_estrellas

# ------------------------------- 
# PANTALLA: INGRESAR PACIENTE
# -------------------------------
def ingresar_paciente():
    input_text = ""
    activo = True
    while activo:
        W, H = get_size()
        screen.fill((240, 240, 240))

        titulo = font_big.render("Rehabilitación ACV", True, (30, 80, 180))
        screen.blit(titulo, (W // 2 - titulo.get_width() // 2, 80))

        sub = font.render("Ingrese ID del paciente:", True, (0, 0, 0))
        screen.blit(sub, (W // 2 - sub.get_width() // 2, 200))

        # caja de texto
        caja = pygame.Rect(W // 2 - 150, 245, 300, 44)
        pygame.draw.rect(screen, (255, 255, 255), caja)
        pygame.draw.rect(screen, (30, 80, 180), caja, 2)
        texto = font.render(input_text, True, (0, 0, 200))
        screen.blit(texto, (caja.x + 10, caja.y + 6))

        hint = font_small.render("Presione ENTER para continuar", True, (100, 100, 100))
        screen.blit(hint, (W // 2 - hint.get_width() // 2, 310))

        esc_hint = font_small.render("ESC para salir", True, (160, 60, 60))
        screen.blit(esc_hint, (W // 2 - esc_hint.get_width() // 2, H - 40))

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
            if event.type == pygame.VIDEORESIZE:
                pass
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    exit()
                elif event.key == pygame.K_RETURN and input_text.strip():
                    activo = False
                elif event.key == pygame.K_BACKSPACE:
                    input_text = input_text[:-1]
                elif event.unicode and event.unicode.isprintable():
                    input_text += event.unicode

        pygame.display.flip()
        clock.tick(60)
    return input_text.strip()

# ------------------------------- 
# PANTALLA: CONSIGNA INICIAL
# -------------------------------
def mostrar_consigna():
    esperando = True
    while esperando:
        W, H = get_size()
        screen.fill((245, 248, 255))

        titulo = font_big.render("¿Cómo jugar?", True, (30, 80, 180))
        screen.blit(titulo, (W // 2 - titulo.get_width() // 2, 60))

        consigna = [
            "Aparecera un circulo azul en la pantalla.",
            "Tu tarea es hacer CLIC sobre el circulo",
            "lo mas rapido y preciso que puedas.",
            "",
            "El juego tiene 4 niveles de dificultad.",
            "Cada nivel los circulos seran mas pequenos",
            "y estaran mas lejos.",
            "",
            "En el nivel 4 (BONUS): el circulo puede aparecer",
            "por toda la pantalla. Intenta atraparlo!",
            "",
            "Podes salir en cualquier momento con ESC.",
        ]

        y_start = 150
        for i, linea in enumerate(consigna):
            color = (30, 80, 180) if linea.startswith("Tu tarea") else (40, 40, 40)
            t = font_small.render(linea, True, color)
            screen.blit(t, (W // 2 - t.get_width() // 2, y_start + i * 34))

        # Botón iniciar
        btn = pygame.Rect(W // 2 - 120, H - 100, 240, 50)
        pygame.draw.rect(screen, (30, 130, 80), btn, border_radius=10)
        btn_txt = font.render("¡Comenzar!", True, (255, 255, 255))
        screen.blit(btn_txt, (btn.x + btn.width // 2 - btn_txt.get_width() // 2,
                               btn.y + btn.height // 2 - btn_txt.get_height() // 2))

        esc_hint = font_small.render("ESC para salir", True, (160, 60, 60))
        screen.blit(esc_hint, (W // 2 - esc_hint.get_width() // 2, H - 30))

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    exit()
                if event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                    esperando = False
            if event.type == pygame.MOUSEBUTTONDOWN:
                if btn.collidepoint(event.pos):
                    esperando = False

        pygame.display.flip()
        clock.tick(60)

# ------------------------------- 
# PANTALLA: ENTRE NIVELES
# -------------------------------
def mostrar_entre_niveles(bloque_completado, puntaje_parcial, intentos_parciales):
    esperando = True
    accuracy = (puntaje_parcial / intentos_parciales * 100) if intentos_parciales > 0 else 0
    siguiente = bloque_completado + 1

    t_inicio = time.time()
    ESPERA_AUTO = 4  # segundos antes de continuar automáticamente

    while esperando:
        W, H = get_size()
        screen.fill((220, 245, 220))

        # Título
        titulo = font_big.render(f"Nivel {bloque_completado} completado!", True, (30, 130, 60))
        screen.blit(titulo, (W // 2 - titulo.get_width() // 2, 60))

        # Estrellas
        msg, color_msg, _ = dibujar_estrellas_resultado(screen, accuracy)
        msg_surf = font.render(msg, True, color_msg)
        screen.blit(msg_surf, (W // 2 - msg_surf.get_width() // 2, H // 2 + 60))

        acc_txt = font.render(f"Precisión en este nivel: {accuracy:.1f}%", True, (60, 60, 60))
        screen.blit(acc_txt, (W // 2 - acc_txt.get_width() // 2, H // 2 + 110))

        if siguiente <= bloques:
            sig_txt = font.render(f"Próximo: Nivel {siguiente} — ¡más desafiante!", True, (30, 80, 180))
            screen.blit(sig_txt, (W // 2 - sig_txt.get_width() // 2, H // 2 + 155))

        # Cuenta regresiva
        restante = max(0, ESPERA_AUTO - int(time.time() - t_inicio))
        timer_txt = font_small.render(f"Continúa en {restante}s  (o presioná ENTER / clic)", True, (120, 120, 120))
        screen.blit(timer_txt, (W // 2 - timer_txt.get_width() // 2, H - 60))

        esc_hint = font_small.render("ESC para salir", True, (160, 60, 60))
        screen.blit(esc_hint, (W // 2 - esc_hint.get_width() // 2, H - 30))

        if time.time() - t_inicio >= ESPERA_AUTO:
            esperando = False

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    exit()
                if event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                    esperando = False
            if event.type == pygame.MOUSEBUTTONDOWN:
                esperando = False

        pygame.display.flip()
        clock.tick(60)

# ------------------------------- 
# PANTALLA: RESULTADOS FINALES
# -------------------------------
def mostrar_resultados_paciente(resultados):
    mostrando = True
    accuracy = resultados["accuracy"]

    while mostrando:
        W, H = get_size()
        screen.fill((220, 245, 220))  # verde claro

        titulo = font_big.render("RESULTADO FINAL", True, (30, 80, 180))
        screen.blit(titulo, (W // 2 - titulo.get_width() // 2, 40))

        # Estrellas
        msg, color_msg, _ = dibujar_estrellas_resultado(screen, accuracy)

        msg_surf = font.render(msg, True, color_msg)
        screen.blit(msg_surf, (W // 2 - msg_surf.get_width() // 2, H // 2 + 60))

        lineas = [
            f"Puntaje total: {resultados['puntaje']} / {resultados['intentos']}",
            f"Precisión: {accuracy:.1f}%",
        ]
        for i, linea in enumerate(lineas):
            t = font.render(linea, True, (40, 40, 40))
            screen.blit(t, (W // 2 - t.get_width() // 2, H // 2 + 110 + i * 40))

        esc_txt = font_small.render("Presione ESC para salir", True, (100, 100, 100))
        screen.blit(esc_txt, (W // 2 - esc_txt.get_width() // 2, H - 40))

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                mostrando = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    mostrando = False

        pygame.display.flip()
        clock.tick(60)

# ------------------------------- 
# FLUJO PRINCIPAL
# -------------------------------
paciente_id = ingresar_paciente()
mostrar_consigna()

data = []
path = []
tracking = False
start_time = None
bloque_actual = 0
repeticion_actual = 0
lado = 1
puntaje = 0
intentos = 0
puntaje_bloque = 0
intentos_bloque = 0

target = generar_target_alternado(bloque_actual, lado)
running = True

# ------------------------------- 
# LOOP PRINCIPAL
# -------------------------------
while running:
    W, H = get_size()

    es_nivel_aleatorio = (bloque_actual == bloques - 1)  # nivel 4

    x, y, D, Wt = target

    # --- Fondo ---
    screen.fill((255, 255, 255))

    # --- Target ---
    color_target = (30, 80, 200) if es_nivel_aleatorio else (30, 80, 200)
    pygame.draw.circle(screen, color_target, (x, y), int(Wt))

    # Feedback visual ring
    if feedback_color and (time.time() - feedback_time < 0.4):
        pygame.draw.circle(screen, feedback_color, (x, y), int(Wt) + 12, 10)

    # --- HUD ---
    #pygame.draw.rect(screen, (230, 235, 245), (0, 0, 340, 210))

    nivel_label = f"NIVEL 4 - BONUS (libre)" if es_nivel_aleatorio else f"Nivel: {bloque_actual + 1} / {bloques}"
    texto  = font.render(f"Puntaje: {puntaje}", True, (0, 0, 0))
    texto2 = font_hud.render(nivel_label, True, (160, 30, 30) if es_nivel_aleatorio else (0, 0, 0))
    texto3 = font_hud.render(f"Objetivo: {repeticion_actual + 1} / {repeticiones}", True, (0, 0, 0))
    texto4 = font_hud.render(f"Intentos: {intentos}", True, (0, 0, 0))

    screen.blit(texto,  (15, 10))
    screen.blit(texto2, (15, 48))
    screen.blit(texto3, (15, 86))
    screen.blit(texto4, (15, 126))

    progreso = repeticion_actual / repeticiones
    dibujar_barra_progreso(screen, 15, 160, 300, 22, progreso)
    prog_label = font_small.render(f"Progreso nivel: {int(progreso * 100)}%", True, (0, 0, 0))
    screen.blit(prog_label, (15, 186))

    esc_hint = font_small.render("ESC - Salir", True, (180, 60, 60))
    screen.blit(esc_hint, (W - esc_hint.get_width() - 15, 12))

    # --- Eventos ---
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.VIDEORESIZE:
            screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False

        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_x, mouse_y = pygame.mouse.get_pos()
            intentos += 1
            intentos_bloque += 1
            error = math.sqrt((mouse_x - x)**2 + (mouse_y - y)**2)

            if error <= Wt:
                # HIT
                mt = time.time() - start_time if start_time else 0
                ID = calcular_ID(D, Wt)
                distancia = calcular_distancia_recorrida(path)
                data.append([mt, error, ID, distancia, Wt, bloque_actual, D])
                puntaje += 1
                puntaje_bloque += 1

                feedback_color = (0, 220, 0)
                feedback_time = time.time()
                play_success_feedback(error, Wt, mt)

                repeticion_actual += 1
                lado *= -1

                if repeticion_actual >= repeticiones:
                    repeticion_actual = 0
                    bloque_completado = bloque_actual + 1
                    bloque_actual += 1

                    if bloque_actual >= bloques:
                        running = False
                        break

                    mostrar_entre_niveles(bloque_completado, puntaje_bloque, intentos_bloque)
                    puntaje_bloque = 0
                    intentos_bloque = 0

                # Generar siguiente target según el nivel
                if bloque_actual == bloques - 1:
                    target = generar_target_aleatorio()
                else:
                    target = generar_target_alternado(bloque_actual, lado)

                path = []
                start_time = time.time()
                tracking = True

            else:
                # MISS
                feedback_color = (220, 0, 0)
                feedback_time = time.time()
                play_error_feedback(error, Wt)

    if tracking:
        path.append(pygame.mouse.get_pos())

    pygame.display.flip()
    clock.tick(60)

# ------------------------------- 
# ANÁLISIS Y RESULTADOS
# -------------------------------
data = np.array(data)
if len(data) > 0:
    MT = data[:, 0]
    ID = data[:, 2]
    coef = np.polyfit(ID, MT, 1)
    print("Pendiente (b):", coef[0])
    print("Intercepto (a):", coef[1])
    print("Puntaje total:", puntaje)

    resultados = calcular_metricas(data, puntaje, intentos)
    if resultados is not None:
        guardar_resultados_json(resultados, paciente_id)
        mostrar_resultados_paciente(resultados)

pygame.quit()
