"""Build the assignment report from source code and actual acceptance evidence."""
from pathlib import Path
import json
import re
import textwrap
from PIL import Image, ImageDraw, ImageFont
from docx import Document
from docx.shared import Cm, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'docs'
EVIDENCE = ROOT / 'artifacts'
if not (EVIDENCE / 'test-results/run.json').exists(): EVIDENCE = DOCS / 'evidence'
ASSETS = DOCS / 'diagrams'
ASSETS.mkdir(parents=True, exist_ok=True)

EFFECTS = [
 ('Rust', 'Монолитный main.rs', 'Слои и AppState', 'Layered architecture и DI', 'Код разбит на отдельные слои; маршруты не содержат SQL, зависимости передаются через AppState и служат для тестирования.'),
 ('HTTP', 'Разные клиенты и ошибки', 'Один клиент, тайм-ауты, retry и rate limit', 'Adapter и bounded retry', 'Внешние запросы имеют общий клиент, таймауты и ограниченные повторы; ошибки содержат код и trace_id без утечки секретов.'),
 ('БД', 'Лишние снимки и дубликаты', 'Upsert и индексы; summary за три запроса', 'Repository и бизнес ключ', 'Сохраняется одна запись на источник; upsert по ключу исключает дубликаты, а индекс ускоряет ограниченные выборки данных.'),
 ('Redis', 'Повторные обращения к БД и API', 'TTL и блокировка заполнения ключа', 'Cache Aside и single flight', 'Повторные чтения используют Redis; блокировка одного ключа исключает параллельные одинаковые запросы к внешнему сервису.'),
 ('Laravel', 'Логика в контроллерах и Blade', 'Сервисы, интерфейсы и ViewModel', 'Strategy и Adapter', 'SQL и HTTP удалены из Blade; сервис формирует ViewModel, а интерфейсы поставщиков помогают подменять источники в тестах.'),
 ('Legacy', 'Бесконечный цикл и shell import', 'Python CLI, cron и COPY FROM STDIN', 'Strangler и идемпотентный импорт', 'CSV сохраняет структуру, точность и диапазоны; повторный импорт идемпотентен, cron явно задаёт время запуска Python CLI.'),
 ('Защита', 'Ключи в коде и сырая разметка', 'Env, allowlist HTML и валидация', 'Validation и output encoding', 'Секреты заданы в env; CMS очищает HTML, загрузка проверяет тип файла, CSRF включена, а JSON выводится через textContent.'),
]
assert all(len(row[-1]) == 120 for row in EFFECTS)

