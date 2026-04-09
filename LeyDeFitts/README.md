**🎯 Test de Control Motor basado en la Ley de Fitts 🧠**

Este software es una herramienta de Ingeniería de la Rehabilitación desarrollada en Python para evaluar el control motor del miembro superior en pacientes con hemiparesia post-ACV, mediante tareas de selección de objetivos en pantalla.

El sistema se basa en la Ley de Fitts, permitiendo analizar la relación entre velocidad y precisión del movimiento a través de métricas cuantitativas.

*🚀 Funcionalidades*

🎮 Evaluación de Control Motor
Se cuenta con tres niveles de dificultad progresiva con targets con movimiento lineal alternado (izquierda ↔ derecha), y un cuarto nivel con distribución aleatoria.
Los targets tienen variación de Distancia (D) y Tamaño del target (W)

🔊 Feedback Multimodal
Retroalimentación visual:
- Verde (acierto)
- Rojo (error)
Feedback auditivo:
- Sonido de éxito (dependiente de desempeño)
- Sonido de error
Sistema de estrellas:
- ⭐ (bien)
- ⭐⭐ (muy bien)
- ⭐⭐⭐ (excelente)

📊Generación automática de reportes en formato JSON con:
- Puntaje total
- Cantidad de intentos
- Precisión (% de aciertos)
- Tiempo de movimiento medio (MT)
- Error medio
- Pendiente de Fitts (b)
- Throughput (TP) → eficiencia motora

📈 Experiencia del Usuario
- Pantalla de instrucciones inicial
- Barra de progreso por nivel
- Transición entre niveles
- Feedback motivacional para el paciente
- Posibilidad de salida en cualquier momento (ESC)

*🛠️ Instalación y Requisitos*
Requisitos:
- Python 3.x
- pip
Librerías necesarias:
*pip install pygame numpy*

*🎮 Cómo usarlo*
Ejecutar el archivo principal:
python fitts.py

Flujo del test:
1. Ingresar ID del paciente
2. Leer las instrucciones iniciales
3. El paciente deberá:
    Hacer click sobre los círculos
    Intentar ser lo más rápido y preciso posible
4. Completar los 3 niveles de dificultad
6. Finalización
Se muestra un resumen simple para el paciente
Se genera automáticamente un archivo JSON en la carpeta /results

Escuela de Ciencia y Tecnología, UNSAM -1er cuatrimestre 2026- Grupo 1: Casademunt, Hidalgo, Pozzo Galdon, Rodriguez Piro
