# File Vault

Микросервис одноразовых зашифрованных ссылок (аналог Mozilla Send). Пользователь передаёт текст или файл, сервис шифрует содержимое на бэкенде, сохраняет его в Redis и выдаёт уникальную ссылку по UUID. Ссылка открывается только один раз — после этого запись атомарно удаляется — либо перестаёт действовать по истечении TTL.

## Возможности
- Шифрование содержимого на бэкенде (Fernet), один и тот же ключ и одна и та же схема — для текста и для файлов.
- Одноразовое чтение: `GETDEL` в Redis атомарно отдаёт значение и тут же удаляет ключ — гонка между двумя одновременными чтениями невозможна.
- Автоматическое уничтожение по TTL (задаётся при создании ссылки, в границах `DEFAULT_TTL_SECONDS`/`MAX_TTL_SECONDS`).
- Поддержка текстовых секретов и файлов через единый JSON-конверт (`{"kind": ..., ...}`), зашифрованный целиком.
- Сквозное логирование: консоль (для Docker) + ротируемые файлы, отдельный поток для ERROR/CRITICAL.
- Интерактивная документация API (Swagger UI, ReDoc, OpenAPI JSON).
- Простой статический фронтенд (Bootstrap + Inter, без серверного шаблонизатора) для демонстрации на защите.
- Запуск одной командой через Docker Compose, приложение работает от непривилегированного пользователя.

## Стек
- **Python 3.12**, **FastAPI**, **Uvicorn**
- **Redis** — хранилище секретов с нативным TTL и атомарным одноразовым чтением
- **cryptography (Fernet)** — шифрование на бэкенде
- **pydantic-settings** — конфигурация через переменные окружения
- **Bootstrap 5.3 + Bootstrap Icons + Inter** — фронтенд (CDN, с SRI-хешами)
- **ruff** — статический анализ кода
- **pytest + pytest-asyncio + httpx + fakeredis** — тесты без поднятия реального Redis

## Архитектура

```
Браузер (static/index.html, static/view.html)
        │  fetch() — JSON / multipart
        ▼
app/main.py              — сборка FastAPI, middleware, обработчики ошибок, статика
        │
        ▼
app/api/v1/routes.py     — HTTP-роуты (создание/чтение секрета)
        │
        ▼
app/services/            — бизнес-логика: валидация TTL/размера, сборка JSON-конверта
secret_service.py
        │
        ├──▶ app/core/crypto.py            — шифрование/расшифровка (Fernet)
        │
        └──▶ app/repositories/              — доступ к данным
             secret_repository.py             SET...EX при записи, GETDEL при чтении
                   │
                   ▼
                 Redis
```

Слои не знают друг о друге лишнего: репозиторий и сервис шифрования одинаково обрабатывают текст и файл — вся разница в типе секрета инкапсулирована в сервисном слое (JSON-конверт `{"kind": "text"|"file", ...}`), а не размазана по коду.

## Переменные окружения

Полный пример — в [`.env.example`](.env.example). Перед запуском скопируйте его в `.env`:

```bash
cp .env.example .env
```

| Переменная | По умолчанию | Описание |
|---|---|---|
| `APP_PORT` | `8000` | Порт **на хосте**, на котором Docker Compose публикует приложение. Внутри контейнера сервис всегда слушает `8000`. |
| `LOG_LEVEL` | `INFO` | Уровень логирования: `DEBUG` \| `INFO` \| `WARNING` \| `ERROR` \| `CRITICAL`. |
| `REDIS_HOST` | `redis` (в Docker) / `localhost` (дефолт в коде) | Хост Redis. |
| `REDIS_PORT` | `6379` | Порт Redis. |
| `REDIS_PASSWORD` | *(пусто)* | Пароль Redis, если включена аутентификация. |
| `ENCRYPTION_KEY` | — (**обязательна**) | Fernet-ключ: 32 url-safe base64 байта. Сгенерировать: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`. Невалидный ключ роняет приложение сразу при старте, а не на первом запросе. |
| `DEFAULT_TTL_SECONDS` | `3600` | TTL секрета, если клиент не указал свой. |
| `MAX_TTL_SECONDS` | `604800` (7 дней) | Максимально допустимый TTL. |
| `MAX_FILE_SIZE_MB` | `20` | Лимит размера файла; также используется как общий лимит тела любого запроса (см. middleware в `app/main.py`). |

## Быстрый старт (Docker)

```bash
cp .env.example .env
# впишите ENCRYPTION_KEY, сгенерировав его командой из таблицы выше
docker compose up --build
```

После запуска:
- Фронтенд: http://localhost:8000
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Локальный запуск без Docker

Пригодится, если Redis уже поднят отдельно (например, `brew services start redis`):

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt

cp .env.example .env
# в .env: REDIS_HOST=localhost, ENCRYPTION_KEY=<сгенерированный ключ>

uvicorn app.main:app --reload
```

## API

| Метод | Путь | Описание |
|---|---|---|
| `POST` | `/api/v1/secrets` | Создать текстовый секрет. Тело: `{"content": "...", "ttl_seconds": 3600}`. Ответ `201`: `{"id": "...", "ttl_seconds": 3600}`. |
| `POST` | `/api/v1/secrets/file` | Создать файловый секрет. `multipart/form-data`: поле `file` + опционально `ttl_seconds`. Ответ тот же, что и выше. |
| `GET` | `/api/v1/secrets/{id}` | Одноразовое чтение. Для текста — JSON `{"kind": "text", "content": "..."}`. Для файла — бинарное содержимое с заголовком `Content-Disposition`. `404`, если секрет не существовал, уже был прочитан или истёк TTL. |

Полная интерактивная документация — в Swagger UI (`/docs`).

## Фронтенд

Статика в `static/` отдаётся тем же FastAPI-приложением (`StaticFiles`, без шаблонизатора):
- `index.html` — создание секрета: текстовое поле с композитным тулбаром (прикрепить файл / выбрать TTL), результат — одноразовая ссылка с копированием.
- `view.html` — открытие секрета: гейт "Показать" (защита от link-preview ботов, которые иначе спалили бы одноразовую ссылку до того, как её увидит человек), затем текст / скачивание файла / сообщение об ошибке.

Оформление — Bootstrap 5.3 + Bootstrap Icons + шрифт Inter, тёмная Zinc-палитра с кастомным индиго-акцентом (переопределены CSS-переменные темы и `--bs-btn-*` у `.btn-primary`, т.к. Bootstrap зашивает цвет кнопки при сборке, а не берёт его из `--bs-primary` в рантайме). Все CDN-подключения — с SRI-хешами.

## Тесты и линтер

```bash
pip install -r requirements-dev.txt

ruff check .      # статический анализ, обязателен без ошибок
pytest            # unit (crypto, repository) + integration (API) тесты, Redis не нужен — используется fakeredis
```

## Структура проекта

```
app/
  core/            # конфигурация, логирование, шифрование, доменные исключения
  api/v1/          # HTTP-роуты
  schemas/         # Pydantic-модели запросов/ответов
  services/        # бизнес-логика
  repositories/    # доступ к данным (Redis)
  main.py          # сборка FastAPI-приложения, middleware, статика
static/            # фронтенд: index.html, view.html, css/, js/
tests/             # unit и integration тесты (pytest)
Dockerfile
docker-compose.yml
```
