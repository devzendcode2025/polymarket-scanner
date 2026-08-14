# CHAT_RESUMEN — polymarket-scanner

### 2026-08-14 [00:50] — v0.7.0: F3 EDGE "datos ganadores" + categorías + 25 ítems
- **Petición:** "Sigue con eso" (F3 cross-check) + "solo miro 10 ítems... deberían tener categorías y más de 10 tarjetas".
- **Acciones:** (a) CATEGORÍAS: nuevo categorias.py clasifica cada señal/mercado (Política, Deportes, Cripto, Economía, Tecnología, Ciencia y espacio, Entretenimiento, Otros) + segundo selector en el dashboard + badge en cada tarjeta; (b) MÁS ÍTEMS: ballenas 15→25, momentum 20→30, top_volumen 10→25, slices del dashboard 10→25; (c) F3 CROSS-CHECK: nuevo crosscheck.py — Kalshi + Manifold + PredictIt (Metaculus descartada: ahora exige cuenta), caché de 10 min en workspace/data/crosscheck_cache.json (ignorado), matching por tokens raros compartidos + misma categoría (depurado 3 veces: eliminados falsos positivos tipo "Chargers NFL"↔"MLB", "Ronald Acuña"↔"James Bond"); edges con prob/confianza/horizonte/razón + links a cada fuente + panel "💎 Datos ganadores" en el dashboard.
- **Resultado:** 1 edge legítimo en la ventana real (Senado Carolina del Sur, Poly 17% vs Manifold 1%); 25 top mercados con categorías y traducciones; py_compile + node --check + make test TODO OK; v0.7.0 publicada. FIX importante: las claves de categorías se escribieron sin acentos ('Economia') → corregidas a 'Economía'/'Política'/'Tecnología' para que el filtro JS coincida.
- **Pendientes:** depurar matching de edges (LLM/embeddings para cruzar el MISMO evento — hoy el recall es bajo pero la precisión es alta); F4 narración DeepSeek; F5 piloto Perú; afinar mispricings; on-ramps USDC; validar Azuro; canal X/Telegram.

### 2026-08-14 [00:10] — v0.6.0: Versión MOBILE + TODO en español (traducción DeepSeek)
- **Petición:** usuario desde el celular: (1) el dashboard no se veía en móvil ("acordaste la versión mobile"); (2) "todo tiene que estar en español" (los títulos de los mercados venían en inglés de la API).
- **Acciones:** (a) MOBILE: media query 768px — tablas se convierten en tarjetas apiladas con etiquetas (data-label), stats 2 columnas, selector de país a ancho completo, barras de probabilidad visibles en móvil; (b) TRADUCCIÓN: nuevo translate.py (DeepSeek deepseek-chat, clave leída del .env del perfil de Hermes SIN versionarse ni imprimirse), tabla translations en SQLite como CACHÉ (solo traduce títulos nuevos, máx 30 por corrida → costo casi cero tras el primer día), fallback silencioso al original si no hay clave o falla la API; run_scan traduce ballenas/mispricings/momentum/top_volumen (campos question_es/titulo_es); render_dashboard ahora incluye top_volumen en data.json; dashboard usa data.json como fuente principal (traducido, ≤1 min de frescura) con fallback a APIs en vivo.
- **Resultado:** traducciones reales verificadas de calidad ("Will the price of Bitcoin be above $58,000 on August 14?" → "¿Estará el precio de Bitcoin por encima de $58,000 el 14 de agosto?"; "O/U" → "Más/Menos"); 13 títulos traducidos en el primer scan; py_compile + node --check + make test TODO OK; v0.6.0 publicada.
- **Pendientes:** F3 cross-check fuentes externas (Kalshi/Metaculus/Manifold) → EDGE "datos ganadores"; F4 pendiente solo narración DeepSeek (la traducción ya usa la clave); F5 piloto Perú; afinar mispricings; on-ramps USDC; validar Azuro; canal X/Telegram.

