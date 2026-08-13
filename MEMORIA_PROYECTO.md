# MEMORIA_PROYECTO — polymarket-scanner

## Estado Actual (vivo)

- **Estado:** Sistema automático COMPLETO — 2026-08-13 22:00: cron scan cada 1 min (job 7a818b7cc17a, script puro), poda de disco activa (snapshots ≥0.5% cambio, TTL 30d, reportes últimos 20), sitio público auto-actualizado (https://devzendcode2025.github.io/polymarket-scanner/), backup diario 03:00 UTC a repo privado polymarket-scanner-data (job e6232106fb87). BD ~0.27 MB.
- **Decisiones firmes:** NO trading en Polymarket desde Nicaragua (bloqueado); solo APIs públicas read-only; cobros en USDC; español primero, inglés después; stdlib Python sin dependencias; Firebase/cPanel/dominio = fase futura.
- **Riesgos:** (1) APIs públicas pueden cambiar/limitarse sin aviso; (2) el cuello de botella comercial es la audiencia, no el código; (3) liquidez de Azuro aún no verificada (Fase 4).
- **Pendientes clave:** (1) confirmar corridas automáticas del cron (primeras 24h); (2) afinar mispricings (barrer menor volumen); (3) on-ramps USDC Nicaragua; (4) validar Azuro; (5) canal público X/Telegram; (6) Firebase/cPanel/dominio (fase futura).
- **Última actualización:** 2026-08-13

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
