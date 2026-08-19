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
- [x] Limitar publicación de GitHub Pages a una vez cada 6 minutos; el scan continúa cada minuto (2026-08-18)
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
- [x] CROSS-CHECK DE PROBABILIDADES (F3): Kalshi + Manifold + PredictIt (Metaculus exige cuenta) → EDGE "datos ganadores", caché 10 min, matching por tokens raros + categoría (v0.7.0)
- [x] DEPURACIÓN DEL MATCHING DE EDGES (F3, v0.8.0): candidatos laxos (nombres propios ≥5 chars o ≥2 tokens con raro) + CONFIRMACIÓN DeepSeek en batch "mismo evento SI/NO" (cache SQLite edge_confirm, 60 pares/corrida, precisión absoluta: sin confirmación no hay edge). Se eliminó el fallback v1 (falsos positivos). MAX_POLY 50→200.
- [x] RECALL BOOST DE EDGES (F3, v0.8.1, 2026-08-18): fuente ESPN (19 ligas, moneyline→"Winner: A vs B" sin vig), Kalshi arreglado (esquema dollars/title + filtro parlays + paginación cursor), Manifold 500, bigramas de NP, top-2 candidatos por fuente, MAX_POLY 400, MAX_CANDIDATOS 150, prompt exige mismo tipo de mercado, filtro determinista Winner: vs draw/O-U/spread, dedupe game_id en consenso. Test: 194→261 candidatos; falsos positivos eliminados; pipeline completo validado (scan real 2 edges).
- [x] RECALL v2 DE EDGES (F3, v0.8.2, 2026-08-19): TOP_K 2→4, MAX_CANDIDATOS 150→300, MAX_POLY 400→600, +14 ligas fútbol ESPN (verificadas en vivo, 9 con moneyline hoy), token raro ≤5→≤8 → candidatos 261→613 (2.3x).
- [x] MISPRICINGS DEL LIBRO REAL (v0.8.2, 2026-08-19): hallazgo — Gamma normaliza precios (spread exacto 0 en 800 mercados), el detector por precios nunca podía ver desvíos. Nuevo: barrido del orderbook CLOB de ambos tokens (caché SQLite orderbooks TTL 10 min, lotes 30/corrida keep-alive 181ms/libro), desvío del mid + arbitraje directo (asks<1 comprar, bids>1 vender), umbral vol $10k→$5k, cola 200→600, analista degrada a baja si libro ilíquido (liq<$10k y vol<$20k).
- [x] ANALISTA DEEPSEEK NARRANDO (F4, v0.8.0): narrativa.py — top-5 señales con justificación narrada en español (2-3 frases, números reales, nota de riesgo), caché SQLite por clave (0 llamadas si la señal no cambió), mostrada en las tarjetas del dashboard
- [x] HISTÓRICO DE ACIERTOS (v0.8.0): historico_aciertos.py cruza mercados resueltos con trades ≥$1k → % de aciertos de ballenas (stat dorada en dashboard; hoy 0/0, acumula datos)
- [x] PODA DE TRADES (v0.8.0): TTL 7 días (la BD crecía ~13 MB/día)
- [x] MISPRICINGS: barrido ampliado al puesto 400 por volumen (offset 200-400, solo escaneo) (v0.8.0)
- [ ] PILOTO POR PAÍS (F5): VERIFICADO en vivo 2026-08-15 — 0 mercados peruanos en top-400 de Gamma (filtro por país OK por tags+keywords; el mercado "sobre Perú" no existe aún; keywords de Perú ampliadas). Re-evaluar cuando haya mercados peruanos (elecciones Perú 2026)
- [ ] Canal Telegram público (detecciones gratis) — REQUIERE usuario (BotFather)
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
