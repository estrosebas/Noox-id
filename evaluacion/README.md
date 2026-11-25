# Evaluación técnica de NooxID

Scripts reproducibles que usan **el mismo servicio facial del backend** (YuNet + SFace, con sus controles de calidad), así
que los números corresponden al sistema tal como está implementado. Los datos de personas no se versionan.

| Script | Para qué |
|---|---|
| `evaluar_lfw.py` | FAR, FRR, EER, exactitud (10 pliegues), identificación 1:N con umbral y margen, y latencia por imagen, con el conjunto público **LFW**. No necesita voluntarios. |
| `medir_latencia_api.py` | Latencia de punta a punta del endpoint `/api/face/verify-user` (en proceso, sin red) con 100 llamadas genuinas y 100 impostoras. |
| `evaluar_reconocimiento.py` | Lo mismo con **fotos de voluntarios** (FAR/FRR/EER, aceptación por condición). Las fotos van en `evaluacion/datos/fotos/` (ignorada por git) y exige consentimiento informado por escrito. |

`resultados_lfw/` guarda la última corrida: `metricas.json`, `pares.csv` (la similitud de cada par) y las figuras.

## Reproducir la evaluación con LFW

```powershell
# 1. Datos (fuera del repositorio). Réplica de LFW que usa scikit-learn; SHA-256 del archivo:
#    055f7d9c632d7370e6fb4afc7468d40f970c34a80d4c6f50ffec63f5a8d536c0
mkdir $env:TEMP\lfw; cd $env:TEMP\lfw
curl.exe -L -o lfw.tgz   https://ndownloader.figshare.com/files/5976018
curl.exe -L -o pairs.txt https://ndownloader.figshare.com/files/5976006
tar -xzf lfw.tgz

# 2. Evaluación (unos 8 a 10 minutos en CPU; guarda un caché de vectores para repetir sin recalcular)
pip install -r noox-id-back/requirements.txt matplotlib
python evaluacion/evaluar_lfw.py --datos $env:TEMP\lfw

# 3. Latencia del endpoint
python evaluacion/medir_latencia_api.py --datos $env:TEMP\lfw --n 100
```

## Cómo leer los resultados

- **FAR / FRR** se calculan sobre los pares cuyas dos fotos aceptó el servicio. Las fotos que el control de calidad rechaza
  (en LFW, alrededor del 20 %, casi todas por no tener exactamente un rostro) se reportan aparte y sus pares se excluyen.
- **Identificación 1:N:** galería con una foto por persona (las que tienen dos o más), sondas con sus otras fotos y, como
  desconocidos, las personas con una sola foto. Regla: mejor coincidencia ≥ τ y ventaja ≥ margen sobre la segunda mejor.
- Con muestras de miles de pares no se puede demostrar una tasa de 1 en 10 000; se reportan intervalos de Wilson al 95 %.
- LFW son fotos de personas públicas sin guía de captura: sirve para validar el modelo y los umbrales, no sustituye una
  evaluación con la población real.

## Pruebas del backend

`noox-id-back/tests/` tiene pruebas automáticas de los flujos y controles de seguridad (registro, código por correo, TOTP,
Google, roles y permisos, límites, claves, aviso de acceso). `python noox-id-back/tests/ejecutar_todas.py`.
