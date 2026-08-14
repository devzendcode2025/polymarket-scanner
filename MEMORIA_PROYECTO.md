# MEMORIA_PROYECTO — polymarket-scanner

## Estado Actual (vivo)

- **Estado:** Sistema automático COMPLETO + v0.7.0 — 2026-08-14 00:50: cron scan cada 1 min, poda de disco activa, sitio público auto-actualizado (https://devzendcode2025.github.io/polymarket-scanner/) con VERSIÓN MOBILE, TODO EN ESPAÑOL (traducción DeepSeek con caché), FILTRO POR PAÍS (27 LatAm), CATEGORÍAS (8) + selector, 25 ÍTEMS por sección, LINKS a Polymarket, ANALISTA HEURÍSTICO (prob/confianza/horizonte/razón) y F3 EDGE "DATOS GANADORES" (cross-check Kalshi/Manifold/PredictIt con caché 10 min; Metaculus descartada por exigir cuenta; matching por tokens raros compartidos + misma categoría — precisión alta, recall bajo, depuración pendiente). Backup diario 03:00 UTC (job e6232106fb87). BD ~2.5 MB.
- **Decisiones firmes:** NO trading en Polymarket desde Nicaragua (bloqueado); solo APIs públicas read-only; cobros en USDC; TODO en español; stdlib Python sin dependencias; Firebase/cPanel/dominio = fase futura; edges con precisión > cantidad (nada de falsos positivos en el panel público); DeepSeek para traducción (activo) y narración (F4).
- **Riesgos:** (1) APIs públicas pueden cambiar/limitarse sin aviso; (2) el cuello de botella comercial es la audiencia, no el código; (3) liquidez de Azuro aún no verificada (Fase 4); (4) probabilidades del analista = heurística, no garantía (transparencia en el pie del dashboard).
- **Pendientes clave:** (1) depurar matching de edges (LLM/embeddings para cruzar el MISMO evento); (2) F4 narración DeepSeek de justificaciones; (3) F5 piloto Perú; (4) afinar mispricings (menor volumen); (5) on-ramps USDC Nicaragua; (6) validar Azuro; (7) canal X/Telegram.
- **Última actualización:** 2026-08-14

---

## Registro de decisiones

### 2026-08-13 — Creación del proyecto
- **Contexto:** el usuario pidió una ruta para ganar dinero con Polymarket. Verificación en vivo (artículo oficial "Geographic Restrictions", help.polymarket.com/en/articles/13364163) confirmó que **Nicaragua está en la lista de 39 países bloqueados** (junto con EE.UU., Brasil, Venezuela, Cuba, etc.).
- **Decisión:** descartar trading en Polymarket. Adoptar doble vía: (1) monetizar datos (señales/suscripciones) — viable ya; (2) trading en Azuro (DeFi sin KYC) — fase posterior.
- **Verificado en vivo:** APIs Gamma/CLOB/Data responden HTTP 200 sin autenticación desde cualquier lugar. Límites generosos (Gamma 4000 req/10s, CLOB 9000, Data 1000).
- **Nota infraestructura:** el navegador de esta sesión no carga polymarket.com (DNS solo IPv6, navegador se cuelga); curl/python por IPv4 funcionan. Para verificación web de estas APIs usar red por IPv4.

## Inventario técnico

- `workspace/scripts/polymarket_client.py` — cliente de las 3 APIs públicas (urllib, retries, backoff).
- `workspace/scripts/db.py` — SQLite: tablas markets, price_snapshots, trades, scans.
- `workspace/scripts/scanner.py` — detecciones: mispricings (Yes+No≠1), ballenas (trades ≥ umbral $), momentum (cambio % en ventana), spreads.
- `workspace/scripts/run_scan.py` — orquestador: recoge → guarda → detecta → reporta (JSON + TXT en reports/technical/).

## Conocimiento de mercado (verificado)

- Mercados de predicción: precios = probabilidades (0.65 = 65%). Yes+No debe sumar 1.
- LatAm habilitada para trading en Polymarket (23 países): México, Colombia, Argentina, Chile, Perú, RD, Panamá, Costa Rica, Guatemala, Honduras, El Salvador, Ecuador, Bolivia, Paraguay, Uruguay, Belice, Bahamas, Barbados, Jamaica, Trinidad y Tobago, Haití, Guyana, Surinam. (Puerto Rico es dudoso: "U.S. persons" prohibidos.)
- LatAm bloqueada (4): Brasil, Cuba, Nicaragua, Venezuela.
- On-ramp/exchange (conocimiento estable, no re-verificado en vivo): Binance/Bybit/OKX/MEXC/KuCoin aceptan Nicaragua; Coinbase no. Retiro USDC→Polygon ≈ 1 USDC (Binance). Compra con tarjeta ≈ 1.8%. P2P NIO pendiente de confirmar.
- Cobro: Stripe/PayPal no operan para receptor en Nicaragua → suscripciones en USDC (el público de prediction markets ya vive en USDC).
