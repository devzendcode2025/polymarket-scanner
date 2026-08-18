# MEMORIA_PROYECTO — polymarket-scanner

## Estado Actual (vivo)

- **Estado:** Sistema automático COMPLETO + v0.8.0 — 2026-08-15: cron scan cada 1 min, poda de disco activa (snapshots 30d + trades 7d), sitio público auto-actualizado (https://devzendcode2025.github.io/polymarket-scanner/) con VERSIÓN MOBILE, TODO EN ESPAÑOL (traducción DeepSeek con caché), FILTRO POR PAÍS (27 LatAm), CATEGORÍAS (8) + selector, 25 ÍTEMS por sección, LINKS a Polymarket, ANALISTA HEURÍSTICO (prob/confianza/horizonte/razón), F4 NARRATIVA DeepSeek (top-5 señales, caché SQLite por clave, 0 llamadas si la señal no cambió), F3 EDGE "DATOS GANADORES" v2 (candidatos por nombres propios + CONFIRMACIÓN DeepSeek "mismo evento SI/NO" con caché SQLite; sin confirmación no hay edge — precisión absoluta), barrido de mispricings hasta el puesto 400 por volumen, HISTÓRICO DE ACIERTOS (mercados resueltos × ballenas ≥$1k → % de aciertos, stat dorada; arrancó 0/0 acumulando), F5 Perú verificado en vivo (0 mercados peruanos en top-400; filtro OK, keywords ampliadas). Backup diario 03:00 UTC (job e6232106fb87). BD ~15.5 MB (acotada con poda de trades 7d). 🐛 Fix crítico 2026-08-15: lock huérfano de cron_scan.sh (mkdir) congeló el sistema ~24h (14 16:04 → 15 16:13); ahora flock del kernel.
- **Decisiones firmes:** NO trading en Polymarket desde Nicaragua (bloqueado); solo APIs públicas read-only; cobros en USDC; TODO en español; stdlib Python sin dependencias; Firebase/cPanel/dominio = fase futura; edges con precisión > cantidad (nada de falsos positivos en el panel público — se eliminó el fallback heurístico de crosscheck); DeepSeek para traducción, narrativa y confirmación de edges.
- **Riesgos:** (1) APIs públicas pueden cambiar/limitarse sin aviso; (2) el cuello de botella comercial es la audiencia, no el código; (3) liquidez de Azuro aún no verificada (Fase 4); (4) probabilidades del analista = heurística, no garantía (transparencia en el pie del dashboard); (5) la confirmación de edges depende de DeepSeek: si la API falla, ese día salen 0 edges (honesto, no degrada precisión).
- **Pendientes clave:** (1) canal Telegram gratis+pago (REQUIERE usuario: BotFather, decisión de canales); (2) backtest Fase 2 (momentum/contrarian con historial acumulado); (3) histórico de aciertos necesita días para mostrar el primer %; (4) on-ramps USDC Nicaragua (verificación manual); (5) validar Azuro; (6) F5 real cuando Polymarket tenga mercados peruanos.
- **Última actualización:** 2026-08-18 — corregido el control de publicación: scan cada 1 min, push a GitHub Pages cada 6 min como máximo para evitar despliegues solapados y correos masivos.

---

## HOJA DE RUTA — para retomar desde la PC

El sistema está COMPLETO y corriendo solo (scan 1/min + backup 03:00 UTC + sitio auto-publicado). Lo que falta es producto y precisión, no infraestructura. Orden sugerido:

1. **Depurar matching de edges** — hoy cruza solo el MISMO evento (tokens raros + categoría): precisión alta, recall bajo (1-2 edges/día). Mejora: embeddings + similitud coseno (sin API) o DeepSeek confirmando pares candidatos. Objetivo: 5-15 edges legítimos/día.
2. **F4 narración DeepSeek** — justificaciones redactadas con contexto (la razón heurística ya existe; F4 la enriquece). Clave YA autorizada y en uso para traducción.
3. **F5 piloto Perú** — verificar el filtro de país con mercados peruanos reales; ajustar keywords si hace falta.
4. **Afinar mispricings** — barrer mercados de menor volumen (hoy los top-200 líquidos son eficientes → 0 señales).
5. **Backtest Fase 2** — momentum/contrarian con el historial de snapshots acumulado.
6. **Histórico de aciertos** — trackear cuántos edges/ballenas convergen (marketing: "nuestras señales aciertan X%").
7. **Canal X/Telegram** — publicar detecciones gratis + suscripciones USDC ($10-25/mes).
8. **On-ramps USDC Nicaragua** — verificación manual (p2p.binance.com fiat NIO, moonpay.com, transak.com).
9. **Validar Azuro** — liquidez real, fees, gas (Fase 4 trading).
10. **Firebase/cPanel/dominio** — fase futura (el estático migra sin cambios).

**Costos activos:** DeepSeek solo traduce títulos NUEVOS (caché SQLite) → centavos el primer día, ~$0 después. Fuentes externas (Kalshi/Manifold/PredictIt) consultadas cada 10 min vía caché. Sin otros gastos.

**Limitaciones conocidas (documentadas):** Metaculus exige cuenta (fuera); matching de edges estricto a propósito (precisión > cantidad); las probabilidades son heurísticas, no garantías (avisado en el pie del sitio).

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