### 2026-08-13 [23:30] — v0.5.0: Links directos + filtro por país + analista heurístico (F1+F2)
- **Petición:** funcionalidades: (1) filtrar por país (ej. Perú) y ver mercados ejecutables; (2) cada señal con justificación + probabilidad de que funcione ("datos ganadores"); (3) links directos a Polymarket. Usuario aprobó Opción 2 (F1+F2). DeepSeek (misma clave de Hermes) autorizada pero queda para F4.
- **Acciones:** polymarket_client.parse_market ahora captura tags de Gamma; scanner.py agrega slug/tags a mispricings/momentum/ballenas; NUEVO analyst.py (heurístico puro, sin LLM): prob 0-100 + confianza (alta/media/baja) + horizonte (24h/72h) + razón numérica por señal; run_scan enriquece ballenas con volumen del mercado (match conditionId + slug) y aplica analyst; dashboard reescrito: selector de 27 países LatAm (23 ✅ ejecutables / 4 🔒 solo datos: Brasil, Cuba, Nicaragua, Venezuela), filtro por tags+keywords en ballenas en vivo/top/mispricings/momentum, botón "Abrir ↗" en cada fila y tarjeta, tarjetas de señal con barra de probabilidad + confianza + horizonte + justificación. Template canónico sigue en workspace/web/dashboard.html (el cron lo copia a docs/).
- **Resultado:** py_compile + node --check OK; scan real OK (ballenas enriquecidas: BUY $4,137 → prob 58% media 24h + URL); reglas calibradas (mispricing desvío 0.04 → 91% alta; momentum 12.5% → 62% media). run-all.sh verde tras commit.
- **Pendientes:** F3 cross-check fuentes externas (Kalshi/Metaculus/Manifold) → EDGE "datos ganadores"; F4 DeepSeek narrando justificaciones; F5 piloto por país; afinar mispricings; on-ramps USDC; validar Azuro; canal X/Telegram.

### 2026-08-13 [22:35] — Dashboard DINÁMICO (v0.4.0)
- **Petición:** "necesitas mostrar esos datos dinámicamente en la página html, sino para qué sirve. Hazlo."
- **Acciones:** verificado CORS de las APIs de Polymarket (Access-Control-Allow-Origin: * en gamma/data/clob). Reescribido docs/index.html como app JS: fetch EN VIVO a Data API (ballenas ≥ $1k, top 10) y Gamma API (top 10 mercados por volumen) directo desde el navegador + data.json (detecciones del pipeline: mispricings/momentum) + auto-refresh 60s + reloj "hace Xs" + hora Nicaragua (America/Managua). render_dashboard.py simplificado → solo genera docs/data.json. cron_scan.sh añade cp del template a docs/.
- **Resultado:** sitio verificado en línea con la app nueva (intento 4 del rebuild); data.json servido con CORS *; JS validado con node --check; cron automático ya regenera data.json (stamp 22:31). Commits v0.4.0.
- **Pendientes:** confirmar visual del usuario en navegador; afinar mispricings; canal X/Telegram; Firebase/cPanel/dominio (fase futura).

### 2026-08-13 [22:00] — Automatización completa: cron 1/min + poda + backup
- **Petición:** scan cada 1 minuto sin llenar el disco; evaluar GitHub/Firebase para datos. Decisión: Firebase/cPanel/dominio = fase futura; ahora diseño A.
- **Acciones:** run_scan.py con --quiet + snapshots filtrados (≥0.5% de cambio) + poda TTL 30d + reportes últimos 20 + tamaño BD en reporte. render_dashboard.py genera docs/index.html (hora Nicaragua). cron_scan.sh (scan→render→push condicional: detecciones o ≥6 min). backup_daily.sh → repo privado polymarket-scanner-data (backup sqlite + gzip + poda 30).
- **Bugs encontrados y corregidos:** (1) backup no pusheaba con "nothing to commit" → push siempre; (2) remote del backup sin token → token del .env; (3) render escribía en workspace/docs/ (resolución de rutas BASE=workspace) → PROYECTO=3 niveles, docs/ real actualizado; (4) cronjob '1m' creaba one-shot → recreado con '* * * * *' repeat forever.
- **Resultado:** crons activos: polymarket-scan-1min (job 7a818b7cc17a, cada minuto, script puro, silencioso) + polymarket-backup-diario (job e6232106fb87, 03:00 UTC). Sitio verificado actualizado (scan 15:38 hora Nicaragua). Repo privado con primer backup. BD 0.27 MB.
- **Pendientes:** confirmar primeras corridas automáticas del cron; afinar mispricings; on-ramps; validar Azuro; Firebase/cPanel/dominio (fase futura); canal X/Telegram.

### 2026-08-13 [21:40] — Sitio público publicado (GitHub Pages)
- **Petición:** publicar el dashboard gratis (opción A elegida). Usuario: devzendcode2025. Token generado con scope "repo".
- **Acciones:** token guardado en .env (chmod 600, excluido de git). gh CLI pidió scope read:org → no necesario: repo creado vía API REST (HTTP 201), push con token en remote URL, Pages activado vía API (branch main, path /docs).
- **Resultado:** https://devzendcode2025.github.io/polymarket-scanner/ → HTTP 200, contenido verificado (dashboard completo con ballenas reales). Commits v0.2.0. Nota: el token vive en el remote URL de .git/config — necesario para el push automático futuro; revocable desde GitHub.
- **Pendientes:** generador automático (render_dashboard.py) + cron de scans con publicación automática; canal X/Telegram.

