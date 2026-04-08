# Test de Reacción Multimodal 🧠

Este software es una herramienta de **Ingeniería de la Rehabilitación** desarrollada en Python para evaluar la coordinación bajo demanda y la integración multisensorial mediante estímulos visuales y auditivos en pacientes con hemiparesia.

## 🚀 Funcionalidades
* **Estimulación Multimodal:** Generación aleatoria de tonos acústicos y formas geométricas.
* **Métricas de Trayectoria:** Cálculo de la rectitud del movimiento y velocidad de ejecución según la Ley de Fitts.
* **Análisis Clínico:** Generación automática de reportes JSON con:
    * Coeficiente de variación (estabilidad atencional).
    * Pendiente de fatiga.
    * Diferencial de interferencia visual-auditiva.
    * Análisis de lateralidad por cuadrantes.

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
    python main.py

2. Ingresa el nombre del paciente en el menú inicial.

3. El paciente deberá:
    * Hacer click en el botón VERDE si ve una figura.
    * Hacer click en el botón AZUL si escucha un sonido.

4. Luego de 10 estímulos, se generará un reporte detallado en la carpeta /results.

## 📁 Estructura de Archivos
* ReaccionMultimodal.py: Código fuente principal.
* docs/: Carpeta que debe contener sonido.webp y formas.png.
* results/: Carpeta donde se almacenan los resultados del paciente (formato .json).


Escuela de Ciencia y Tecnología, UNSAM -1er cuatrimestre 2026- Grupo 1: Casademunt, Hidalgo, Pozzo Galdon, Rodriguez Piro