def diagrams():
    font_path = 'C:/Windows/Fonts/arial.ttf'
    if not Path(font_path).exists(): font_path = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
    font = ImageFont.truetype(font_path, 25)
    def image(name, boxes, arrows, size=(1600,800)):
        im=Image.new('RGB',size,'white'); d=ImageDraw.Draw(im)
        for a,b in arrows:
            d.line([a,b],fill='#555555',width=4)
            x,y=b; dx,dy=x-a[0],y-a[1]
            if abs(dx)>=abs(dy): d.polygon([(x,y),(x-(12 if dx>0 else -12),y-7),(x-(12 if dx>0 else -12),y+7)],fill='#555555')
            else: d.polygon([(x,y),(x-7,y-(12 if dy>0 else -12)),(x+7,y-(12 if dy>0 else -12))],fill='#555555')
        for box,label in boxes:
            d.rounded_rectangle(box,radius=12,fill='#F0F3F6',outline='#707984',width=2)
            d.multiline_text(((box[0]+box[2])/2,(box[1]+box[3])/2),label,font=font,fill='black',anchor='mm',align='center',spacing=9)
        im.save(ASSETS/name)
    image('before.png',[
      ((30,60,270,190),'Браузер\nDashboard'),((340,60,580,190),'Nginx'),((650,60,980,190),'Laravel\nHTTP в контроллерах'),
      ((650,300,980,450),'Blade\nSQL и сырой HTML'),((1130,60,1540,190),'Внешние API\nJWST и Astronomy'),
      ((650,580,980,730),'Rust main.rs\nHTTP и SQL'),((1130,580,1540,730),'PostgreSQL\nЛоги и данные'),
      ((30,580,400,730),'Pascal\nCSV и psql'),((1130,300,1540,450),'NASA и ISS API')
    ],[((270,125),(340,125)),((580,125),(650,125)),((980,125),(1130,125)),((815,190),(815,300)),((980,375),(1330,580)),((815,450),(815,580)),((980,655),(1130,655)),((400,655),(650,655)),((1335,450),(980,580))])
    image('after.png',[
      ((30,40,270,160),'Браузер'),((340,40,580,160),'Nginx'),((650,40,980,160),'Laravel\nТонкие контроллеры'),
      ((650,250,980,400),'Сервисы и порты\nGallery и Events'),((1130,250,1540,400),'Redis\nTTL и single flight'),
      ((650,510,980,660),'Rust AppState\nСлои и repo'),((1130,510,1540,660),'Внешние API\nЕдиный HTTP клиент'),
      ((650,770,980,900),'PostgreSQL\nМиграции и upsert'),((30,770,400,900),'Python LegacyCSV\nCron и COPY')
    ],[((270,100),(340,100)),((580,100),(650,100)),((815,160),(815,250)),((980,325),(1130,325)),((815,400),(815,510)),((980,585),(1130,585)),((815,660),(815,770)),((400,835),(650,835))],(1600,950))
    image('cache-flow.png',[
      ((30,80,320,240),'Запрос и\nвалидация'),((420,80,780,240),'Поиск ключа\nв Redis'),((1040,80,1510,240),'HIT\nВозврат ответа'),
      ((420,400,780,560),'MISS\nLock ключа'),((1040,400,1510,560),'Чтение источника\nУспех → кэш с TTL'),
      ((1040,670,1510,800),'Ошибка → ok=false\nНе кэшировать')
    ],[((320,160),(420,160)),((780,160),(1040,160)),((600,240),(600,400)),((780,480),(1040,480)),((1275,560),(1275,670))],(1600,850))

