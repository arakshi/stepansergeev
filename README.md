# Demo Simulation Control Panel (FastAPI + SQLModel)

Учебный DEMO-макет панели управления с **полностью симуляционными** метриками и событиями.

> В проекте нет реальных VPN/туннелей/обходов/сетевых инъекций. Все потоки и действия — синтетические.

## Быстрый старт (CLI)

### Windows (PowerShell)
```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run.py
```

### macOS/Linux
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run.py
```

Откройте: `http://127.0.0.1:8000/dashboard`

---

## Запуск в PyCharm (чтобы не было ваших ошибок)

Проблема из вашего лога: при запуске `app/main.py` IDE подхватывает **чужой пакет `app`** из `site-packages`, а не локальную папку проекта.

Сделайте так:

1. **Откройте проект целиком** (корень репозитория), а не только папку `app`.
2. **Выберите интерпретатор проекта**:
   - `File → Settings → Project: ... → Python Interpreter`
   - создайте/выберите `.venv` внутри проекта.
3. Установите зависимости:
   - в терминале PyCharm: `pip install -r requirements.txt`
4. Создайте Run Configuration:
   - `Run → Edit Configurations...`
   - `+` → **Python**
   - `Script path`: `<проект>/run.py`
   - `Working directory`: `<проект>`
   - `Python interpreter`: ваш `.venv`
5. Нажмите Run.

Альтернатива:
- можно запускать как модуль: `python -m app`.

> В проект добавлен безопасный launcher `run.py` и `app/__main__.py`, чтобы запуск в PyCharm/Windows был стабильным.

---

## Если в preview "Not Found"
В репозитории есть legacy static-preview конфиг (`static.json`).
Чтобы preview не был пустым, добавлена fallback-страница `public/index.html` с инструкцией запуска FastAPI.
Для полноценной работы нужен запуск backend-команды выше.

Также добавлен `Procfile`:
```Procfile
web: uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

## Стек
- FastAPI
- SQLModel + SQLite
- Jinja2 templates
- HTMX + Alpine.js (CDN)
- TailwindCSS (CDN)
- Chart.js (CDN)

## Что есть по страницам
- `/dashboard` — KPI и мини-графики трендов.
- `/agents` — таблица агентов, поиск/фильтры/сортировка, apply/stop (с модалками), последние telemetry по агенту.
- `/profiles` — поиск и сортировка профилей.
- `/audit` — фильтры по пользователю/действию/диапазону дат.
- `/analytics` — KPI, графики, объединённая лента последних событий, экспорт telemetry CSV.
- `/tests` — список прогонов, длительность, список проверок, график процента успешных прогонов.

## API метрик
- `GET /api/metrics/kpi?range=1h|24h|7d`
- `GET /api/metrics/traffic?range=1h|24h`
- `GET /api/metrics/latency?range=1h|24h`
- `GET /api/metrics/actions?range=24h`
- `GET /api/metrics/profile_distribution?range=7d`
- `GET /api/metrics/top_errors?range=24h`
- `GET /api/telemetry/export.csv?range=24h`
- `GET /healthz`

## Данные
При первом запуске сидируются:
- 3 пользователя: admin/operator/viewer
- 7 агентов
- 5 профилей
- telemetry за последний час
- тестовые прогоны за ~15 дней

Также запускается фоновый генератор telemetry для online-агентов (каждые ~7 секунд).
