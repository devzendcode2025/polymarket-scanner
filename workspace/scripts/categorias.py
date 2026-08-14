#!/usr/bin/env python3
"""Clasifica titulos de mercados por categoria (v0.7.0).

Orden de prioridad por lista. Se evalua el titulo original (EN) y el
traducido (ES) juntos. Fallback: "Otros".
"""
import re

CATEGORIAS = [
    ("Deportes", [
        "nfl", "nba", "mlb", "nhl", "wnba", "ufc", "boxing", "tennis", "wimbledon",
        "us open", "french open", "australian open", "soccer", "futbol", "fútbol",
        "world cup", "champions league", "la liga", "premier league", "super bowl",
        "olympics", "olympic", "gold medal", "grand slam", "atp", "wta", "esports",
        "lcs", "league of legends", "cincinnati open", "match", "championship",
        "champion", "series", "game", "quarterfinal", "semifinal", "final",
        "mls", "ncaa", "masters", "us open", "tour de france", "f1", "formula 1",
        "grand prix", "nascar", "pga", "liverpool", "real madrid", "barcelona",
        "messi", "ronaldo", "swiatek", "djokovic", "alcaraz", "leagues", "playoffs",
        "eliminatorias", "copa", "mundial", "supercopa", "partido", "juego",
    ]),
    ("Cripto", [
        "bitcoin", "btc", "ethereum", "eth", "solana", "crypto", "cryptocurrency",
        "dogecoin", "doge", "xrp", "cardano", "polkadot", "chainlink", "uniswap",
        "stablecoin", "usdc", "usdt", "blockchain", "token", "altcoin", "mining",
        "halving", "etf", "coinbase", "binance", "defi", "web3", "nft",
        "price of bitcoin", "precio de bitcoin", "cripto",
    ]),
    ("Política", [
        "election", "president", "presidential", "senate", "senator", "congress",
        "house", "governor", "mayor", "prime minister", "vote", "voting", "nominat",
        "candidate", "cabinet", "government", "policy", "tariff", "impeach",
        "trump", "biden", "harris", "vance", "obama", "putin", "zelensky",
        "netanyahu", "boluarte", "milei", "maduro", "ortega", "bukele", "petro",
        "lula", "sheinbaum", "amlo", "xiomara", "noboa", "boric", "abinader",
        "eleccion", "elecciones", "presidente", "gobierno", "senado", "congreso",
        "legislative", "referendum", "ballot", "supreme court", "minister",
        "parliament", "coalition", "democrat", "republican", "midterm",
        "nominated", "nomination", "debate", "inaugur", "sanctions",
    ]),
    ("Economía", [
        "fed", "federal reserve", "inflation", "inflacion", "interest rate",
        "rate cut", "rate hike", "recession", "gdp", "unemployment", "jobs report",
        "nonfarm", "stock market", "s&p", "nasdaq", "dow jones", "crude oil",
        "oil price", "gas price", "housing", "cpi", "inflation report", "tariff",
        "trade war", "shutdown", "debt ceiling", "treasury", "yield", "dollar",
        "eurusd", "gold price", "silver price", "economy", "economia", "pib",
        "desempleo", "inflacion", "petroleo", "petróleo", "recesion", "recesión",
        "banco central", "tasa de interes", "tasas", "bolsa", "mercado",
    ]),
    ("Tecnología", [
        "ai", "artificial intelligence", "openai", "chatgpt", "google", "alphabet",
        "apple", "samsung", "tesla", "spacex", "twitter", "x corp", "meta",
        "facebook", "instagram", "microsoft", "nvidia", "amd", "intel", "iphone",
        "machine learning", "robot", "self-driving", "quantum", "chip", "semiconductor",
        "elon", "musk", "neuralink", "apple", "android", "software", "cyber",
        "hack", "data breach", "inteligencia artificial", "tecnologia", "tecnología",
        "gpt", "llm", "model", "trump media", "truth social",
    ]),
    ("Ciencia y espacio", [
        "nasa", "space", "mars", "marte", "moon", "luna", "asteroid", "asteroide",
        "comet", "cometa", "satellite", "satelite", "satélite", "rocket", "cohete",
        "launch", "lanzamiento", "starship", "eclipse", "solar storm", "climate",
        "global warming", "sea level", "earthquake", "terremoto", "volcano", "volcan",
        "volcán", "hurricane", "huracan", "huracán", "tornado", "wildfire",
        "incendio", "flood", "inundacion", "inundación", "heat wave", "ola de calor",
        "cold snap", "drought", "sequia", "sequía", "el nino", "el niño", "la nina",
        "la niña", "pandemic", "pandemia", "virus", "vaccine", "vacuna", "disease",
        "enfermedad", "cancer", "medical", "medicina", "drug", "fda", "clinical trial",
        "ensayo clinico", "cure", "cura", "health", "salud", "covid",
    ]),
    ("Entretenimiento", [
        "movie", "film", "pelicula", "película", "oscar", "grammy", "box office",
        "taylor swift", "album", "music", "musica", "música", "concert", "concierto",
        "netflix", "disney", "star wars", "marvel", "tiktok", "youtube", "k pop",
        "kpop", "celebrity", "actor", "actress", "beyonce", "beyoncé", "golden globes",
        "emmy", "billboard", "spotify", "hollywood", "cinema", "cannes", "tour",
        "gira", "single", "song", "cancion", "canción", "rapper", "band", "grupo",
        "video game", "videogame", "videojuego", "gta", "zelda", "nintendo", "playstation",
        "xbox", "minecraft", "fortnite", "streaming", "podcast", "influencer",
    ]),
]

