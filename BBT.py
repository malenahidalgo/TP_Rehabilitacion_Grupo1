import pygame
import json
import os
import math
import re
import time

# --- Configuración de Constantes ---
WIDTH, HEIGHT = 1000, 600
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
GREEN = (0, 255, 0)
GRAY = (200, 200, 200)

BLOCK_SIZE = 40
FPS = 60
# Conversión de píxeles a mm: 96 DPI (estándar de pantalla)
# 96 píxeles = 25.4 mm (1 pulgada)
PX_TO_MM = 25.4 / 96  # ≈ 0.2646 mm/píxel

class BBTGame:
    def __init__(self):
        pygame.init()
        pygame.mixer.init()  # Inicializar el mixer de audio
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Digital Box and Block Test - Evaluación Post-ACV")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Helvetica", 18)
        self.font_large = pygame.font.SysFont("Helvetica", 36, bold=True)
        self.font_medium = pygame.font.SysFont("Helvetica", 28)
        self.font_small = pygame.font.SysFont("Helvetica", 20)
        
        # Áreas de juego
        self.box_left = pygame.Rect(50, 150, 350, 300)
        self.box_right = pygame.Rect(600, 150, 350, 300)
        self.partition = pygame.Rect(485, 150, 30, 300)
        
        self.patient_name = ""
        self.trial_mode = None  # "training" o "test"
        self.sound_enabled = True  # Control de sonidos
        self.current_test_number = None  # Número de prueba para el test actual
        self.create_sounds()  # Crear sonidos
        self.reset_session()

    def create_sounds(self):
        """Crea sonidos programáticamente para efectos de audio"""
        # Sonido de golpe/colisión (tono bajo y corto)
        self.error_sound = self.generate_descending_tone(400, 200, 0.25, 0.3)  # 400Hz a 200Hz, 250ms

        # Sonido de éxito (tono alto y agradable)
        self.success_sound = self.generate_tone(400, 0.2, 0.4)  # 400Hz, 200ms, volumen 0.4

        # Sonido de error/caída (tono descendente)
        self.collision_sound = self.generate_tone(200, 0.15, 0.3)  # 200Hz, 150ms, volumen 0.3
        
        # Sonido de selección (tono suave)
        self.select_sound = self.generate_tone(300, 0.1, 0.2)  # 300Hz, 100ms, volumen 0.2

    def generate_tone(self, frequency, duration, volume=0.5):
        """Genera un tono simple"""
        sample_rate = 44100
        num_samples = int(sample_rate * duration)

        # Crear onda sinusoidal
        buffer = []
        for i in range(num_samples):
            sample = int(volume * 32767 * math.sin(2 * math.pi * frequency * i / sample_rate))
            buffer.append(sample)

        # Convertir a bytes
        sound_bytes = b''
        for sample in buffer:
            sound_bytes += sample.to_bytes(2, byteorder='little', signed=True)

        # Crear objeto Sound
        sound = pygame.mixer.Sound(buffer=bytes(sound_bytes))
        return sound

    def generate_descending_tone(self, start_freq, end_freq, duration, volume=0.5):
        """Genera un tono descendente"""
        sample_rate = 44100
        num_samples = int(sample_rate * duration)

        buffer = []
        for i in range(num_samples):
            # Frecuencia descendente lineal
            freq = start_freq + (end_freq - start_freq) * (i / num_samples)
            sample = int(volume * 32767 * math.sin(2 * math.pi * freq * i / sample_rate))
            buffer.append(sample)

        sound_bytes = b''
        for sample in buffer:
            sound_bytes += sample.to_bytes(2, byteorder='little', signed=True)

        sound = pygame.mixer.Sound(buffer=bytes(sound_bytes))
        return sound

    def reset_session(self):
        self.blocks = []
        colors = [RED, BLUE, GREEN]
        for i in range(10):
            # Generar bloques dentro del área de box_left actual
            x = self.box_left.x + 20 + (i*30) % (self.box_left.width - 60)
            y = self.box_left.y + 20 + (i*25) % (self.box_left.height - 60)
            rect = pygame.Rect(x, y, BLOCK_SIZE, BLOCK_SIZE)
            self.blocks.append({'rect': rect, 'color': colors[i%3], 'original_pos': rect.topleft})
        
        self.selected_block = None
        self.metrics = {
            "velocidades_px_frame": [],
            "velocidades_mm_s": [],
            "aceleraciones_px_frame2": [],
            "aceleraciones_mm_s2": [],
            "exitos": 0,
            "errores_pared": 0,
            "caidas_mouse": 0,
            "vibraciones": 0,
            # Métricas de espasmos
            "picos_aceleracion_alta": 0,
            "cambios_direccion_bruscos": 0,
            "microMovimientos": 0,
            "duracion_espasmo_ms": 0,
            "eventos_espasmo": []  # Lista de timestamps y duraciones
        }
        self.last_pos = None
        self.last_vel = 0
        self.last_angle = 0
        self.pos_history = []  # Para calcular cambios de dirección
        self.start_time = time.time()
        self.espasmo_inicio = None
        self.prev_movement_time = time.time()

    def calculate_next_test_number(self):
        """Calcula el próximo número de prueba para el paciente actual"""
        if not os.path.exists('results'):
            os.makedirs('results')
        
        patient_id = self.patient_name.strip().replace(" ", "_")
        if not patient_id:
            patient_id = "Paciente"
        patient_id = "".join(ch for ch in patient_id if ch.isalnum() or ch in ("_", "-"))
        
        # Buscar todos los archivos del paciente para determinar el próximo número
        existing = [f for f in os.listdir("results") if f.startswith(patient_id + "_") and f.endswith(".json")]
        max_prueba = 0
        for fname in existing:
            m = re.match(rf"^{re.escape(patient_id)}_.*_prueba(\d+)\.json$", fname)
            if m:
                num = int(m.group(1))
                max_prueba = max(max_prueba, num)
        
        self.current_test_number = max_prueba + 1

    def calculate_kinematics(self, current_pos):
        current_time = time.time()
        
        if self.last_pos:
            dx = current_pos[0] - self.last_pos[0]
            dy = current_pos[1] - self.last_pos[1]
            dist = math.sqrt(dx**2 + dy**2)
            
            # Velocidad en píxeles/frame
            vel_px_frame = dist
            # Velocidad en mm/s
            vel_mm_s = vel_px_frame * PX_TO_MM * FPS
            
            self.metrics["velocidades_px_frame"].append(vel_px_frame)
            self.metrics["velocidades_mm_s"].append(vel_mm_s)
            
            # Aceleración en píxeles/frame²
            accel_px_frame2 = abs(vel_px_frame - self.last_vel)
            # Aceleración en mm/s²
            accel_mm_s2 = accel_px_frame2 * PX_TO_MM * FPS * FPS
            
            self.metrics["aceleraciones_px_frame2"].append(accel_px_frame2)
            self.metrics["aceleraciones_mm_s2"].append(accel_mm_s2)
            
            # Detección de ESPASMOS
            
            # 1. Picos de aceleración alta (> 50 px/frame²)
            if accel_px_frame2 > 50:
                self.metrics["picos_aceleracion_alta"] += 1
                if self.espasmo_inicio is None:
                    self.espasmo_inicio = current_time
            
            # 2. Cambios de dirección bruscos
            # Calcular ángulo del movimiento actual
            if dist > 0:
                current_angle = math.atan2(dy, dx)
                self.pos_history.append((current_pos, current_angle))
                
                # Mantener historial de últimas 5 posiciones
                if len(self.pos_history) > 5:
                    self.pos_history.pop(0)
                
                # Si hay historial anterior, calcular cambio de dirección
                if len(self.pos_history) >= 2:
                    angle_diff = abs(current_angle - self.last_angle)
                    # Normalizar a [0, π]
                    if angle_diff > math.pi:
                        angle_diff = 2 * math.pi - angle_diff
                    
                    # Si cambio > 90 grados (π/2 radianes)
                    if angle_diff > math.pi / 2:
                        self.metrics["cambios_direccion_bruscos"] += 1
                
                self.last_angle = current_angle
            
            # 3. Detectar fin de espasmo
            if self.espasmo_inicio is not None and accel_px_frame2 < 20:
                duracion = (current_time - self.espasmo_inicio) * 1000  # en ms
                self.metrics["duracion_espasmo_ms"] += duracion
                self.metrics["eventos_espasmo"].append(round(duracion, 2))
                self.espasmo_inicio = None
            
            # 4. Vibraciones (aceleración entre 15 y 50)
            if 15 <= accel_px_frame2 <= 50:
                self.metrics["vibraciones"] += 1
            
            self.last_vel = vel_px_frame
            self.prev_movement_time = current_time
        
        self.last_pos = current_pos

    def detect_micro_movements(self, current_pos):
        """Detecta movimientos involuntarios cuando NO hay bloque seleccionado"""
        if self.selected_block is None:
            current_time = time.time()
            
            if self.last_pos:
                dx = current_pos[0] - self.last_pos[0]
                dy = current_pos[1] - self.last_pos[1]
                dist = math.sqrt(dx**2 + dy**2)
                
                # Si hay movimiento pequeño pero perceptible (2-10 px) sin seleccionar
                if 2 <= dist <= 10:
                    time_since_last = current_time - self.prev_movement_time
                    # Si es un movimiento rápido y repetitivo (< 100ms entre movimientos)
                    if time_since_last < 0.1:
                        self.metrics["microMovimientos"] += 1
            
            self.last_pos = current_pos

    def save_results(self, phase_name):
        if not os.path.exists('results'):
            os.makedirs('results')
            
        final_data = {
            "id_paciente": self.patient_name,
            "fase": phase_name,
            "exitos": self.metrics["exitos"],
            "errores_pared": self.metrics["errores_pared"],
            "caidas_mouse": self.metrics["caidas_mouse"],
            "vibraciones": self.metrics["vibraciones"],
            "vel_max_mm_s": round(max(self.metrics["velocidades_mm_s"]), 2) if self.metrics["velocidades_mm_s"] else 0,
            "vel_avg_mm_s": round(sum(self.metrics["velocidades_mm_s"])/len(self.metrics["velocidades_mm_s"]), 2) if self.metrics["velocidades_mm_s"] else 0,
            "acc_max_mm_s2": round(max(self.metrics["aceleraciones_mm_s2"]), 2) if self.metrics["aceleraciones_mm_s2"] else 0,
            "acc_avg_mm_s2": round(sum(self.metrics["aceleraciones_mm_s2"])/len(self.metrics["aceleraciones_mm_s2"]), 2) if self.metrics["aceleraciones_mm_s2"] else 0,
            "vel_max_px_frame": round(max(self.metrics["velocidades_px_frame"]), 2) if self.metrics["velocidades_px_frame"] else 0,
            "vel_avg_px_frame": round(sum(self.metrics["velocidades_px_frame"])/len(self.metrics["velocidades_px_frame"]), 2) if self.metrics["velocidades_px_frame"] else 0,
            "acc_max_px_frame2": round(max(self.metrics["aceleraciones_px_frame2"]), 2) if self.metrics["aceleraciones_px_frame2"] else 0,
            "acc_avg_px_frame2": round(sum(self.metrics["aceleraciones_px_frame2"])/len(self.metrics["aceleraciones_px_frame2"]), 2) if self.metrics["aceleraciones_px_frame2"] else 0,
            "picos_aceleracion_alta": self.metrics["picos_aceleracion_alta"],
            "cambios_direccion_bruscos": self.metrics["cambios_direccion_bruscos"],
            "microMovimientos": self.metrics["microMovimientos"],
            "duracion_espasmo_ms": round(self.metrics["duracion_espasmo_ms"], 2),
            "eventos_espasmo": self.metrics["eventos_espasmo"],
             "_unidades_y_descripciones": {
                "exitos": "conteo - Numero de bloques movidos exitosamente al area destino",
                "errores_pared": "conteo - Numero de veces que choco con la pared central",
                "caidas_mouse": "conteo - Numero de veces que solto el bloque fuera del area destino",
                "vibraciones": "conteo - Cambios moderados de direccion (15-50 px/frame²)",
                "vel_max_mm_s": "mm/s - Velocidad maxima alcanzada por el mouse",
                "vel_avg_mm_s": "mm/s - Velocidad promedio del mouse durante la prueba",
                "acc_max_mm_s2": "mm/s² - Aceleracion maxima registrada",
                "acc_avg_mm_s2": "mm/s² - Aceleracion promedio durante la prueba",
                "vel_max_px_frame": "pixeles/frame - Velocidad maxima (valor original)",
                "vel_avg_px_frame": "pixeles/frame - Velocidad promedio (valor original)",
                "acc_max_px_frame2": "pixeles/frame² - Aceleracion maxima (valor original)",
                "acc_avg_px_frame2": "pixeles/frame² - Aceleracion promedio (valor original)",
                "picos_aceleracion_alta": "conteo - Aceleraciones > 50 px/frame² (ESPASMO)",
                "cambios_direccion_bruscos": "conteo - Cambios de dirección > 90° (ESPASMO)",
                "microMovimientos": "conteo - Movimientos involuntarios detectados en reposo",
                "duracion_espasmo_ms": "milisegundos - Duracion total acumulada de espasmos",
                "eventos_espasmo": "array - Lista de duraciones individuales de cada espasmo (ms)"
            },
            "timestamp": time.ctime()
        }
        
        # Generar nombre de archivo basado en el paciente, fase y número de prueba
        patient_id = self.patient_name.strip().replace(" ", "_")
        if not patient_id:
            patient_id = "Paciente"
        patient_id = "".join(ch for ch in patient_id if ch.isalnum() or ch in ("_", "-"))

        phase_id = str(phase_name).strip().replace(" ", "_")
        if not phase_id:
            phase_id = "Fase"
        phase_id = "".join(ch for ch in phase_id if ch.isalnum() or ch in ("_", "-"))

        filename = os.path.join("results", f"{patient_id}_{phase_id}_prueba{self.current_test_number}.json")

        with open(filename, 'w') as f:
            json.dump(final_data, f, indent=4)
        print(f"Resultados guardados en {filename}")


    def show_menu_inicial(self):
        """Pantalla de menú inicial"""
        input_text = ""
        selected_option = None
        input_active = True
        
        while True:
            self.screen.fill(WHITE)
            
            title = self.font_large.render("Box and Block Test", True, BLACK)
            self.screen.blit(title, (WIDTH//2 - title.get_width()//2, 50))
            
            input_label = self.font_medium.render("Nombre del paciente:", True, BLACK)
            self.screen.blit(input_label, (100, 150))
            
            input_box = pygame.Rect(100, 200, 400, 50)
            pygame.draw.rect(self.screen, GRAY if input_active else WHITE, input_box, 2)
            
            input_surface = self.font.render(input_text, True, BLACK)
            self.screen.blit(input_surface, (110, 215))
            
            # Checkbox para sonidos
            sound_label = self.font.render("Sonidos activados:", True, BLACK)
            self.screen.blit(sound_label, (100, 280))
            
            sound_checkbox = pygame.Rect(250, 275, 30, 30)
            pygame.draw.rect(self.screen, BLACK, sound_checkbox, 2)
            if self.sound_enabled:
                pygame.draw.rect(self.screen, GREEN, pygame.Rect(255, 280, 20, 20))
            
            options_label = self.font_medium.render("Selecciona una opción:", True, BLACK)
            self.screen.blit(options_label, (100, 330))
            
            btn_training = pygame.Rect(100, 390, 300, 60)
            color_training = GRAY if selected_option == 0 else BLUE
            pygame.draw.rect(self.screen, color_training, btn_training)
            training_text = self.font.render("ENTRENAMIENTO", True, WHITE)
            self.screen.blit(training_text, (btn_training.x + 50, btn_training.y + 20))
            
            btn_test = pygame.Rect(500, 390, 300, 60)
            color_test = GRAY if selected_option == 1 else BLUE
            pygame.draw.rect(self.screen, color_test, btn_test)
            test_text = self.font.render("PRUEBA FORMAL", True, WHITE)
            self.screen.blit(test_text, (btn_test.x + 50, btn_test.y + 20))
            
            instruction = self.font.render("Haz clic en una opción o presiona ENTER", True, BLACK)
            self.screen.blit(instruction, (WIDTH//2 - instruction.get_width()//2, 480))
            
            pygame.display.flip()
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    return False
                
                if event.type == pygame.KEYDOWN:
                    if input_active:
                        if event.key == pygame.K_BACKSPACE:
                            input_text = input_text[:-1]
                        elif event.key == pygame.K_RETURN:
                            input_active = False
                        elif len(input_text) < 30:
                            input_text += event.unicode
                    else:
                        if event.key == pygame.K_LEFT:
                            selected_option = 0
                        elif event.key == pygame.K_RIGHT:
                            selected_option = 1
                        elif event.key == pygame.K_RETURN and selected_option is not None:
                            self.patient_name = input_text if input_text else "Paciente"
                            self.trial_mode = "training" if selected_option == 0 else "test"
                            return True
                
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if input_box.collidepoint(event.pos):
                        input_active = True
                    elif sound_checkbox.collidepoint(event.pos):
                        self.sound_enabled = not self.sound_enabled
                    elif btn_training.collidepoint(event.pos):
                        selected_option = 0
                        self.patient_name = input_text if input_text else "Paciente"
                        self.trial_mode = "training"
                        return True
                    elif btn_test.collidepoint(event.pos):
                        selected_option = 1
                        self.patient_name = input_text if input_text else "Paciente"
                        self.trial_mode = "test"
                        return True

    def show_transition_notification(self, message, duration=3):
        """Muestra una notificación en pantalla"""
        start_time = time.time()
        
        while time.time() - start_time < duration:
            self.screen.fill(WHITE)
            
            s = pygame.Surface((WIDTH, HEIGHT))
            s.set_alpha(200)
            s.fill(BLACK)
            self.screen.blit(s, (0, 0))
            
            msg_surface = self.font_large.render(message, True, WHITE)
            self.screen.blit(msg_surface, (WIDTH//2 - msg_surface.get_width()//2, HEIGHT//2 - 50))
            
            instruction = self.font.render("Presiona ENTER para continuar", True, WHITE)
            self.screen.blit(instruction, (WIDTH//2 - instruction.get_width()//2, HEIGHT//2 + 80))
            
            pygame.display.flip()
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return False
                if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                    return True
            
            self.clock.tick(FPS)
        
        return True

    def show_final_notification(self):
        """Pantalla final de prueba completada"""
        waiting = True
        
        while waiting:
            self.screen.fill(WHITE)
            
            s = pygame.Surface((WIDTH, HEIGHT))
            s.set_alpha(200)
            s.fill(GREEN)
            self.screen.blit(s, (0, 0))
            
            msg_surface = self.font_large.render("¡PRUEBA FINALIZADA!", True, WHITE)
            self.screen.blit(msg_surface, (WIDTH//2 - msg_surface.get_width()//2, HEIGHT//2 - 80))
            
            stats_text = self.font_small.render(f"Paciente: {self.patient_name}", True, WHITE)
            self.screen.blit(stats_text, (WIDTH//2 - stats_text.get_width()//2, HEIGHT//2 + 20))
            
            instruction = self.font.render("Presiona cualquier tecla para salir", True, WHITE)
            self.screen.blit(instruction, (WIDTH//2 - instruction.get_width()//2, HEIGHT//2 + 100))
            
            pygame.display.flip()
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return False
                if event.type == pygame.KEYDOWN or event.type == pygame.MOUSEBUTTONDOWN:
                    return True
            
            self.clock.tick(FPS)

    def run_trial(self, duration_sec, phase_name):
        self.reset_session()
        running = True
        end_time = time.time() + duration_sec
        skip_pressed = False
        
        while running:
            self.screen.fill(WHITE)
            current_time = time.time()
            remaining = max(0, int(end_time - current_time))
            
            if remaining <= 0 or len(self.blocks) == 0:
                running = False

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit(); return
                
                if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                    if not skip_pressed:
                        skip_pressed = True
                        running = False
                
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for b in self.blocks:
                        if b['rect'].collidepoint(event.pos):
                            self.selected_block = b
                            if self.sound_enabled:
                                self.select_sound.play()  # 🔊 Sonido de selección
                            break
                            
                if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    if self.selected_block:
                        if self.box_right.colliderect(self.selected_block['rect']):
                            self.metrics["exitos"] += 1
                            if self.sound_enabled:
                                self.success_sound.play()  # 🔊 Sonido de éxito
                            self.blocks.remove(self.selected_block)
                        else:
                            self.metrics["caidas_mouse"] += 1
                            if self.sound_enabled:
                                self.collision_sound.play()  # 🔊 Sonido de golpe (fuera de área)
                            self.selected_block['rect'].topleft = self.selected_block['original_pos']
                        self.selected_block = None

            if self.selected_block:
                mouse_pos = pygame.mouse.get_pos()
                self.selected_block['rect'].center = mouse_pos
                self.calculate_kinematics(mouse_pos)
                
                if self.selected_block['rect'].colliderect(self.partition):
                    self.metrics["errores_pared"] += 1
                    if self.sound_enabled:
                        self.error_sound.play()  # 🔊 Sonido de error/caída contra la línea central
                    self.selected_block['rect'].topleft = self.selected_block['original_pos']
                    self.selected_block = None
            else:
                # Detectar movimientos involuntarios cuando NO hay bloque seleccionado
                mouse_pos = pygame.mouse.get_pos()
                self.detect_micro_movements(mouse_pos)

            pygame.draw.rect(self.screen, GRAY, self.box_left, 2)
            pygame.draw.rect(self.screen, GRAY, self.box_right, 2)
            pygame.draw.rect(self.screen, BLACK, self.partition)
            
            for b in self.blocks:
                pygame.draw.rect(self.screen, b['color'], b['rect'])
            
            timer_text = self.font.render(f"Tiempo: {remaining}s | Bloques restantes: {len(self.blocks)} | Movidos: {self.metrics['exitos']}", True, BLACK)
            self.screen.blit(timer_text, (10, 10))
            
            phase_text = self.font.render(f"Fase: {phase_name}", True, BLACK)
            self.screen.blit(phase_text, (10, 35))
            
            if remaining > 10:
                skip_text = self.font.render("(ENTER para pasar a siguiente fase)", True, BLUE)
                self.screen.blit(skip_text, (10, 60))
            
            pygame.display.flip()
            self.clock.tick(FPS)
            
        # self.save_results(phase_name)  # Datos de pruebas desactivados


if __name__ == "__main__":
    game = BBTGame()
    
    # Mostrar menú inicial
    if not game.show_menu_inicial():
        pygame.quit()
        exit()
    
    if game.trial_mode == "training":
        # Modo Entrenamiento - Calcular número de prueba
        game.calculate_next_test_number()
        game.run_trial(900, "Entrenamiento")
        
        # Después del entrenamiento, realizar la prueba formal
        if not game.show_transition_notification("Iniciando Prueba Formal", duration=2):
            pygame.quit()
            exit()
    
    # Modo Prueba Formal (dos fases) - Se ejecuta después del entrenamiento o directamente si se selecciona prueba
    # Calcular el número de prueba una sola vez para que ambas fases compartan el mismo número
    game.calculate_next_test_number()
    
    # Fase 1: Lado Izquierdo
    game.run_trial(60, "Lado Izquierdo")
    
    # Notificación de transición
    if not game.show_transition_notification("Cambiando a Lado Derecho", duration=2):
        pygame.quit()
        exit()
    
    # Reiniciar métricas para segunda fase
    game.metrics = {
        "velocidades_px_frame": [],
        "velocidades_mm_s": [],
        "aceleraciones_px_frame2": [],
        "aceleraciones_mm_s2": [],
        "exitos": 0,
        "errores_pared": 0,
        "caidas_mouse": 0,
        "vibraciones": 0,
        "picos_aceleracion_alta": 0,
        "cambios_direccion_bruscos": 0,
        "microMovimientos": 0,
        "duracion_espasmo_ms": 0,
        "eventos_espasmo": []
    }
    
    # Invertir cajas para la segunda vuelta
    game.box_left, game.box_right = game.box_right, game.box_left
    #Fase 2: Lado Derecho
    game.run_trial(60, "Lado Derecho")
    
    # Mostrar pantalla final
    game.show_final_notification()
    
    pygame.quit()
