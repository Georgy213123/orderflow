# OrderFlow — заявка → конструкция → смета

Платформа для вымышленной мастерской корпусной мебели «Кедр»: менеджер вставляет текст
заявки из письма, конструктор задаёт параметры шкафа, система строит спецификацию
деталей и считает смету по единому справочнику цен.

```
 текст заявки ──► разбор ──► поля «найдено в тексте» ──► подтверждение человеком
                                                                │
 смета ◄── справочник цен ◄── спецификация деталей ◄── параметры шкафа
   │
   └─► статус «смета готова» ──► отправка клиенту
```

Кейс показывает системный анализ (BPMN as-is и to-be, use case, FR/NFR, истории
с Given/When/Then), проектирование API с контрактом, точную арифметику денег и
тесты на трёх уровнях. Компания, люди, цены и числа боли вымышлены.

## Карта модулей продукта

| Модуль | Назначение | В демо |
|---|---|---|
| Приём заявки | форма и разбор свободного текста; у каждого поля источник, предположение разбора ждёт подтверждения | ✅ |
| Конструкция изделия | параметрическая модель шкафа → спецификация деталей с кромкой, проверка инвариантов | ✅ |
| Смета | площадь плиты, кромка, фурнитура, коэффициент запаса; неполный итог и цены разных дат | ✅ |
| Статусы заявки | новая → разобрана → конструкция готова → смета готова → отправлена клиенту, переход проверяет сервер | ✅ |
| Маршрут производства | задания по ролям и участкам цеха | ⬜ |
| Документы заказа | спецификация и бланк для цеха | ⬜ |
| Оптимизация раскроя | раскладка деталей по листам | ⬜ |
| Склад и снабжение | остатки плиты и фурнитуры, заказ поставщику | ⬜ |
| Обмен с учётной системой | выгрузка сметы и заказа; в демо только интерфейс `AccountingExporter` и заглушка | ⬜ |
| Личный кабинет клиента | статус заказа и смета для клиента | ⬜ |

Разбор текста работает правилами и регулярными выражениями. Языковая модель
подключается через тот же интерфейс `RequestParser` (ADR-0002), в демо — заглушка.

## Запуск

Docker:

```bash
make up          # postgres :55301, backend :8301, frontend :5301
```

Без Docker, с локальным PostgreSQL 16:

```bash
make install
export DATABASE_URL=postgresql+psycopg://postgres@localhost:55301/orderflow
make dev         # миграции, справочник, API и интерфейс
```

Интерфейс — http://localhost:5301, документация API — http://localhost:8301/docs.

## Проверки

```bash
make lint        # ruff, mypy strict, eslint, tsc, prettier
make test        # pytest unit + integration (TEST_DATABASE_URL), vitest
make e2e         # Playwright: десктоп 1440×900 и телефон 390×844
make audit       # pip-audit, npm audit
make openapi     # выгрузить контракт; тест сверяет файл с кодом
```

## Документация

| Раздел | Что внутри |
|---|---|
| [01-problem](docs/01-problem.md) | контекст, боль, роли, критерии успеха, границы |
| [02-analysis](docs/02-analysis/) | [BPMN as-is](docs/02-analysis/as-is.bpmn) и [to-be](docs/02-analysis/to-be.bpmn), [процессы](docs/02-analysis/processes.md), [use case](docs/02-analysis/use-cases.md), [FR/NFR](docs/02-analysis/requirements.md), [истории](docs/02-analysis/user-stories.md) |
| [03-design](docs/03-design/) | [C4](docs/03-design/architecture.md), [ER](docs/03-design/er.md), [openapi.yaml](docs/03-design/openapi.yaml), [ADR](docs/03-design/adr/) |
| [04-ai-development](docs/04-ai-development.md) | декомпозиция на задачи для агентов, конвейер, разбор задачи «смета» |
| [05-testing](docs/05-testing.md) | пирамида, трассировка US → тест, отчёт прогона |
| [06-bugs](docs/06-bugs.md) | пять багов с регрессионными тестами |
| [07-releases](docs/07-releases.md) | путь v0.1 → v1.0, [CHANGELOG](docs/CHANGELOG.md) |

## Стек

Python 3.12, FastAPI, SQLAlchemy 2, Alembic, PostgreSQL 16, pydantic v2, uv ·
React 19, TypeScript, Vite · pytest, Vitest, Testing Library, Playwright ·
ruff, mypy, ESLint, Prettier · Docker Compose.

## Структура

```
backend/    FastAPI: app/domain — чистая логика, app/services.py — сценарии, alembic — миграции
frontend/   React: заявка, конструкция, смета на одном экране
e2e/        Playwright
docs/       01…07 по канону витрины
```
