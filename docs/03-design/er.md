# Модель данных

Схема — миграция в `backend/alembic/versions/`, на диаграмме главные поля.

```mermaid
erDiagram
  requests ||--o{ request_fields : "поля"
  requests ||--o{ status_changes : "история"
  requests ||--o| designs : "конструкция"
  requests ||--o| estimates : "смета"
  designs ||--|{ design_parts : "детали"
  designs ||--o{ design_hardware : "фурнитура"
  estimates ||--|{ estimate_lines : "строки"
  materials ||--o{ design_parts : "материал"
  materials ||--o{ design_hardware : "позиция"

  requests {
    int id PK
    text raw_text
    varchar status "new|parsed|designed|estimated|sent"
  }
  request_fields {
    varchar key
    varchar value
    varchar source "text|human"
    bool confirmed
    varchar fragment
  }
  designs {
    jsonb params
  }
  design_parts {
    varchar code "side|top_bottom|shelf|back|door"
    int length_mm
    int width_mm
    int qty
  }
  materials {
    varchar code PK
    varchar kind "board|back|edge|hardware"
    bigint price_kop "null = нет цены"
    date price_date
    numeric waste_factor
  }
  estimates {
    bigint total_kop
    bool complete
  }
  estimate_lines {
    numeric net_quantity
    numeric quantity
    bigint price_kop
    bigint amount_kop
  }
```

## Словарь

| Сущность | Смысл |
|---|---|
| requests | заявка; `status` ограничен `CHECK`, меняет его только сервер |
| request_fields | `source` — откуда значение, `confirmed` — подтвердил ли человек, `fragment` — кусок текста |
| status_changes | журнал переходов, по нему строится история |
| designs, design_parts | параметры шкафа и детали в целых мм |
| materials | справочник: цена в копейках (`null` — цены нет), дата цены, коэффициент запаса |
| estimates, estimate_lines | смета-снимок: количества и цены копируются в строки. `total_kop` при `complete = false` — нижняя граница |