def main():
    status_file = EVIDENCE / 'test-results/run.json'
    if not status_file.exists(): raise RuntimeError('Acceptance run metadata is required before publishing the report')
    run = json.loads(status_file.read_text(encoding='utf-8'))
    if run['conclusion'] != 'success': raise RuntimeError('Do not report a failed acceptance run as complete')
    for name in ['dashboard','iss','osdr','cms']:
        if not (EVIDENCE/'screenshots'/f'{name}.png').exists(): raise RuntimeError(f'Missing actual screenshot: {name}')
    diagrams()
    doc=Document(); sec=doc.sections[0]
    sec.page_width=Cm(21); sec.page_height=Cm(29.7)
    sec.top_margin=Cm(2); sec.bottom_margin=Cm(2); sec.left_margin=Cm(2.5); sec.right_margin=Cm(1.5)
    normal=doc.styles['Normal']; normal.font.name='Times New Roman'; normal.font.size=Pt(12)
    normal.paragraph_format.line_spacing=1.15; normal.paragraph_format.space_after=Pt(7)
    for name,size in [('Title',20),('Subtitle',15),('Heading 1',15),('Heading 2',13)]:
        doc.styles[name].font.name='Times New Roman'; doc.styles[name].font.size=Pt(size);doc.styles[name].font.color.rgb=RGBColor(0,0,0)
    doc.styles['Caption'].font.name='Times New Roman'; doc.styles['Caption'].font.size=Pt(10)
    doc.styles['Caption'].font.color.rgb=RGBColor(0,0,0)
    sec.different_first_page_header_footer=True
    footer=sec.footer.paragraphs[0];footer.alignment=WD_ALIGN_PARAGRAPH.CENTER
    fld=OxmlElement('w:fldSimple');fld.set(qn('w:instr'),'PAGE');footer._p.append(fld)
    def p(text='',bold=False):
        paragraph=doc.add_paragraph();paragraph.add_run(text).bold=bold;return paragraph
    def title(text): doc.add_heading(text,level=1)
    def sub(text): doc.add_heading(text,level=2)
    def page():doc.add_page_break()
    def code(text):
        for line in [part for raw in text.strip().splitlines() for part in (textwrap.wrap(raw, width=92, replace_whitespace=False, drop_whitespace=False) or [''])]:
            para=doc.add_paragraph();para.paragraph_format.space_after=Pt(0);para.paragraph_format.line_spacing=1
            run=para.add_run(line);run.font.name='Consolas';run.font.size=Pt(9)
        p()
    def figure(file,caption,width=16.5,max_height=19):
        with Image.open(file) as im: w,h=im.size
        width=min(width,max_height*w/h)
        para=doc.add_paragraph();para.alignment=WD_ALIGN_PARAGRAPH.CENTER
        para.add_run().add_picture(str(file),width=Cm(width))
        doc.add_paragraph(caption,style='Caption').alignment=WD_ALIGN_PARAGRAPH.CENTER
    def table(headers,rows,widths):
        t=doc.add_table(rows=1,cols=len(headers));t.alignment=WD_TABLE_ALIGNMENT.CENTER;t.autofit=False
        for i,w in enumerate(widths):t.columns[i].width=Cm(w)
        for i,c in enumerate(headers):t.rows[0].cells[i].text=c
        for row in rows:
            cells=t.add_row().cells
            for i,value in enumerate(row):cells[i].text=str(value)
        for n,row in enumerate(t.rows):
            prop=row._tr.get_or_add_trPr();prop.append(OxmlElement('w:cantSplit'))
            if n==0:prop.append(OxmlElement('w:tblHeader'))
            for i,cell in enumerate(row.cells):
                cell.width=Cm(widths[i]);cell.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
                tc=cell._tc.get_or_add_tcPr();borders=OxmlElement('w:tcBorders')
                for side in ['top','left','bottom','right']:
                    el=OxmlElement('w:'+side);el.set(qn('w:val'),'single');el.set(qn('w:sz'),'4');el.set(qn('w:color'),'D9D9D9');borders.append(el)
                tc.append(borders)
                if n==0:
                    fill=OxmlElement('w:shd');fill.set(qn('w:fill'),'EAEAEA');tc.append(fill)
                for para in cell.paragraphs:
                    para.paragraph_format.space_after=Pt(4);para.paragraph_format.space_before=Pt(4);para.paragraph_format.line_spacing=1.05
                    for run in para.runs:run.font.size=Pt(10);run.bold=n==0
        p()
    p('Дисциплина Рефакторинг программного кода').alignment=WD_ALIGN_PARAGRAPH.CENTER
    p();p();doc.add_paragraph('Отчёт по практической работе 4',style='Title').alignment=WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph('Рефакторинг проекта Кассиопея',style='Subtitle').alignment=WD_ALIGN_PARAGRAPH.CENTER
    p('Оптимизация архитектуры и интеграций космического Dashboard').alignment=WD_ALIGN_PARAGRAPH.CENTER
    p();p();p('Выполнил ____________________________________').alignment=WD_ALIGN_PARAGRAPH.RIGHT
    p('Группа _______________________________________').alignment=WD_ALIGN_PARAGRAPH.RIGHT
    p('Проверил _____________________________________').alignment=WD_ALIGN_PARAGRAPH.RIGHT
    p();p('2026').alignment=WD_ALIGN_PARAGRAPH.CENTER
    page();title('1 Цель работы и исходный проект')
    p('Цель — устранить архитектурные дефекты распределённого монолита, стабилизировать внешние интеграции и повысить тестируемость и производительность при сохранении страниц и успешных контрактов API.')
    p('Проект включает Rust Axum и SQLx, Laravel с Bootstrap, PostgreSQL, Nginx и генератор LegacyCSV на Object Pascal. Анализ охватил все исходные файлы, включая конфигурации, Blade, SQL, дубли JwstHelper, остатки .orig/.rej и опубликованные настройки окружения.')
    p('В исходнике Rust-логика находилась в main.rs, SQL и HTTP смешивались с обработчиками. Dashboard делал SQL из Blade и трижды вставлял CMS. CMS-контроллер обращался к отсутствующей cms_blocks, тогда как init.sql создавал cms_pages. Графики ожидали points, отсутствовавший в trend. Секреты были записаны в Compose и .env.')
    figure(ASSETS/'before.png','Рисунок 1 — Фактические зависимости до рефакторинга',max_height=12)
    p('Использована исходная ревизия 898965c7dce4cc50a145a8c141e56dd8e9adf7e6. Публичный демонстрационный Dashboard по ссылке задания не ответил за 12 секунд; его состояние не использовалось как доказательство результата.')
    page();title('2 Архитектура после рефакторинга')
    figure(ASSETS/'after.png','Рисунок 2 — Состав модулей и точки интеграции после рефакторинга',max_height=12)
    p('Rust и Laravel сохранены. Laravel обновлён с шаблона 11 до 12 при сохранении маршрутов и пользовательских функций; это обновление фреймворка, а не смена стека. LegacyCLI перенесён на Python с отдельным контрактом и планом замены.')
    code('services/rust-iss/src/\n  routes/ handlers/ services/ clients/ repo/ domain/ config/\nservices/php-web/laravel-patches/app/\n  Contracts/ Clients/ Services/ Repositories/ ViewModels/\n  Http/Controllers/ Support/ Providers/\nservices/pascal-legacy/legacy.py\ndb/  tests/  docs/  docker-compose.yml  compose.test.yml')
    p('AppState содержит PgPool, общий HTTP-клиент, конфигурацию и semaphore. Конфигурация проверяется при старте. Задания читают интервалы из env; advisory transaction lock исключает одновременную работу одного source, а semaphore ограничивает число заданий и расход соединений.')
    page();title('3 Rust и внешние API')
    p('Обработчики принимают State<AppState> и возвращают Result<Json<T>, ApiError>. В handlers отсутствуют SQL и прямые HTTP-вызовы. IssRepo, OsdrRepo и CacheRepo отвечают за БД; clients — за ISS, OSDR, JWST и AstronomyAPI; services — за сбор и расчёт тренда.')
    sub('Единый HTTP клиент и ошибки')
    p('Один reqwest Client переиспользует соединения. Настроены connect timeout, общий timeout, User-Agent и ограниченный размер тела 8 МиБ. Повторяются только сетевые ошибки, 429 и 5xx, до двух раз с задержкой. 401/403 не повторяются. Rate limit группирует запросы по host; APOD, NEO и DONKI делят очередь NASA в рамках процесса.')
    code('Json(json!({\n  "ok": false,\n  "error": {\n    "code": self.code, "message": self.message,\n    "trace_id": self.trace_id\n  }\n})).into_response()')
    p('JSON API возвращает HTTP 200 при ошибках приложения и интеграций по требованию задания. Laravel сохраняет trace_id из Rust. Успешные ответы не обёрнуты в новый объект. Защитные ответы HTML-форм и навигация сохраняют HTTP 419/404; правило 200 относится к JSON API. Клиент проверяет ok=false.')
    sub('Стабилизация поставщиков')
    p('OSDR-словарь OSD-* разворачивается до записи, ключ dataset_id становится бизнес-ключом. AstronomyAPI исправлен по документации: /events/sun и /events/moon, from_date/to_date, elevation и time; результаты нормализуются для таблицы, а raw сохраняется. Фильтры JWST проверяются до HTTP-вызова. URL и ключи берутся из окружения или *_FILE, а не из клиентских параметров.')
    p('Переход на другой язык для Rust-сервиса не обоснован: проблемы вызваны смешением ответственности и конфигурацией. Для сборки зафиксирован Rust 1.92.0 и Cargo.lock, чтобы изменение floating-тега не ломало SQLx.')
    page();title('4 База данных и производительность')
    table(['Таблица','Назначение и ключ'],[
      ('iss_fetch_log','История ISS; id, fetched_at TIMESTAMPTZ, source_url, payload JSONB.'),
      ('osdr_items','Карточки исследований; частичный UNIQUE dataset_id, updated_at TIMESTAMPTZ и raw JSONB.'),
      ('space_cache','Текущий снимок source; UNIQUE source, fetched_at TIMESTAMPTZ, payload JSONB.'),
      ('telemetry_legacy','CSV-телеметрия; UNIQUE source_file и recorded_at, voltage/temp NUMERIC(6,2).'),
      ('cms_blocks','CMS; UNIQUE slug, title, content и is_active; перенос данных из cms_pages.')
    ],[4.2,12.3])
    p('TIMESTAMPTZ представляет момент времени; DateTime<Utc> сохраняет временную зону при декодировании и сериализации. Ошибочная дата не заменяется текущим временем. В старом коде DateTime<Utc> уже применялся, но парсер timestamp мог маскировать ошибку через now; это поведение исправлено.')
    p('Upsert обновляет существующую сущность по бизнес-ключу; слепой INSERT добавляет дубликаты. Для OSDR ON CONFLICT(dataset_id) использует WHERE dataset_id IS NOT NULL, согласованный с частичным индексом. Для space_cache upsert ограничивает таблицу одной строкой на источник. ISS остаётся историческим журналом, поскольку история нужна графикам.')
    code('INSERT INTO space_cache(source,payload) VALUES($1,$2)\nON CONFLICT(source) DO UPDATE\nSET fetched_at=now(), payload=EXCLUDED.payload;')
    p('Summary получает пять снимков одним запросом; вместе с последним ISS и count OSDR это три round trips вместо семи. Индекс inserted_at DESC/id DESC поддерживает ограниченную выборку OSDR. SQLx выполняет миграции при старте Rust, Laravel — свои миграции при старте PHP. Именованные тома сохраняют данные после down/up.')
    page();title('5 Кэширование и веб слой')
    figure(ASSETS/'cache-flow.png','Рисунок 3 — Cache Aside с блокировкой заполнения',max_height=10)
    p('Redis разгружает основную PostgreSQL и внешние API. ISS и OSDR кэшируются на 10 секунд, JWST и события — на 120, CMS — на 60. Ключ содержит путь и отсортированные параметры. Cache::lock предотвращает stampede при одновременном холодном чтении; ошибки не сохраняются. TTL ограничивает устаревание.')
    p('Контроллеры Laravel выполняют валидацию и делегируют работу сервисам. SpaceDataSource отделяет HTTP-адаптер RustClient от CachedSpaceService. GalleryProvider и EventProvider позволяют подменять поставщиков через контейнер зависимостей. Выбранные паттерны — Adapter, Strategy, Repository и Cache-Aside.')
    p('JWST и AstronomyAPI не считаются взаимозаменяемыми по произвольному JSON: новый поставщик должен реализовать соответствующий интерфейс и нормализовать ответ до того же контракта. Этот подход проверяется fake GalleryProvider в тесте Laravel.')
    p('DTO задаёт контракт переноса данных, а ViewModel — набор данных для конкретного представления. DashboardViewModel содержит iss, безопасный cmsHtml и warning. SQL, HTTP и бизнес-логика удалены из Blade; шаблон отвечает за отображение и безопасную работу с DOM.')
    page();title('6 Безопасность и совместимость')
    p('Ключи upstream не перенесены в решение; локальный .env исключён из Git. История решения начинается заново, чтобы не публиковать секреты старых коммитов. Порты PostgreSQL и Redis не опубликованы; сайт и диагностический Rust-порт доступны на loopback. APP_DEBUG выключен, логи направлены в stderr.')
    p('SQL-параметры передаются через bind или Query Builder. limit, координаты, дни, program, suffix и instrument ограничены по диапазонам и формату. Клиент не может указать произвольный upstream URL. Перенаправления внешнего HTTP-клиента выключены.')
    p('CMS очищается по allowlist тегов и атрибутов с запретом внешних сущностей XML. Динамические подписи и астрономические значения выводятся через textContent; ссылки допускают только http/https. Upload проверяет MIME, размер и хранит файлы вне public под сгенерированными именами. Исключение CSRF для upload удалено.')
    p('Сохранены /dashboard, /iss, /osdr, /page/{slug}, API ISS, JWST и Astronomy. Восстановлена доступность /iss и добавлен points в trend без удаления старых полей. Миграция создаёт cms_blocks и переносит существующие cms_pages. Дубли CMS, нерабочий layout и остатки конфликтов .orig/.rej устранены.')
    sub('Фрагмент внедрения зависимостей')
    code("$this->app->bind(SpaceDataSource::class, RustClient::class);\n$this->app->bind(GalleryProvider::class, JwstGalleryProvider::class);\n$this->app->bind(EventProvider::class, AstronomyEventProvider::class);")
    p('Frontend-библиотеки Bootstrap, Leaflet и Chart.js включены в образ из зафиксированных npm-версий; сайт не загружает исполняемые библиотеки из CDN при каждом открытии. Картографические тайлы остаются внешним ресурсом.')
    page();title('7 LegacyCSV и план замены')
    p('LegacyCSV — консольная программа Object Pascal для Free Pascal. Активный контейнер теперь выполняет Python 3.12 CLI. Сохранены имена GetEnvDef, RandFloat и GenerateAndCopy, формула генерации, порядок колонок и две десятичные цифры. Совпадение псевдослучайных последовательностей разных языков не обещается.')
    code("def RandFloat(minV, maxV, rng=None):\n    return minV + (rng or random).random() * (maxV - minV)\n\nFIELDS = ['recorded_at', 'voltage', 'temp', 'source_file']")
    p('CSV: UTF-8, запятая, LF, заголовок и одна строка. Имя telemetry_YYYYMMDD_HHMMSS.csv; recorded_at в UTC, voltage в [3.2,12.6), temp в [-50,80), формат 0.00. После округления отображаемое число может достигать верхней границы.')
    p('Cron задаётся через LEGACY_CRON, по умолчанию */5 * * * *. Entrypoint запускает crond в foreground. Импорт использует psycopg COPY FROM STDIN во временную таблицу и INSERT ON CONFLICT DO NOTHING в одной транзакции с advisory lock. Повторный CSV не создаёт дубликат. Логи — JSON в stdout/stderr, ошибки дают ненулевой exit code.')
    p('План перехода: зафиксировать CSV-контракт; сравнить генерацию в режиме --csv-only; применить уникальный индекс; проверить повторный импорт; остановить старый цикл; включить только новый cron и проверить одну запись. При откате сохранить CSV и данные, отключив новый scheduler. Подробный контракт и команды находятся в docs/LEGACY_CONTRACT.md.')
    page();title('8 Таблица изменений и эффект')
    p('Каждая ячейка столбца «Эффект» содержит ровно 120 символов, включая пробелы и знаки препинания; длины проверяются программно при сборке отчёта.')
    table(['Модуль','Проблема','Решение','Паттерн','Эффект'],EFFECTS[:4],[1.3,2.6,3.0,2.6,7.0])
    page();title('8 Таблица изменений и эффект продолжение')
    table(['Модуль','Проблема','Решение','Паттерн','Эффект'],EFFECTS[4:],[1.3,2.6,3.0,2.6,7.0])
    p('Эффект отделён от абсолютного времени ответа: сокращение числа запросов проверяется счётчиком mock и SQL-структурой; универсальный процент ускорения без одинакового стенда и данных не приводится.')
    page();title('9 Результаты проверки')
    p('Проверки выполнены через Docker Compose в изолированном стенде GitHub Actions. Использованы PostgreSQL, Redis, реальный Rust и Laravel, Python CLI и mock внешних провайдеров. Fixture-изображения и события демонстрируют интерфейс и контракты, а не реальные наблюдения NASA.')
    p('Успешный прогон: '+run['html_url'])
    p('Ревизия проверенного кода: '+run['head_sha'])
    table(['Набор','Что подтверждено'],[
      ('Rust unit','Haversine, числовые строки, URL, словарь OSDR, неверный timestamp.'),
      ('Laravel','Подмена GalleryProvider, envelope HTTP 200, валидация и очистка HTML.'),
      ('Интеграция','Сбор и upsert; страницы и API; 403 и 429; Cache-Aside; job lock; UTC и legacy import; CSRF.'),
      ('Браузер','Dashboard, ISS, OSDR и CMS; скриншоты реального тестового приложения, отсутствие JS pageerror.'),
      ('Сохранность','Пересоздание контейнеров без удаления volumes сохраняет число записей ISS.')
    ],[3.2,13.3])
    for filename in ['rust.log','php.log','integration.log','browser.log','persistence.log']:
        log=(EVIDENCE/'test-results'/filename).read_text(encoding='utf-8',errors='replace')
        selected=[line for line in log.splitlines() if re.search(r'test result:|Tests:|Ran \d+ tests|^OK|browser_checks_passed|ISS persisted',line)]
        if selected: code(filename+'\n'+'\n'.join(selected)[-1300:])
    page();title('10 Скриншоты интерфейса')
    figure(EVIDENCE/'screenshots/dashboard.png','Рисунок 4 — Dashboard на изолированном тестовом стенде',max_height=21)
    page();title('10 Скриншоты интерфейса продолжение')
    figure(EVIDENCE/'screenshots/iss.png','Рисунок 5 — Данные МКС и тренд',max_height=9)
    figure(EVIDENCE/'screenshots/osdr.png','Рисунок 6 — Таблица OSDR с тестовым исследованием',max_height=9)
    page();title('11 Журналы и подтверждение результата')
    figure(EVIDENCE/'screenshots/cms.png','Рисунок 7 — Страница CMS после переноса и очистки содержимого',max_height=8)
    log=(EVIDENCE/'logs/compose.log').read_text(encoding='utf-8',errors='replace')
    selected=[line for line in log.splitlines() if any(s in line for s in ['collection_complete','server_started','php_ready','legacy_cron_started'])]
    p('Фрагменты фактического журнала контейнеров:')
    code('\n'.join(selected[:7])[:2300])
    p('Полные stdout/stderr и результаты тестов приложены к указанному прогону как acceptance-evidence. trace_id используется для ошибок; ключи, DSN и ответы с секретами в прикладные логи не включаются.')
    page();title('12 Выводы и рекомендации')
    p('Рефакторинг сохранил пользовательские страницы и назначение модулей, устранив смешение слоёв и дефекты контрактов. Наиболее прямой эффект дают общий HTTP-клиент, ограниченные повторы, Redis с single-flight и SQL-агрегация снимков. Upsert и уникальные ключи обеспечивают идемпотентность справочника OSDR, текущих снимков и повторного legacy import.')
    p('Автоматические проверки подтверждают работоспособность контейнерного решения на тестовых источниках. Работа реальных защищённых JWST и AstronomyAPI требует собственных действительных ключей; тестовый стенд не подтверждает квоты или доступность сторонних сервисов. Rate limit является локальным для процесса: при масштабировании collector потребуется общий лимитер Redis и мониторинг квот.')
    p('Рекомендуются политика хранения исторических ISS-записей, метрики p95 и cache-hit ratio, наблюдение по trace_id, CI-аудит зависимостей и фиксация digest образов. Сначала следует измерить реальные объёмы и нагрузку; read replica PostgreSQL не вводилась, поскольку Redis снимает повторные чтения без дополнительной согласованности реплики.')
    sub('Решение и материалы')
    for text in [
      'Репозиторий решения: https://github.com/Lucky21211/rab4_optim_prog_code',
      'Успешная проверка: '+run['html_url'],
      'Исходник: https://gitverse.ru/stasnorman/he-path-of-the-samurai',
      'AstronomyAPI Events: https://docs.astronomyapi.com/endpoints/bodies/events',
      'OSDR: https://visualization.osdr.nasa.gov/biodata/api/',
      'NASA API: https://api.nasa.gov/',
      'Задание: Практическая работа №4.pdf, страницы 1–4. Требования к отчёту — страница 4.',
    ]:p(text)
    doc.core_properties.title='Рефакторинг проекта Кассиопея Практическая работа 4'
    doc.core_properties.author=''
    target=DOCS/'Отчет_практическая_работа_4.docx'
    doc.save(target)
    (DOCS/'effects.json').write_text(json.dumps([{'module':r[0],'effect':r[-1],'characters':len(r[-1])}for r in EFFECTS],ensure_ascii=False,indent=2),encoding='utf-8')
    print(target)

if __name__=='__main__':main()
