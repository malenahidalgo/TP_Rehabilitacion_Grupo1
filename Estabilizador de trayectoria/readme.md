# Test estabilización de trayectoria 🧠

Este software es una herramienta de **Ingeniería de la Rehabilitación** desarrollada en Python para evaluar el control motor fino y la estabilización de trayectoria en pacientes con hemiparesia post-ACV, mediante el seguimiento de un camino sinusoidal con el mouse.

## 🚀 Funcionalidades
* **Evaluación de Control Motor:** Tres niveles de dificultad creciente con trayectorias sinusoidales de distinta amplitud y frecuencia.
* **Feedback Multimodal:** Retroalimentación visual en tiempo real (cursor azul/rojo) y sonora al salir del camino.
* **Análisis Clínico:** Generación automática de reportes JSON con:
    * Errores por nivel y errores por minuto normalizados.
    * Tiempo de reacción a la iniciación motora.
    * Tendencia de fatiga entre niveles.
    * Índice de Precisión de Trayectoria (IPT)

## 🛠️ Instalación y Requisitos

1. **Python 3.x** instalado.
2. **pip** (administrador de paquetes de Python).
3. Clonar o descargar este repositorio.
4. Instalar las dependencias necesarias:
    ```bash 
   pip install -r requirements.txt

## 🎮 Cómo usarlo
1. Ejecuta el archivo principal:
    ```bash
    python EstabilizadorTrayectoria.py

2. Ingresá el nombre del paciente en el menú inicial y hacé clic en COMENZAR.

3. El paciente deberá:
    * Mover el mouse hasta el punto VERDE para iniciar el nivel.
    * Seguir el camino sin salirse del borde.
    * Llegar hasta el punto ROJO para completar el nivel.

4. Luego de 3 niveles, se generará un reporte detallado en la carpeta /resultados.

💡 Si el paciente no puede completar el test, los niveles ya realizados se guardan automáticamente al presionar ESC o cerrar la ventana.

## 📁 Estructura de Archivos
* EstabilizadorTrayectoria.py: Código fuente principal.
* docs/: Carpeta que debe contener sonidos del test.
* results/: Carpeta donde se almacenan los resultados del paciente (formato .json).


Escuela de Ciencia y Tecnología, UNSAM -1er cuatrimestre 2026- Grupo 1: Casademunt, Hidalgo, Pozzo Galdon, Rodriguez Piro