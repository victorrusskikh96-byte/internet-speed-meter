# Задачи: измеритель скорости загрузки HTTP-ресурса

> Порядок задач учитывает зависимости. Core-реализация начинается только после завершения bootstrap.

## Этап 1. Project bootstrap

- [x] **T001** Настроить `pyproject.toml`: metadata, Python 3.12+, runtime-зависимость `httpx`, dev-зависимости и entry point `internet-speed-meter`. [FR-001] [NFR-001]
- [x] **T002** Добавить `.python-version` и `.gitignore` для Python, `uv`, test/type/lint/build artifacts и IDE-файлов. [NFR-001]
- [x] **T003** Создать минимальный `src`-layout с package `internet_speed_meter` и пустым `__init__.py`, не добавляя measurement implementation. [NFR-005]
- [x] **T004** Настроить в `pyproject.toml` умеренные правила `pytest`, `ruff` и `mypy` без необоснованно строгих suppressions. [NFR-003]
- [x] **T005** Выполнить `uv sync` и зафиксировать воспроизводимый `uv.lock`. [NFR-001]
- [x] **T006** Добавить минимальный smoke test импорта package и запустить bootstrap quality checks. [NFR-003]

## Этап 2. Core models и calculations

- [x] **T007** Добавить неизменяемую модель результата одной попытки с длительностью и числом фактически полученных bytes. [FR-007]
- [x] **T008** Добавить неизменяемую итоговую модель для request count, total duration, average duration, total bytes, MB, MB/s и Mbps. [FR-008] [FR-009] [FR-010] [FR-011]
- [x] **T009** Реализовать проверку ровно 10 результатов и положительной длительности каждой попытки до агрегации. [FR-003] [ERR-005]
- [x] **T010** Реализовать расчёт total duration, среднего времени, total bytes и десятичных MB без промежуточного округления. [FR-008] [FR-009]
- [x] **T011** Реализовать MB/s и Mbps из total bytes / total duration, не усредняя индивидуальные скорости. [FR-010] [FR-011]
- [x] **T012** Покрыть модели, формулы, инварианты, нулевой объём и неодинаковые длительности unit-тестами. [FR-003] [FR-008] [FR-009] [FR-010] [FR-011] [ERR-005]

## Этап 3. HTTP measurement

- [x] **T013** Добавить одну минимальную прикладную ошибку измерения для передачи ожидаемой причины в CLI без traceback. [ERR-002] [ERR-003] [ERR-004] [ERR-005]
- [x] **T014** Реализовать 10 последовательных логических GET через один переданный `httpx.Client`, полный streaming final body через `iter_raw()` и прямую сумму chunk lengths. [FR-003] [FR-004] [FR-005] [FR-007]
- [x] **T015** Ограничить timing границами непосредственно перед request и после полного body через `time.perf_counter()`, отклоняя длительность `<= 0`. [FR-006] [ERR-005]
- [x] **T016** После полного чтения final body обрабатывать только конечные статусы 4xx/5xx как HTTP error. [ERR-002]
- [x] **T017** Добавить создание одного синхронного client с `follow_redirects=True`, `max_redirects=20` и явным `httpx.Timeout(30.0)`. [FR-014] [ERR-003] [NFR-002]
- [x] **T018** Проверить redirect chain, полное чтение промежуточных body, исключение их bytes, unsupported scheme, cycle и redirect limit. [FR-004] [FR-005] [FR-014] [ERR-004]
- [x] **T019** Покрыть measurement детерминированными `MockTransport`/`SyncByteStream` tests без реального интернета и `sleep`. [FR-005] [FR-006] [FR-007] [NFR-003]

## Этап 4. CLI

