# Архитектура

C4, два уровня. Контракт — [openapi.yaml](openapi.yaml), данные — [er.md](er.md),
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

Предметная логика (разбор, конструкция, смета, статусы) не зависит от базы и HTTP,
поэтому покрыта быстрыми unit-тестами. Авторизации и ролей в API нет.