_STOP = set((
    "will what the and for with from that this these those before after than his her "
    "their are was has have had would should could does did not over under next last "
    "year month week day when who which into about against between during without "
    "through out up down off on in at by to of a an or if then else too also just only "
    "can may might must shall be been being is are were it its our your my their "
    "august september october november december january february march april may june "
    "july 2024 2025 2026 2027 2028 2029 2030 today tomorrow".split()
))

# Tokens genericos de los mercados de prediccion: aportan estructura, no identidad.
# Se excluyen del matching entre fuentes para evitar cruces absurdos
# (ej. "Chargers NFL" con "MLB games" por compartir "regular season").
_GENERICOS = set((
    "regular season seasons games game match matches finish finished most least more "
    "total number amount percent returns return win wins winning won victory victories "
    "election elections electoral vote votes voting voter voters candidate candidates "
    "party parties seat seats state states county counties district districts "
    "republican republicans democrat democrats democratic gop primary primaries "
    "president presidential senate senator congress congressional house governor "
    "governors minister ministers prime cabinet government nomination nominated "
    "nominate run running reelected reelect incumbent challenger margin margins "
    "reach reaches reached hit hits passes pass passed top first last next current "
    "new open close closed end starts started ending begins beginning take takes "
    "make makes gets get go goes coming comes happen happens happen before during "
    "after since until within outside above below over under more than less than "
    "at least at most or more or less percent points point lead leads leading "
    "ahead behind favor favourite favorite win by win the win an win a lose loses "
    "lost defeat defeats beaten be the be in be out take office take power assume "
    "2024 2025 2026 2027 2028 2029 2030 august september october november december "
    "january february march april may june july monday tuesday wednesday thursday "
    "friday saturday sunday today tomorrow yesterday"
).split())


def clasificar(titulo, titulo_es=None):
    """Devuelve la categoria del titulo ('Otros' si no matchea ninguna)."""
    texto = f"{titulo or ''} {titulo_es or ''}".lower()
    texto = re.sub(r"[^a-z0-9áéíóúñü ]", " ", texto)
    for cat, kws in CATEGORIAS:
        for kw in kws:
            if kw in texto:
                return cat
    return "Otros"


def tokens(titulo):
    """Tokens significativos para matching entre fuentes (sin genericos)."""
    t = re.sub(r"[^a-z0-9 ]", " ", (titulo or "").lower())
    return {w for w in t.split() if len(w) >= 4 and w not in _STOP and w not in _GENERICOS}
