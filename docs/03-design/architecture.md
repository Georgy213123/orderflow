# Архитектура

Модель C4, два уровня. Контракт API — [openapi.yaml](openapi.yaml), данные — [er.md](er.md),
решения — [adr/](adr/).

## Контекст

```mermaid
flowchart TB
  client([Клиент<br/>присылает заявку, получает смету])
  staff([Менеджер, конструктор, руководитель<br/>работают в браузере])
  of[OrderFlow<br/>заявка → конструкция → смета]
  llm[/Языковая модель<br/>разбор текста, не подключена/]
  notify[/Сервис уведомлений<br/>почта или мессенджер, заглушка/]
  acc[/Учётная система<br/>вне демо, интерфейс/]

  client -- текст заявки --> staff
  staff -- HTTPS --> of
  of -. RequestParser .-> llm
  of -- ClientNotifier --> notify
  notify -.-> client
  of -. AccountingExporter .-> acc
```

Пунктир — точки расширения: интерфейс есть, в демо работает заглушка без сети.

## Контейнеры

```mermaid
flowchart LR
  user([Браузер])
  subgraph stand[Стенд: docker compose]
    web[frontend<br/>React 19 + TypeScript, Vite<br/>nginx в образе, порт 5301]
    api[backend<br/>FastAPI, Python 3.12<br/>порт 8301]
    db[(PostgreSQL 16<br/>порт 55301)]
  end
  user -- HTTP --> web
  web -- /api, JSON --> api
  api -- SQLAlchemy 2, psycopg 3 --> db
```

## Слои бэкенда

```
app/
├── api/routes.py        HTTP: схемы запроса и ответа, коды ошибок
├── services.py          сценарии: создать заявку, подтвердить поле, сменить статус,
│                        сохранить конструкцию, посчитать смету
├── domain/              чистая логика без БД и HTTP — покрыта unit-тестами
│   ├── parser.py        RequestParser, RuleBasedParser, LlmRequestParser (заглушка)
│   ├── fields.py        поля заявки, источник, правило подтверждения
│   ├── design.py        модель шкафа → спецификация, инварианты
│   ├── estimate.py      спецификация + цены → смета
│   ├── money.py         копейки и Decimal
│   └── status.py        машина состояний заявки
├── integrations/        адаптеры внешних систем: уведомления, учётная система
├── models.py            таблицы SQLAlchemy
└── main.py              сборка приложения, обработчики ошибок
```

Правило зависимостей: `domain` не импортирует ничего из `api`, `services`, `models`.
Поэтому расчёт сметы и разбор текста тестируются без базы за доли секунды,
а интеграционные тесты проверяют только склейку с PostgreSQL и HTTP.

## Поток «смета готова»

```mermaid
sequenceDiagram
  actor M as Менеджер
  participant W as frontend
  participant A as backend
  participant D as PostgreSQL
  M->>W: «Посчитать смету»
  W->>A: POST /api/requests/{id}/estimate
  A->>D: заявка, конструкция, справочник
  A->>A: check_transition(designed → estimated)
  A->>A: build_estimate(spec, prices)
  A->>D: estimates + estimate_lines, status_changes
  A-->>W: EstimateOut (копейки, количества строкой)
  W-->>M: таблица, итоги по видам, предупреждения
```

## Что сознательно не сделано

- Нет очереди и фоновых задач: расчёт сметы занимает миллисекунды.
- Нет авторизации и ролей в API: в демо один интерфейс. Перед боевым запуском —
  вход и права по ролям из 01-problem.md.
- Нет кэша справочника: справочник маленький, читается при каждом расчёте.
