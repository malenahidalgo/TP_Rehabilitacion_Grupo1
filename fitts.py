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
#pygame.mixer.init()

#Variables
intentos = 0
feedback_color = None
feedback_time = 0

WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 36)

# -------------------------------
# PARÁMETROS CLÍNICOS
# -------------------------------
bloques = 3
repeticiones = 8  # obstáculos por bloque

D_min, D_max = 100, 350
W_min, W_max = 20, 60

# -------------------------------
# FUNCIONES
# -------------------------------
def calcular_ID(D, W):
    return math.log2((2*D)/W)

def calcular_distancia_recorrida(path):
    dist = 0
    for i in range(1, len(path)):
        dist += math.sqrt(
            (path[i][0] - path[i-1][0])**2 +
            (path[i][1] - path[i-1][1])**2
        )
    return dist

def generar_target_alternado(bloque, lado):
    # progresión por bloque
    D = D_min + (D_max - D_min) * (bloque / (bloques - 1))
    W = W_max - (W_max - W_min) * (bloque / (bloques - 1))

    center_x, center_y = WIDTH // 2, HEIGHT // 2

    # alternancia izquierda (-1) / derecha (+1)
    x = int(center_x + lado * D)
    y = center_y

    return x, y, D, W

def dibujar_barra_progreso(screen, x, y, ancho, alto, progreso): #barra de progreso
    # fondo (gris)
    pygame.draw.rect(screen, (200,200,200), (x, y, ancho, alto))
    color = color_progreso(progreso)
    #color = (0,200,0) if progreso > 0.5 else (200,150,0)
    # barra de progreso (verde)
    ancho_progreso = int(ancho * progreso)
    pygame.draw.rect(screen, color, (x, y, ancho_progreso, alto))

    # borde
    pygame.draw.rect(screen, (0,0,0), (x, y, ancho, alto), 2)

def generate_tone(frequency, duration, volume=0.5, sample_rate=44100):
    t = np.linspace(0, duration, int(sample_rate * duration), False)

    wave = np.sin(2 * np.pi * frequency * t)

    audio = wave * (2**15 - 1) * volume
    audio = audio.astype(np.int16)

    # convertir a estéreo (2 canales)
    audio_stereo = np.column_stack((audio, audio))

    return pygame.sndarray.make_sound(audio_stereo)

def generate_descending_tone(f_start, f_end, duration, volume=0.5, sample_rate=44100):
    t = np.linspace(0, duration, int(sample_rate * duration), False)

    frequencies = np.linspace(f_start, f_end, t.size)
    wave = np.sin(2 * np.pi * frequencies * t)

    audio = wave * (2**15 - 1) * volume
    audio = audio.astype(np.int16)

    # estéreo
    audio_stereo = np.column_stack((audio, audio))

    return pygame.sndarray.make_sound(audio_stereo)

def play_success_feedback(error, W, mt):
    # normalizaciones
    precision = max(0, 1 - (error / W))   # 0 a 1
    velocidad = min(1, 1 / (mt + 0.001))  # evitar división por 0
    # combinar ambas (podés ajustar pesos)
    score = 0.6 * precision + 0.4 * velocidad
    # mapear a frecuencia
    freq = 300 + (700 * score)  # rango 300–1000 Hz
    sound = generate_tone(freq, 0.15, 0.4)
    sound.play()

def play_error_feedback(error, W):
    severity = min(1, error / (W*2))  # qué tan lejos erró
    freq_start = 400 - (200 * severity)
    freq_end = 150
    sound = generate_descending_tone(freq_start, freq_end, 0.2, 0.4)
    sound.play()

def mostrar_resultados_paciente(screen, font, resultados):
    mostrando = True

    # interpretación simple
    if resultados["accuracy"] < 50:
        mensaje = "Seguí practicando"
    elif resultados["accuracy"] < 80:
        mensaje = "¡Buen trabajo!"
    else:
        mensaje = "¡Excelente!"

    while mostrando:
        screen.fill((240,240,240))

        titulo = font.render("RESULTADO", True, (0,0,0))
        screen.blit(titulo, (320, 50))

        lineas = [
            f"Puntaje: {resultados['puntaje']}",
            f"Precisión: {resultados['accuracy']:.1f} %",
            "",
            mensaje,
            "",
            "Presione ESC para salir"
        ]

        for i, linea in enumerate(lineas):
            texto = font.render(linea, True, (0,0,0))
            screen.blit(texto, (250, 140 + i*50))

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                mostrando = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    mostrando = False

        pygame.display.flip()
        clock.tick(60)

def calcular_metricas(data, puntaje, intentos):
    if len(data) == 0:
        return None

    MT = data[:,0]
    errores = data[:,1]
    ID = data[:,2]

    # ajuste lineal
    coef = np.polyfit(ID, MT, 1)
    b = coef[0]

    # métricas básicas
    mt_mean = np.mean(MT)
    error_mean = np.mean(errores)
    accuracy = (puntaje / intentos) * 100 if intentos > 0 else 0

    # throughput simple
    # evitar divisiones por 0
    validos = MT > 0

    if np.any(validos): #sino me sale ID/0 y me da infinito
        TP = np.mean(ID[validos] / MT[validos])
    else:
        TP = 0

    return {
        "puntaje": puntaje,
        "intentos": intentos,
        "accuracy": accuracy,
        "mt": mt_mean,
        "error": error_mean,
        "b": b,
        "tp": TP
    }

