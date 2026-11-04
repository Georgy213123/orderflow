# 05. Тестирование

## Пирамида

```
            e2e Playwright          4 сценария × десктоп и телефон
          ─────────────────
        integration pytest          HTTP + PostgreSQL, сквозной путь заявки
      ───────────────────────
    unit pytest + Vitest            разбор, поля, конструкция, смета, деньги, статусы, UI
  ───────────────────────────────
```

Предметные правила — чистые функции, поэтому основной вес на unit.

| Слой | Что проверяет |
|---|---|
| unit, бэкенд | единицы в тексте, подтверждение поля, инварианты, округление сметы, копейки, переходы, сверка `openapi.yaml` |
| integration | HTTP и PostgreSQL, 404/409/422, история, откат миграций, параллельные запросы к заявке |
| unit, фронт | переключение заявок, запоздавшие ответы, форматирование копеек |
| e2e | текст → подтверждение → конструкция → итог 12 331,96 ₽; неполная смета; форма на 390 px |

## История → тест

| История | unit | integration | e2e |
|---|---|---|---|
| US-01 | `test_parser.py` | `test_us01_*` | «менеджер вставляет текст…» |
| US-02 | `test_fields.py`, `FieldRow.test.tsx` | `test_us02_*` | «полный путь…» |
| US-03 | `test_design.py` | `test_us03_*`, `test_redesign_drops_estimate` | «полный путь…» |
| US-04 | `test_estimate.py`, `test_money.py` | `test_us03_us04_us05_full_flow` | «полный путь…», «смета без цены…» |
| US-05 | `test_status.py`, `StatusSteps.test.tsx` | `test_us05_*` | статус на каждом шаге |
| US-06 | `test_integrations.py` | `test_us04_incomplete_*` | «смета без цены…» |
| R-01…R-10 | `test_review_fixes.py`, `App.test.tsx` | `test_review_fixes.py` | — |

## Прогон 2026-11-04, v0.3.2

macOS, PostgreSQL 16, Chromium из Playwright 1.64.

| Команда | Результат |
|---|---|
| `make lint` | ruff, mypy strict, eslint, tsc, prettier — без замечаний |
| `make test` | pytest 82 passed за 4,79 с (67 unit, 15 integration), покрытие `app/` 97 %; Vitest 18 passed |
| `make e2e` | 7 passed, 1 skipped за 11,1 с: мобильный сценарий на десктопе пропускается намеренно |
| `make audit` (03.11) | pip-audit чисто; npm: 12 moderate в инструментах ESLint |

Не проверено: `make up`, на машине сборки нет Docker.
