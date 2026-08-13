# TAREAS — polymarket-scanner

## Fase 0 — Validación de acceso (hecha en su mayoría)
- [x] Verificar si Nicaragua puede operar en Polymarket → NO (lista oficial de 39 países bloqueados)
- [x] Verificar acceso global a APIs públicas de datos → SÍ (HTTP 200 sin auth)
- [x] Informe LatAm: 23 habilitados / 4 bloqueados
- [ ] Verificar on-ramps USDC desde Nicaragua (MoonPay/Transak/Binance P2P NIO) — manual o navegador
- [ ] Validar Azuro a fondo: mercados, liquidez real, fondeo, fees, gas

## Fase 1 — Pipeline de datos (en curso)
- [x] Scaffolding del proyecto + archivos de control
- [x] Cliente de APIs (Gamma / CLOB / Data) con retries
- [x] Base SQLite (markets, price_snapshots, trades, scans)
- [x] Motor de detección: mispricings, ballenas, momentum, spreads
- [x] Primer scan real ejecutado y validado (2026-08-13 20:40: 200 mercados, 5 ballenas; mispricings 0 en top-200)
- [ ] Afinar mispricings: barrer mercados de menor volumen / bajar umbral (los top-200 líquidos son eficientes)
- [ ] Programar scans periódicos (cron) + historial acumulado
- [ ] Resumen diario del scan (para WhatsApp vía gateway, si el usuario lo pide)

## Fase 2 — Backtest de estrategias
- [ ] Recolectar historial (prices-history) de mercados de cripto 24h y deportes
- [ ] Estrategia A: momentum en mercados cripto
- [ ] Estrategia B: contrarian en sobrerreacción
- [ ] Estrategia C: arbitraje cruzado Polymarket vs Azuro
- [ ] Criterio: 200+ trades simulados, win rate + riesgo/recompensa

## Fase 3 — Audiencia y venta de datos (Opción 1)
- [x] Mockup visual del dashboard (workspace/web/dashboard.html) — con datos reales del scan; pendiente aprobación del diseño
- [ ] Decidir arquitectura/hosting del sitio (estático generado vs backend)
- [ ] Generador del dashboard desde los reportes JSON + publicación automática
- [ ] Canal X/Twitter en español con detecciones gratis (4 semanas de contenido)
- [ ] Canal Telegram público (detecciones gratis)
- [ ] Canal Telegram pago: alertas ballenas $10/mes, scanner $20/mes, combo $25/mes (pago en USDC)
- [ ] Boletín semanal (Substack) — mes 2-3
- [ ] Venta B2B del feed (mes 3+): $50-200/mes por cliente

## Fase 4 — Trading en Azuro (Opción 2, requiere Fase 0 completada)
- [ ] Fonder MetaMask con USDC (vía exchange → Polygon)
- [ ] Paper trading 50+ señales
- [ ] Capital real: $50-100, máx 5-10% por trade, stop-loss, 3 trades máx simultáneos
- [ ] Escalar solo tras 4 semanas consecutivas positivas

## Reglas permanentes (ver REGLAS_PROYECTO.md)
- No operar trading en Polymarket; solo datos read-only.
- Cobros en USDC. Archivos de control al día tras cada trabajo.
