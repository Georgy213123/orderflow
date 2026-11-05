# OrderFlow — заявка → конструкция → смета

[![CI](https://github.com/Georgy213123/orderflow/actions/workflows/ci.yml/badge.svg)](https://github.com/Georgy213123/orderflow/actions/workflows/ci.yml)
[![CodeQL](https://github.com/Georgy213123/orderflow/actions/workflows/codeql.yml/badge.svg)](https://github.com/Georgy213123/orderflow/actions/workflows/codeql.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

В мебельной мастерской заявка приходит текстом: «шкаф 120 на 210, глубина 60, две двери».
Её переписывают в таблицу, детали считают на бумаге, смету — по своей копии прайса.
Ответ уходит через несколько дней. OrderFlow разбирает текст в поля с пометкой
источника, строит из параметров шкафа спецификацию деталей и считает смету по одному
справочнику цен. Мастерская «Кедр», люди и цены вымышлены.

<img src="docs/img/intake-sources-desktop.png" alt="Заявка из текста: у полей источник «найдено в тексте»">

<p>
<img src="docs/img/estimate-desktop.png" alt="Спецификация и смета, итог 12 331,96 ₽" width="560">
<img src="docs/img/intake-mobile.png" alt="Форма заявки на телефоне" width="260">
</p>

## Карта модулей

| Модуль | Что делает | В демо |
|---|---|---|
| Приём заявки | разбор текста, у поля источник, предположение ждёт подтверждения | ✅ |
| Конструкция | параметры шкафа → детали с кромкой, проверка правил конструкции (полка не шире проёма, не больше 10 полок и 4 дверей) | ✅ |
| Смета | плита, задняя стенка (ХДФ), кромка, фурнитура, запас; неполный итог, цены разных дат | ✅ |
| Статусы | от «новая» до «отправлена», переход проверяет сервер | ✅ |
| Справочник материалов с историей цен | | ⬜ |
| Вход и роли | | ⬜ |
| Документы для цеха | | ⬜ |
| Обмен с учётной системой | только интерфейс `AccountingExporter` и заглушка | ⬜ |

## Решения и компромиссы

- **Разбор правилами, модель за интерфейсом.** Правила работают без сети. Модель
  подключается через тот же `RequestParser`, и её ответ тоже приходит неподтверждённым ([ADR-0002](docs/03-design/adr/0002-external-services-behind-adapters.md)).
- **Человек подтверждает каждое найденное поле.** Лишний клик, зато ошибка разбора не
  доходит до сметы.
- **Деньги в целых копейках, количества в `Decimal`.** Во float теряется копейка на суммах,
  поэтому итоги в целых копейках. Следующий шаг — тест на сходимость с эталонной сметой.
  Итоги считает только сервер ([ADR-0003](docs/03-design/adr/0003-money-in-kopecks.md)).
- **Статус меняется как следствие действия.** `PATCH status` отверг: таблица переходов
  на сервере, пропуск шага — 409 ([ADR-0004](docs/03-design/adr/0004-server-side-state-machine.md)).
- **Блокировка строки заявки** (`SELECT … FOR UPDATE`) появилась после ревью. Очередь не
  завёл: смета считается за миллисекунды. Чтобы тяжёлый запрос не положил расчёт, у входа
  есть лимиты. Размеры, текст и значения полей ограничены в [`schemas.py`](backend/app/schemas.py).
  Число полок и дверей — не больше 10 и 4, как в правилах конструкции. Иначе 422 (BUG-12).

## Что не сделано и почему

- Адаптер языковой модели — заглушка с TODO: сначала замер доли найденных полей на реальных заявках.
- Нет входа и ролей, это первый шаг v0.4.
- Отправка сметы: статус `sent` ставится только после успешной отправки, повтор идёт с ключом,
  который не даёт отправить письмо дважды (BUG-13). Очередь отправки в базе с фоновым отправщиком (outbox) — следующий шаг:
  пока отправка идёт внутри запроса под блокировкой строки заявки.
- Экрана справочника цен нет, цены в начальных данных. Отправка сметы пишет в журнал.
- Модель конструкции одна — шкаф. Типы ответов API на фронте описаны руками, клиент по
  `openapi.yaml` не генерируется.

## Запуск

```bash
make up                  # Docker: postgres :55301, backend :8301, frontend :5301

make install             # без Docker, нужен PostgreSQL 16
export DATABASE_URL=postgresql+psycopg://postgres@localhost:55301/orderflow
make dev                 # миграции, справочник, API и интерфейс

make lint test e2e       # ruff, mypy strict, eslint, tsc; pytest и Vitest; Playwright
```

Интерфейс — http://localhost:5301, API — http://localhost:8301/docs.
`make test` ждёт базу `orderflow_test` (`TEST_DATABASE_URL`).

## Как это сделано

Код и тесты писал Claude Code по моим брифам, аналитику и приёмку делал я. Codex ревьюил
в два круга: 10 находок, потом ещё 3, воспроизвелись все. Каждую я сначала подтверждал
падающим тестом. Тесты агента проверяли один запрос за раз и пропустили гонки. Подробно —
[04-ai-development](docs/04-ai-development.md).

## Документация

[01-problem](docs/01-problem.md) · [02-analysis](docs/02-analysis/): BPMN [as-is](docs/02-analysis/as-is.bpmn) и [to-be](docs/02-analysis/to-be.bpmn), [процессы](docs/02-analysis/processes.md), [use case](docs/02-analysis/use-cases.md), [FR/NFR](docs/02-analysis/requirements.md), [истории](docs/02-analysis/user-stories.md) ·
[03-design](docs/03-design/): [C4](docs/03-design/architecture.md), [ER](docs/03-design/er.md), [openapi.yaml](docs/03-design/openapi.yaml), [ADR](docs/03-design/adr/) ·
[04-ai-development](docs/04-ai-development.md) · [05-testing](docs/05-testing.md) · [06-bugs](docs/06-bugs.md) · [07-releases](docs/07-releases.md) · [CHANGELOG](docs/CHANGELOG.md)

Стек: Python 3.12, FastAPI, SQLAlchemy 2, Alembic, PostgreSQL 16 · React 19, TypeScript,
Vite · pytest, Vitest, Playwright · Docker Compose.

---

Один из трёх проектов портфолио [ai-product-engineering](https://github.com/Georgy213123/ai-product-engineering):
там же процесс работы с агентами и два других проекта.
