# Модель данных

Схема создаётся миграцией `backend/alembic/versions/0001_initial_schema.py`.

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
    varchar parser "rules|llm"
    timestamptz created_at
    timestamptz updated_at
  }
  request_fields {
    int id PK
    int request_id FK
    varchar key "product_type, width_mm, ..."
    varchar value
    varchar source "text|human"
    bool confirmed
    varchar fragment "фрагмент исходного текста"
  }
  status_changes {
    int id PK
    int request_id FK
    varchar from_status
    varchar to_status
    timestamptz changed_at
  }
  designs {
    int id PK
    int request_id FK "unique"
    jsonb params
  }
  design_parts {
    int id PK
    int design_id FK
    int position
    varchar code "side|top_bottom|shelf|back|door"
    int length_mm
    int width_mm
    int qty
    varchar material_code FK
    int edge_long "0-2"
    int edge_short "0-2"
  }
  design_hardware {
    int id PK
    int design_id FK
    varchar material_code FK
    int qty
  }
  materials {
    varchar code PK
    varchar name
    varchar kind "board|back|edge|hardware"
    varchar unit "m2|m|pcs"
    int thickness_mm
    bigint price_kop "null = нет цены"
    date price_date
    numeric waste_factor ">= 1"
  }
  estimates {
    int id PK
    int request_id FK "unique"
    bigint total_kop
    bool complete
    jsonb totals_by_kind
    jsonb warnings
  }
  estimate_lines {
    int id PK
    int estimate_id FK
    varchar kind
    varchar material_code
    numeric net_quantity "14,6"
    numeric waste_factor "5,3"
    numeric quantity "12,2"
    bigint price_kop
    date price_date
    bigint amount_kop
  }
```

## Словарь данных

| Таблица | Поле | Смысл |
|---|---|---|
| requests | status | статус заявки, ограничен `CHECK`; переход меняет только сервер |
| requests | parser | каким разборщиком разобран текст: `rules` или `llm` |
| request_fields | source | `text` — найдено в тексте, `human` — ввёл человек |
| request_fields | confirmed | человек подтвердил значение; без этого поле не считается заполненным |
| request_fields | fragment | кусок исходного текста, из которого взято значение; у ручного ввода пусто |
| status_changes | — | журнал переходов, по нему строится история заявки |
| designs | params | параметры шкафа целиком (габариты, толщина, полки, двери, материалы) |
| design_parts | edge_long / edge_short | сколько длинных и коротких сторон детали оклеено кромкой |
| materials | price_kop | цена за единицу в копейках; `null` — цены нет, итог сметы будет неполным |
| materials | price_date | дата цены; разные даты в одной смете дают предупреждение |
| materials | waste_factor | коэффициент запаса на обрезки и брак |
| estimate_lines | net_quantity | количество без запаса, точно (м², м, шт.) |
| estimate_lines | quantity | количество в смету: нетто × запас, округлено один раз |
| estimate_lines | amount_kop | сумма строки в копейках; `null`, если нет цены |
| estimates | total_kop | сумма известных строк; при `complete = false` это нижняя граница |

Смета хранится снимком: цены и количества копируются в `estimate_lines`. Если справочник
потом изменится, отправленная клиенту смета останется прежней.
