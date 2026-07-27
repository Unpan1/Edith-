# ClipAI

Plataforma local de IA para generar clips automáticos de video con subtítulos.

Sube un MP4 → Whisper transcribe → HighlightDetector elige los mejores momentos → FFmpeg corta clips (20–60 s) con subtítulos incrustados.

## Requisitos

- Python 3.11+
- Node.js 18+
- MySQL 8+
- [FFmpeg](https://ffmpeg.org/download.html) en el PATH
- (Opcional) GPU CUDA para acelerar Whisper

## Configuración rápida

### 1. Base de datos

```sql
CREATE DATABASE clipai CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 2. Backend

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
copy .env.example .env   # ajusta MYSQL_* y FFMPEG_PATH
```

Edita `.env` con tus credenciales MySQL. Las tablas se crean al arrancar (también puedes usar Alembic):

```bash
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API docs: http://127.0.0.1:8000/docs

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Abre http://localhost:5173

## Flujo

1. Arrastra un video a la zona de upload
2. Pulsa **Procesar**
3. Observa el progreso: audio → Whisper → análisis → clips → subtítulos
4. Reproduce o descarga los clips con subtítulos quemados

## API

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/upload` | Subir video |
| GET | `/videos` | Listar videos |
| GET | `/videos/{id}` | Detalle |
| POST | `/videos/{id}/process` | Iniciar pipeline |
| GET | `/videos/{id}/clips` | Clips del video |
| GET | `/clip/{id}` | Detalle clip |
| GET | `/clip/{id}/stream` | Reproducir |
| GET | `/clip/{id}/download` | Descargar |
| GET | `/clip/{id}/thumbnail` | Miniatura |
| DELETE | `/video/{id}` | Eliminar |

## Arquitectura

```
backend/app/
  config/      → Settings (.env)
  database/    → SQLAlchemy session
  models/      → ORM (users, videos, transcripciones, clips)
  schemas/     → Pydantic
  services/    → VideoService, ClipService + DI
  ai/          → WhisperService, HighlightDetector
  video/       → FFmpegService
  subtitle/    → SubtitleService (SRT/VTT)
  storage/     → StorageService (UUID)
  routes/      → FastAPI (sin lógica de negocio)
  utils/       → logs, excepciones, validadores
```

Servicios independientes inyectados vía `Depends`:

- `VideoService` · `WhisperService` · `SubtitleService` · `ClipService`
- `HighlightDetector` · `StorageService` · `FFmpegService`

## Variables de entorno

| Variable | Descripción |
|----------|-------------|
| `MYSQL_HOST` / `PORT` / `DATABASE` / `USER` / `PASSWORD` | Conexión MySQL |
| `UPLOAD_FOLDER` / `OUTPUT_FOLDER` | Rutas de archivos |
| `WHISPER_MODEL` | `tiny` \| `base` \| `small` \| `medium` \| `large` |
| `FFMPEG_PATH` | Binario FFmpeg |
| `MAX_UPLOAD_SIZE_MB` | Límite de subida |

## ClipAI Studio (capa SaaS)

Sobre el motor de clips existe una segunda capa modular:

| Ruta UI | API | Módulo |
|---------|-----|--------|
| `/` | `/api/dashboard` | Dashboard |
| `/studio` | `/upload`, `/videos/...` | Studio (clips + subtítulos) |
| `/library` | `/api/library` | Biblioteca |
| `/library/clips/:id` | `/api/content`, `/api/thumbnails`, `/api/editor` | Workspace clip |
| `/trends` | `/api/trends` | Tendencias |
| `/calendar` | `/api/calendar` | Calendario |
| `/publishing` | `/api/publishing` | Publicación |
| `/analytics` | `/api/analytics` | Analytics |
| `/learning` | `/api/learning` | Aprendizaje |
| `/automation` | `/api/automation` | Modo automático |
| `/growth` | `/api/growth` | Agente de crecimiento |
| `/credits` | `/api/credits` | Créditos / planes |
| `/admin` | `/api/admin` | Administración |

Backend modular en `backend/app/modules/`. El pipeline de Whisper/highlights/clips **no se modifica**; tras generar clips se ejecuta un hook de enrichment (títulos, hashtags, miniaturas, créditos).

OAuth real de redes y analytics de plataformas están stubs listos para integrar APIs oficiales.
