# REGLAS_PROYECTO — polymarket-scanner

Reglas durables. No cambiar sin avisar al usuario.

1. **NO operar trading en Polymarket desde Nicaragua.** Nicaragua está en la lista oficial de países bloqueados. Prohibido usar VPN para evadirlo (ToS 2.1.4) y prohibido usar identidad/cuenta USA ("U.S. persons" bloqueados). Este proyecto usa SOLO las APIs públicas de solo lectura.
2. **Solo APIs públicas read-only** (Gamma/CLOB/Data). Sin autenticación, sin POST, sin endpoints privados.
3. **Cobros de suscripciones en USDC** (Stripe/PayPal no operan para receptor en Nicaragua). El público de prediction markets ya usa USDC.
4. **Idioma: español primero, inglés después.** El edge comercial es el mercado hispano desatendido.
5. **Archivos de control al día tras cada trabajo** (README/MEMORIA/CHAT_RESUMEN/TAREAS). Vale para cualquier canal (CLI, WhatsApp, cron).
6. **Capital real de trading solo tras backtest + paper trading aprobados** (regla de la Fase 4).
7. **Registro de todo trade con tesis escrita** antes de entrar (cuando llegue la fase de trading).