- [ ] **T020** Реализовать русскоязычный `argparse` с одним обязательным позиционным `URL`, `-h` и `--help`. [FR-001] [ERR-001] [NFR-004]
- [ ] **T021** Реализовать локальную HTTP/HTTPS URL validation, проверку hostname/port и удаление fragment до сетевого вызова. [FR-002] [ERR-001]
- [ ] **T022** Реализовать последовательное потребление 10 core-результатов через один context-managed client без request body и retries. [FR-003] [FR-004] [NFR-002]
- [ ] **T023** После каждой успешной полной попытки выводить в `stdout` progress `N/10`, duration и bytes. [FR-012] [NFR-004]
- [ ] **T024** После 10 попыток выводить русскоязычные итоги с округлением только при отображении до трёх знаков. [FR-013] [NFR-004]
- [ ] **T025** Реализовать entry point `main()` и exit codes 0/1/2 согласно результату запуска. [ERR-006]

## Этап 5. Error handling

- [ ] **T026** Выводить в `stderr` номер попытки и status code для HTTP 4xx/5xx после полного body. [ERR-002]
- [ ] **T027** Отдельно преобразовывать `httpx.TimeoutException` в русскоязычное timeout-сообщение без retry. [ERR-003] [NFR-004]
- [ ] **T028** Преобразовывать connection, DNS, TLS, protocol и redirect failures в краткое русскоязычное network error без traceback. [ERR-004] [NFR-004]
- [ ] **T029** Реализовать fail-fast: не печатать progress неуспешной попытки и итоги, не начинать следующие запросы, сохранять предыдущий progress. [ERR-002] [ERR-003] [ERR-004] [ERR-005]

## Этап 6. Tests

- [ ] **T030** Проверить CLI arguments/help, допустимые схемы без учёта регистра и отклонение invalid URL до HTTP-вызова. [FR-001] [FR-002] [ERR-001]
- [ ] **T031** Доказать тестами ровно 10 строго последовательных GET, один client lifecycle и полное чтение body до следующего обмена. [FR-003] [FR-004] [FR-005] [NFR-002]
- [ ] **T032** Проверить 10 progress lines, итоговые labels, значения и display-only rounding в `stdout`. [FR-008] [FR-009] [FR-010] [FR-011] [FR-012] [FR-013]
- [ ] **T033** Проверить fail-fast, сообщения, отсутствие traceback/final summary и exit codes для всех категорий ошибок. [ERR-002] [ERR-003] [ERR-004] [ERR-005] [ERR-006]
- [ ] **T034** Проверить, что весь automated test suite не использует реальную сеть, реальные задержки или nondeterministic clock. [NFR-003]

## Этап 7. README

- [ ] **T035** Написать русскоязычный README с требованиями Python 3.12+, установкой через `uv`, запуском `internet-speed-meter URL` и командами проверок. [FR-001] [NFR-001] [NFR-004]
- [ ] **T036** Описать единицы, aggregate throughput, redirects, timeout, ошибки и ограничение относительно ISP speed test. [FR-009] [FR-010] [FR-011] [FR-014] [ERR-002] [ERR-003] [ERR-004]

## Этап 8. CI

- [ ] **T037** Добавить минимальный GitHub Actions job для Python 3.12: `uv sync --locked --dev`, Ruff format/lint, mypy и pytest. [NFR-001] [NFR-003]

## Этап 9. Final verification

- [ ] **T038** Выполнить полный набор `uv run ruff format --check .`, `uv run ruff check .`, `uv run mypy src` и `uv run pytest`. [NFR-003]
- [ ] **T039** Повторно сопоставить все FR/ERR/NFR с реализацией и automated tests, устранив пробелы до завершения. [FR-001] [FR-002] [FR-003] [FR-004] [FR-005] [FR-006] [FR-007] [FR-008] [FR-009] [FR-010] [FR-011] [FR-012] [FR-013] [FR-014] [ERR-001] [ERR-002] [ERR-003] [ERR-004] [ERR-005] [ERR-006] [NFR-001] [NFR-002] [NFR-003] [NFR-004] [NFR-005]
- [ ] **T040** Провести финальное ревью русского пользовательского текста, английских identifiers, минимального scope и отсутствия запрещённых технологий/архитектурных слоёв. [NFR-004] [NFR-005]
