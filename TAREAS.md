# TAREAS — polymarket-scanner

## Fase 0 — Validación de acceso (hecha en su mayoría)
- [x] Verificar si Nicaragua puede operar en Polymarket → NO (lista oficial de 39 países bloqueados)
- [x] Verificar acceso global a APIs públicas de datos → SÍ (HTTP 200 sin auth)
- [x] Informe LatAm: 23 habilitados / 4 bloqueados
- [ ] Verificar on-ramps USDC desde Nicaragua (MoonPay/Transak/Binance P2P NIO) — manual o navegador
- [ ] Validar Azuro a fondo: mercados, liquidez real, fondeo, fees, gas

## Fase 1 — Pipeline de datos (en curso)
- [x] Runner canónico de verificación (verificacion/run-all.sh + VERIFICACION.md) — verde desde v0.1.1
- [x] Scaffolding del proyecto + archivos de control
- [x] Cliente de APIs (Gamma / CLOB / Data) con retries
- [x] Base SQLite (markets, price_snapshots, trades, scans)
- [x] Motor de detección: mispricings, ballenas, momentum, spreads
- [x] Primer scan real ejecutado y validado (2026-08-13 20:40: 200 mercados, 5 ballenas; mispricings 0 en top-200)
- [x] Cron cada 1 minuto (job polymarket-scan-1min, script puro sin LLM, silencioso)
- [x] Poda de disco: snapshots solo con cambio ≥0.5%, TTL 30 días, reportes últimos 20 (~1-3 MB/día)
- [x] Backup diario comprimido a repo privado polymarket-scanner-data (job polymarket-backup-diario, 03:00 UTC)
- [x] LINKS DIRECTOS a Polymarket en cada señal/mercado del dashboard (F1, v0.5.0)
- [x] FILTRO POR PAÍS LatAm en el dashboard: 23 ✅ ejecutables / 4 🔒 solo datos (F1, v0.5.0)
- [x] ANALISTA HEURÍSTICO: prob 0-100 + confianza + horizonte + justificación por señal, sin LLM (F2, v0.5.0)
- [x] VERSIÓN MOBILE del dashboard: tablas→tarjetas apiladas, stats 2 col, selector full-width (v0.6.0)
- [x] TODO EN ESPAÑOL: traducción automática de títulos con DeepSeek (translate.py + caché SQLite, máx 30 nuevos/corrida; fallback silencioso) (v0.6.0)
- [x] CATEGORÍAS por señal/mercado (categorias.py: Política/Deportes/Cripto/Economía/Tecnología/Ciencia/Entretenimiento/Otros) + selector + badge (v0.7.0)
- [x] MÁS DE 10 ÍTEMS: ballenas 25, momentum 30, top 25, slices del dashboard 25 (v0.7.0)
- [x] CROSS-CHECK DE PROBABILIDADES (F3): Kalshi + Manifold + PredictIt (Metaculus exige cuenta) → EDGE "datos ganadores", caché 10 min, matching por tokens raros + categoría (v0.7.0)
- [ ] Afinar mispricings: barrer mercados de menor volumen / bajar umbral (los top-200 líquidos son eficientes)

## Fase 2 — Backtest de estrategias
- [ ] Recolectar historial (prices-history) de mercados de cripto 24h y deportes
- [ ] Estrategia A: momentum en mercados cripto
- [ ] Estrategia B: contrarian en sobrerreacción
- [ ] Estrategia C: arbitraje cruzado Polymarket vs Azuro
- [ ] Criterio: 200+ trades simulados, win rate + riesgo/recompensa

## Fase 3 — Audiencia y venta de datos (Opción 1)
- [x] SITIO PÚBLICO EN LÍNEA: https://devzendcode2025.github.io/polymarket-scanner/ (GitHub Pages, repo público polymarket-scanner)
- [x] DASHBOARD DINÁMICO (v0.4.0): app JS consulta las APIs de Polymarket EN VIVO desde el navegador (ballenas vía Data API, top mercados vía Gamma — CORS verificado) + data.json del pipeline (mispricings/momentum) + auto-refresh 60s + hora Nicaragua
- [x] Generador: render_dashboard.py → docs/data.json (detecciones del último scan); docs/index.html = app fija con JS
- [x] Sitio se auto-actualiza: cron 1/min → render → push condicional (detecciones o ≥6 min; límite Pages ~10 builds/h)
- [x] CROSS-CHECK DE PROBABILIDADES (F3): Kalshi/Manifold/PredictIt (Metaculus exige cuenta) → EDGE "datos ganadores"; matching por tokens raros + categoría; DEPURACIÓN del matching pendiente (LLM/embeddings para mismo evento) — ver Fase 1
- [ ] ANALISTA DEEPSEEK (F4): justificaciones narradas en español con el edge real (clave de Hermes ya autorizada; top-5 señales, cron 30-60 min)
- [ ] PILOTO POR PAÍS (F5): verificación en vivo con Perú + ajustes
- [ ] Firebase Firestore + dominio propio + cPanel: FASE FUTURA (usuario decidió dejarlo para adelante; el HTML estático migra sin cambios)
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