### 2026-08-13 [21:20] — Runner canónico de verificación
- **Petición:** tracker de verificación marcó unverified tras editar .gitignore (script temporal eliminado = sin evidencia persistente).
- **Acciones:** persistidos los checks como regresión en verificacion/ (run-all.sh = py_compile + verify_gitignore.sh); primera corrida falló (verificacion/ sin versionar → tree sucio), se versionó (v0.1.1) y la corrida quedó en verde; VERIFICACION.md con evidencia.
- **Resultado:** verificacion/run-all.sh → TODO OK (exit 0). Commits v0.1.1 (+v0.1.2 pendiente con este registro).
- **Pendientes:** sin cambios respecto a los anteriores (token GitHub, publicación Pages, generador, cron).

### 2026-08-13 [21:05] — Mockup del dashboard web
- **Petición:** "Necesitamos un sitio web, como van a ver los datos los clientes."
- **Acciones:** extraídos datos reales del último scan (top volumen, ballenas); creado mockup visual autocontenido dark-theme en workspace/web/dashboard.html (stats, ballenas, mispricings, momentum, top volumen, CTA de suscripción).
- **Resultado:** mockup listo para revisión del usuario (abrir en navegador local). Pendiente: aprobación de diseño + decisión de arquitectura/hosting (estático vs backend).
- **Pendientes:** generador del dashboard desde reportes; hosting; canal X/Telegram.

### 2026-08-13 [20:40] — Primer scan real
- **Petición:** arrancar el proyecto (OK explícito del usuario) + recordatorio: puede chatear por WhatsApp; mantener control files al día.
- **Acciones:** creado polymarket-scanner en /srv/hermes-projects/proyectos con 5 archivos de control (README, MEMORIA con bloque vivo, CHAT_RESUMEN, TAREAS por fases, REGLAS) + pipeline en workspace/scripts (polymarket_client.py, db.py, scanner.py, run_scan.py — solo stdlib).
- **Resultado:** scan real OK: 200 mercados binarios activos, 5 ballenas (máx $5,890 BUY tenis Cincinnati Open; también NFL y LoL), 0 mispricings en top-200 (líquidos = eficientes; ajustar a menor volumen), 0 momentum (sin historial previo). Reportes en workspace/reports/technical/scan_20260813_204015.{json,txt}. SQLite en workspace/data/polymarket.db.
- **Pendientes:** cron periódico; afinar mispricings; on-ramps USDC; validar Azuro; canal X/Telegram; posible resumen diario por WhatsApp (gateway).

### 2026-08-13 [20:00] — Creación del proyecto y ruta de negocio
- **Petición:** "cómo podemos ganar dinero usando Polymarket y tomando las decisiones correctas". Luego: plan para Opción 1 (vender datos) y Opción 2 (trading Azuro), y qué países latinoamericanos están habilitados.
- **Acciones:**
  - Verificación en vivo del artículo oficial "Geographic Restrictions": Nicaragua en lista de 39 países bloqueados → trading en Polymarket NO (ni VPN, ni cuenta USA).
  - Verificación de APIs públicas (Gamma/CLOB/Data): accesibles globalmente, sin auth.
  - Informe LatAm: 23 países habilitados / 4 bloqueados (Brasil, Cuba, Nicaragua, Venezuela).
  - Plan de venta: Telegram + X (español primero), cobro en USDC, precios benchmark ($10-25/mes), embudo gratis→pago, B2B feed después.
  - Creación del proyecto polymarket-scanner con archivos de control + pipeline Fase 1.
- **Resultado:** proyecto creado en /srv/hermes-projects/proyectos/polymarket-scanner. Pipeline escrito (cliente APIs + SQLite + scanner). Primer scan en ejecución.
- **Pendientes:** validar scan real; verificar on-ramps USDC Nicaragua; validar Azuro; canal X/Telegram; backtest; (usuario recordó: puede chatear por WhatsApp si no está en la computadora — mantener control files al día para sync entre canales).

### 2026-08-13 [~19:00] — Investigación on-ramps (subagente)
- **Petición:** verificar on-ramps/exchanges para comprar USDC desde Nicaragua.
- **Acciones:** subagente con tools web/browser; su navegador falló (11 intentos) → informe de conocimiento marcado como NO verificado en vivo.
- **Resultado:** consistente con lo estable: Binance/Bybit/OKX/MEXC/KuCoin aceptan Nicaragua; fee retiro USDC→Polygon ≈ 1 USDC; tarjeta ≈ 1.8%; cuenta bancaria USA NO habilita on-ramps gringos. Su dato "Polymarket no restringe Nicaragua" quedó DESCARTADO (desactualizado; la verificación oficial del help center lo contradice).
- **Pendientes:** verificación manual opcional: p2p.binance.com (fiat NIO), support.moonpay.com y transak.com/supported-countries (buscar Nicaragua), binance.com/fee/schedule.
