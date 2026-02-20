# PerLap - Guía de Uso

## Requisitos

- Python 3.10+
- Cámara USB (Ourlife action cam u otra webcam)
- Pista de autos RC 1/43

Instalar dependencias:
```
cd PC
pip install -r requirements.txt
```

Ejecutar:
```
python main.py
```

---

## 1. Conectar la Cámara

Al abrir la app, intenta conectarse al **Dispositivo 0** (primera cámara USB).

- Si no ves imagen, selecciona otro dispositivo en el combo **"Cámara"** de la barra superior.
- La cámara Ourlife debe conectarse por USB **en modo webcam** (no en modo almacenamiento).
- Si la Ourlife no aparece como webcam, prueba encenderla con el cable USB ya conectado.

La imagen aparece en el panel izquierdo. Si ves "Sin señal de cámara", revisa la conexión.

---

## 2. Definir la Línea de Meta

La línea de meta es una línea virtual sobre el video. Los autos se detectan cuando cruzan esta línea.

### Pasos:

1. Haz clic en **"Definir Meta"** en la barra superior.
2. El cursor cambia a una cruz (+).
3. **Primer clic**: marca el inicio de la línea. La barra de estado muestra las coordenadas.
4. **Segundo clic**: marca el fin de la línea.

### Consejos para la línea de meta:

- Dibújala **perpendicular a la dirección de los autos** (de lado a lado de la pista).
- Colócala en una zona con **buena iluminación** y fondo uniforme.
- La línea roja aparece sobre el video junto con un rectángulo que muestra la **zona de detección** (ROI).
- Solo se analizan los colores dentro de ese rectángulo, lo cual reduce el ruido.
- Si la línea no funciona bien, puedes redefinirla haciendo clic en "Definir Meta" de nuevo.
- La posición se guarda automáticamente en `config.json`.

---

## 3. Registrar Autos (Detección por Color)

Cada auto necesita un **sticker o marca de color visible en la parte superior**. La cámara identifica los autos por este color.

### Preparación de los autos:

- Pega un sticker de color sólido y brillante en el **techo** de cada auto.
- Usa **colores distintos entre sí**: rojo, azul, verde, amarillo, naranja, blanco, etc.
- El sticker debe ser visible desde la cámara (mínimo ~1cm x 1cm en escala 1/43).
- Evita colores que se parezcan al fondo de la pista o a la pista misma.

### Pasos para registrar:

1. **Coloca el auto en la zona de la meta** (sobre la línea roja visible en el video).
2. Haz clic en **"Registrar Auto"** en la barra superior.
3. Se abre el diálogo de registro:
   - **Slot**: elige un slot (0-5). Cada auto ocupa un slot único.
   - **Nombre**: escribe el nombre del auto (ej: ROJO, P1, FERRARI). Máximo 12 caracteres.
4. Haz clic en **"Muestrear Color del Video"**.
5. El botón cambia a "Haz clic en el auto en el video..."
6. **Haz clic directamente sobre el sticker de color del auto** en la imagen de video.
7. La app toma una muestra del color en esa zona (parche de 20x20 píxeles).
8. El cuadro de preview muestra el color detectado.
9. Haz clic en **"Registrar"** para confirmar.

### Cómo funciona la detección de color:

- La app convierte el color a espacio **HSV** (Hue/Saturation/Value).
- HSV separa el tono del brillo, lo que hace la detección más robusta ante cambios de luz.
- Se genera un **rango automático** alrededor del color muestreado (±12 en Hue, ±60 en S/V).
- En cada frame, se buscan píxeles dentro de ese rango en la zona de la meta.
- Si encuentra un grupo de píxeles suficiente (contorno > 80px de área), calcula su centro.
- Se trackea el movimiento del centro frame a frame para detectar el cruce.

### Tips para buena detección:

- Muestrea el color **bajo las mismas condiciones de luz** que tendrás durante la carrera.
- Si un auto no se detecta bien, regístralo de nuevo con un nuevo muestreo.
- Los colores se guardan en `config.json`, así que no necesitas registrar cada vez.
- Si dos autos tienen colores similares, la app puede confundirlos. Usa colores bien distintos.

---

## 4. Iniciar una Carrera

1. Asegúrate de tener al menos un auto registrado y la línea de meta definida.
2. Haz clic en **"Iniciar Carrera"** (botón verde).
3. El botón cambia a **"Finalizar Carrera"** (rojo).
4. Los contadores se reinician a cero.

### Durante la carrera:

- Cada vez que un auto cruza la línea de meta, se detecta automáticamente.
- **Primer cruce** → evento START (el auto está en pista, vuelta 0).
- **Cruces siguientes** → evento LAP (se registra el tiempo de vuelta).
- Hay un **debounce de 2 segundos** entre detecciones del mismo auto (evita falsos).
- La pestaña **"Clasificación"** muestra posiciones, vueltas y tiempos en tiempo real.
- La pestaña **"Tiempos"** muestra cada vuelta individual con gaps.

### Finalizar carrera:

1. Haz clic en **"Finalizar Carrera"**.
2. Se guarda un archivo JSON en `races/` con todos los datos:
   - Tiempos de cada vuelta por competidor
   - Mejor vuelta, promedio
   - Gaps al líder
   - Todos los eventos cronológicos

---

## 5. Reiniciar

- **"Reiniciar"** pone todos los contadores a cero sin terminar la carrera.
- Los autos registrados y la línea de meta se mantienen.

---

## 6. Archivos de Configuración

### `config.json`
Se guarda automáticamente. Contiene:
- Posición de la línea de meta
- Autos registrados (nombre + rangos de color HSV)
- Índice de cámara seleccionado

Se carga automáticamente al abrir la app.

### `races/YYYY-MM-DD_HH-MM-SS.json`
Un archivo por carrera con datos completos. Ejemplo:
```json
{
  "id": "2026-02-12_15-30-00",
  "date": "2026-02-12T15:30:00",
  "duration_ms": 180000,
  "cars": [
    {
      "name": "ROJO",
      "total_laps": 5,
      "best_lap_ms": 4050,
      "avg_lap_ms": 4200,
      "laps": [
        {"lap": 1, "time_ms": 4321, "gap_to_leader_ms": 0},
        {"lap": 2, "time_ms": 4150, "gap_to_leader_ms": 200}
      ]
    }
  ]
}
```

---

## Solución de Problemas

| Problema | Solución |
|----------|----------|
| No hay imagen | Prueba otro dispositivo de cámara en el combo |
| Auto no se detecta | Re-muestrear el color con el auto en la zona de meta |
| Detecciones falsas | Definir la meta en zona con fondo uniforme, evitar colores del fondo |
| Detecta doble | El debounce de 2s debería evitarlo; si persiste, verificar la línea de meta |
| Colores confundidos | Usar stickers más distintos entre sí (ej: rojo vs azul, no rojo vs naranja) |
| FPS bajo | Verificar que no haya otras apps usando la cámara |
