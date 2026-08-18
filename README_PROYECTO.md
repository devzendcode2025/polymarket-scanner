# polymarket-scanner

Scanner de oportunidades en mercados de predicción basado en las APIs públicas de Polymarket.

El escáner procesa datos cada minuto y publica el dashboard en GitHub Pages como máximo cada seis minutos.

## Objetivo

Un solo pipeline de datos con dos salidas de dinero:

- **Opción 1 — Venta de datos/señales (activa ya):** detección de ballenas, mispricings, spreads y momentum; venta de alertas/suscripciones a traders de países habilitados (LatAm hispana: México, Colombia, Argentina, Chile, Perú, RD, etc.).
- **Opción 2 — Trading en Azuro (fase posterior):** usar el precio de Polymarket como referencia ("precio justo") y ejecutar en Azuro (DeFi, sin KYC, accesible desde Nicaragua) cuando se desvía.

## Restricción clave (verificada 2026-08-13)

Nicaragua está en la lista oficial de 39 países bloqueados de Polymarket (artículo "Geographic Restrictions" del help center). **NO se opera trading en Polymarket desde Nicaragua** — ni con VPN (prohibido, ToS 2.1.4) ni con cuenta bancaria USA (el bloqueo es por residencia; además "U.S. persons" también están prohibidos). Las APIs públicas de datos (solo lectura) SÍ son accesibles globalmente y son la base del proyecto.

## Stack

- Python 3 (solo stdlib: urllib, sqlite3, json) — cero dependencias externas.
- SQLite para almacenamiento local.
- APIs públicas de Polymarket: Gamma (descubrimiento), CLOB (precios/libro), Data (trades).

## Estructura

```
polymarket-scanner/
├── README_PROYECTO.md
├── MEMORIA_PROYECTO.md
├── CHAT_RESUMEN.md
├── TAREAS.md
├── REGLAS_PROYECTO.md
└── workspace/
    ├── scripts/        # pipeline (cliente APIs, db, scanner, runner)
    ├── data/           # SQLite local
    ├── reports/technical/  # reportes de detecciones (JSON + TXT)
    └── evidence/       # evidencia de verificaciones
```

## Estado

Fase 1 (pipeline de datos) en curso. Ver MEMORIA_PROYECTO.md (bloque Estado Actual) y TAREAS.md.