def ingresar_paciente(screen, font):
    input_text = ""
    activo = True

    while activo:
        screen.fill((240,240,240))

        titulo = font.render("Ingrese ID del paciente:", True, (0,0,0))
        screen.blit(titulo, (220, 200))

        texto = font.render(input_text, True, (0,0,255))
        screen.blit(texto, (220, 250))

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return None

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    activo = False
                elif event.key == pygame.K_BACKSPACE:
                    input_text = input_text[:-1]
                else:
                    input_text += event.unicode

        pygame.display.flip()
        clock.tick(60)

    return input_text

def color_progreso(p):
    p = max(0, min(1, p))  # asegurar rango 0-1

    if p < 0.5:
        # rojo → amarillo
        r = 255
        g = int(255 * (p * 2))
        b = 0
    else:
        # amarillo → verde
        r = int(255 * (1 - (p - 0.5) * 2))
        g = 255
        b = 0

    return (r, g, b)

def guardar_resultados_json(resultados):
    # crear carpeta si no existe
    os.makedirs("results", exist_ok=True)

    datos = {
        "paciente_id": "001",  # podés hacerlo dinámico
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "resultados": resultados
    }

    nombre_archivo = f"results/resultado_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    with open(nombre_archivo, "w") as f:
        json.dump(datos, f, indent=4)

    print("Archivo guardado en:", nombre_archivo)
    

# -------------------------------
# VARIABLES
# -------------------------------
paciente_id = ingresar_paciente(screen, font)
data = []
path = []
tracking = False
start_time = None

bloque_actual = 0
repeticion_actual = 0
lado = 1  # empieza a la derecha

puntaje = 0

target = generar_target_alternado(bloque_actual, lado)

running = True

# -------------------------------
# LOOP PRINCIPAL
# -------------------------------
while running:
    screen.fill((255,255,255))

    # diseño el target
    x, y, D, W = target
    pygame.draw.circle(screen, (0,0,255), (x,y), int(W))

    # mostrar feedback por 200 ms
    if feedback_color and (time.time() - feedback_time < 0.4):
        pygame.draw.circle(screen, feedback_color, (x,y), int(W)+12, 10)

    # texto en pantalla
    texto = font.render(f"Puntaje: {puntaje}", True, (0,0,0))
    screen.blit(texto, (20,20))

    texto2 = font.render(f"Bloque: {bloque_actual+1}/{bloques}", True, (0,0,0))
    screen.blit(texto2, (20,60))

    texto3 = font.render(f"Obstáculo: {repeticion_actual+1}/{repeticiones}", True, (0,0,0))
    screen.blit(texto3, (20,100))

    texto4 = font.render(f"Intentos: {intentos}", True, (0,0,0))
    screen.blit(texto4, (20,140))

    progreso = repeticion_actual / repeticiones
    texto_prog = font.render(f"Progreso nivel: {int(progreso*100)}%", True, (0,0,0))
    screen.blit(texto_prog, (20, 160))
    dibujar_barra_progreso(screen, 20, 180, 300, 25, progreso)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.MOUSEBUTTONDOWN:  #ACÁ DETECTO EL CLICK
            mouse_x, mouse_y = pygame.mouse.get_pos()

            intentos += 1

            error = math.sqrt((mouse_x-x)**2 + (mouse_y-y)**2)

            if error <= W:  # HIT
                mt = time.time() - start_time if start_time else 0
                ID = calcular_ID(D, W)
                distancia = calcular_distancia_recorrida(path)

                data.append([mt, error, ID, distancia, W, bloque_actual, D])

                puntaje += 1

                # feedback visual
                feedback_color = (0,255,0)
                feedback_time = time.time()

                # feedback auditivo CORRECTO
                play_success_feedback(error, W, mt)

                repeticion_actual += 1
                lado *= -1

                if repeticion_actual >= repeticiones:
                    repeticion_actual = 0
                    bloque_actual += 1

                    if bloque_actual >= bloques:
                        running = False
                        break

                target = generar_target_alternado(bloque_actual, lado)

                path = []
                start_time = time.time()
                tracking = True

            else:  # MISS
                feedback_color = (255,0,0)
                feedback_time = time.time()

                #  feedback auditivo error
                play_error_feedback(error, W)

    if tracking:
        path.append(pygame.mouse.get_pos())

    pygame.display.flip()
    clock.tick(60)


# -------------------------------
# ANÁLISIS
# -------------------------------
data = np.array(data)

if len(data) > 0:
    MT = data[:,0]
    ID = data[:,2]

    coef = np.polyfit(ID, MT, 1)

    print("Pendiente (b):", coef[0])
    print("Intercepto (a):", coef[1])
    print("Puntaje total:", puntaje)

pygame.event.clear()
screen.fill((0,0,0))
pygame.display.flip()

resultados = calcular_metricas(data, puntaje, intentos)

if resultados is not None:
    pygame.event.clear()
    screen.fill((0,0,0))
    pygame.display.flip()

    guardar_resultados_json(resultados)
    mostrar_resultados_paciente(screen, font, resultados)

pygame.quit()
