# Контракт LegacyCSV и план замены

Исходник `services/pascal-legacy/legacy.pas` написан на Object Pascal, компилятор Free Pascal; сохранён как материал сравнения. Активная реализация — Python 3.12, `legacy.py`. Названия `GetEnvDef`, `RandFloat`, `GenerateAndCopy` сохранены. RandFloat использует ту же формулу `minV + random * (maxV - minV)`; RNG Python и Pascal не обещают одинаковую последовательность.

## CSV

- Имя: `telemetry_YYYYMMDD_HHMMSS.csv`.
- Кодировка UTF-8, разделитель запятая, LF, первая строка — заголовок.
- Колонки и порядок: `recorded_at,voltage,temp,source_file`.
- Одна строка данных на запуск.
- `recorded_at`: `YYYY-MM-DD HH:MM:SS`; процесс и сеанс PostgreSQL работают в UTC.
- `voltage`: случайное значение `[3.2, 12.6)` с форматированием до двух знаков.
- `temp`: случайное значение `[-50, 80)` с форматированием до двух знаков.
- После округления крайняя отображаемая величина может совпасть с верхней границей.
- `source_file`: basename текущего файла.

## Запись в таблицу

`telemetry_legacy(id BIGSERIAL PK, recorded_at TIMESTAMPTZ, voltage NUMERIC(6,2), temp NUMERIC(6,2), source_file TEXT)`.

Бизнес-ключ `(source_file, recorded_at)` уникален. Импорт выполняется COPY FROM STDIN во временную таблицу и INSERT ON CONFLICT DO NOTHING, в одной транзакции с advisory lock. Повторный импорт того же CSV не добавляет дубликат. shell-команды из данных не собираются.

## Расписание и эксплуатация

`LEGACY_CRON=*/5 * * * *` задаёт запуск каждые пять минут; timezone UTC. Entrypoint создаёт crontab с фиксированной командой и запускает crond в foreground. Убраны бесконечный цикл и компиляция на каждом старте. JSON-события legacy_generated/legacy_imported идут в stdout; legacy_failed — в stderr.

```bash
docker compose exec pascal_legacy python /app/legacy.py
docker compose exec pascal_legacy python /app/legacy.py --csv-only
docker compose exec pascal_legacy python /app/legacy.py --import-file /data/csv/telemetry_YYYYMMDD_HHMMSS.csv
```

Секреты БД передаются через окружение libpq. Каталог CSV хранится в отдельном томе. Эксклюзивное создание файла предотвращает перезапись файла при совпадении времени до секунды; такая коллизия даёт ненулевой exit code.

## План перехода

1. Зафиксировать схему CSV и проверить диапазоны, формулу, точность и UTC на тестовом стенде.
2. Запустить новую CLI с `--csv-only`, сопоставить контракт с Pascal без параллельного импорта.
3. Применить уникальный индекс и проверить повторную загрузку fixture.
4. Остановить прежний scheduler; включить только cron новой CLI.
5. Проверить журнал, CSV и появление ровно одной записи.
6. Для отката отключить новый cron, сохранив CSV и таблицу; два импортёра одновременно не включать.
