# Исходные материалы

Задание: «Практическая работа №4.pdf», 4 страницы. Все страницы и обе ссылки просмотрены.

- Исходный проект: https://gitverse.ru/stasnorman/he-path-of-the-samurai
- Исходная ревизия: `898965c7dce4cc50a145a8c141e56dd8e9adf7e6`.
- Указанный в задании демонстрационный сайт: http://95.163.232.216:8080/dashboard
- Решение: https://github.com/Lucky21211/rab4_optim_prog_code

В PDF нет отдельного раздела «Паттерн для производительности» и отсутствуют упомянутые «сценарии приёмки в конце». В исходном Readme.md они также отсутствуют. Приёмочные проверки составлены по действующим маршрутам, структуре ответов, Blade-шаблонам и явным требованиям задания; они находятся в tests/ и в Laravel tests/Feature.

Ключи из публичного исходного репозитория не используются. Удалена их копия из текущих конфигураций. История upstream, содержащая опубликованные ключи, не включается в историю решения.

## Проверенные первичные источники

- OSDR Biological Data API: https://visualization.osdr.nasa.gov/biodata/api/
- NASA OSDR API: https://www.nasa.gov/osdr-api/
- NASA APOD, NEO, DONKI: https://api.nasa.gov/
- ISS: https://api.wheretheiss.at/w/documentation
- AstronomyAPI authentication: https://docs.astronomyapi.com/
- AstronomyAPI Events: https://docs.astronomyapi.com/endpoints/bodies/events
- JWST: https://api.jwstapi.com — в исходнике используется сторонний API JWST, не официальный сервис NASA.

AstronomyAPI требует /events/:body и from_date/to_date/elevation/time. Прежний URL без тела и параметры from/to исправлены в Rust-клиенте. Ключи JWST/AstronomyAPI необходимо получить самостоятельно: их действительность не подтверждается тестовыми fixtures.
