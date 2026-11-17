# Практическая работа 4 — Кассиопея

Рефакторинг проекта Rust/Axum + Laravel/Bootstrap + PostgreSQL + Pascal LegacyCSV.
Исходник и ревизия указаны в [docs/UPSTREAM.md](docs/UPSTREAM.md). Решение: https://github.com/Lucky21211/rab4_optim_prog_code

## Что изменено

- Rust разделён на routes, handlers, services, clients, repo, domain, config; зависимости передаются через AppState.
- Единый reqwest Client, timeout/connect timeout, User-Agent, ограниченные retry только для сетевых сбоев, 429 и 5xx; лимит частоты по host.
- Планировщик читает интервалы из env; транзакционные advisory locks предотвращают наложение одного задания, semaphore ограничивает параллелизм.
- SQL находится только в репозиториях. TIMESTAMPTZ декодируется в DateTime<Utc>. Upsert OSDR учитывает predicate уникального индекса; space_cache ограничен одной записью на source.
- Контроллеры Laravel используют сервисы и интерфейсы. Dashboard получает ViewModel; из Blade удалены SQL и HTTP. Ошибки JSON API имеют HTTP 200 и ok=false/error.code/message/trace_id.
- Redis Cache-Aside и single-flight lock снижают повторные обращения; CMS проходит allowlist-очистку HTML; динамический JS использует textContent и безопасные URL.
- AstronomyAPI исправлен по документации: отдельные sun/moon, from_date/to_date и обязательные параметры.
- Python CLI сохраняет имена методов и CSV-контракт Pascal. Явный cron, stdout/stderr, транзакционный COPY и идемпотентный импорт.
- Секреты исходника удалены из рабочих конфигов и новой Git-истории. Локальный .env исключён из Git.

## Запуск через Docker Compose

Нужен работающий Docker Desktop с Linux containers/WSL 2 и Docker Compose 2.24.4 или новее.
В папке rabota4 уже создан приватный .env с локальными APP_KEY и паролем БД; они не публикуются.
После клонирования с GitHub создайте приватный .env через Compose; уже существующий файл команда не перезаписывает:

```bash
docker compose -f compose.setup.yml run --rm init
```

Команда генерирует случайный URL-safe пароль БД и APP_KEY; значения не выводятся в журнал.

```bash
docker compose config --quiet
docker compose up --build -d --wait
docker compose ps
```

Сайт: http://localhost:8080/dashboard. Rust: http://localhost:8081/health.
Внешние ключи NASA_API_KEY, JWST_API_KEY, JWST_EMAIL, ASTRO_APP_ID и ASTRO_APP_SECRET задаются в .env. Без действительных ключей защищённые поставщики возвращают явную ошибку; остальные страницы продолжают открываться. Чужие ключи из задания не используются.

```bash
docker compose logs -f rust_iss php pascal_legacy
docker compose down
```

down сохраняет данные. Флаг -v использовать только для удаления данных своего стенда.
Исходники Laravel и зависимости устанавливаются при сборке образа, а не при старте. Entrypoint синхронизирует приложение в собственный appdata и применяет миграции. Не подключайте чужой существующий каталог к этому тому.

## Изолированные проверки без реальных внешних API

Тестовые fixtures не являются космическими наблюдениями. Снимки интерфейса тестового стенда должны быть подписаны соответствующим образом.

```bash
docker compose -f docker-compose.yml -f compose.test.yml -p cassiopeia_pr4_test up --build -d --wait
docker compose -f docker-compose.yml -f compose.test.yml -p cassiopeia_pr4_test --profile test run --rm tests
docker compose -f docker-compose.yml -f compose.test.yml -p cassiopeia_pr4_test --profile test run --rm rust_tests
docker compose -f docker-compose.yml -f compose.test.yml -p cassiopeia_pr4_test --profile test run --rm php_tests
docker compose -f docker-compose.yml -f compose.test.yml -p cassiopeia_pr4_test --profile test run --rm browser
```

Тестовый сайт: http://localhost:18080/dashboard. Rust: http://localhost:18081/health.
Полный прогон, проверка сохранности, снимки и логи также предусмотрены в GitHub Actions `.github/workflows/acceptance.yml`.

## Документация

- [Контракты и приёмка](docs/ACCEPTANCE.md)
- [LegacyCSV и план миграции](docs/LEGACY_CONTRACT.md)
- [Источники и ссылки задания](docs/UPSTREAM.md)

Готовый [отчёт Word](docs/Отчет_практическая_работа_4.docx), диаграммы и фактические подтверждения находятся в docs. Снимки и журналы сохранены в docs/evidence; генератор отчёта — tools/build_report.py.
