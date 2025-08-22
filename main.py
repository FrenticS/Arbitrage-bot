# One-file Arbitrage Bot (compact UI, i18n + auto top watcher + New Tokens)
# Env: TELEGRAM_BOT_TOKEN
# Replit-ready (Flask keep-alive) + Raw Telegram Bot API + requests only.

import os, json, time, threading, logging
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional

import requests
from flask import Flask

# ----------------------- CONFIG -----------------------

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
if not BOT_TOKEN:
    raise RuntimeError("Set TELEGRAM_BOT_TOKEN in Replit Secrets.")

API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# watch / autoscan every N seconds
SCAN_PERIOD = 30

# default pair
DEFAULT_PAIR = "BTC/USDT"

# short watchlist used in “Top Opportunities” and Auto watcher
WATCHLIST = [
    "BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "XRP/USDT",
    "TON/USDT", "DOGE/USDT", "ADA/USDT", "TRX/USDT", "ZIL/USDT",
]

# CoinPaprika (free, no key)
PAPR_BASE = "https://api.coinpaprika.com/v1"

# Enable logs
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("arb-bot")

# ----------------------- i18n -----------------------

LANGS = {
    "en": dict(
        scan_now="Scan Now",
        change_pair="Change Pair",
        top="Top Opportunities",
        auto_on="Auto: ON",
        auto_off="Auto: OFF",
        back="Back",
        language="Language",
        new_tokens="New Tokens",
        lang_pick="Choose language:",
        lang_en="English",
        lang_ru="Русский",
        lang_uz="Oʻzbekcha",
        home_pair="Pair: <b>{pair}</b>\nTap <b>Scan Now</b> to fetch prices.",
        ask_pair="Type a symbol like <b>btc</b>, <b>BTCUSDT</b>, or <b>BTC/USDT</b>.",
        bad_pair="Didn't understand. Example: <b>eth</b> or <b>ETHUSDT</b>.",
        pair_set="Pair set to <b>{pair}</b>.",
        no_spreads="No positive spreads right now.",
        top_title="<b>Top Opportunities</b>",
        auto_now="Auto scan: <b>{state}</b>.",
        new_opp="🔥 New opportunity: <b>{pair}</b> — <b>{pct:.2f}%</b>\nBuy @ {bx} {bp} | Sell @ {sx} {sp}",
        thresholds_note="(fees/slippage not included)",
        exchanges_title="exch         bid        ask",
        no_quotes="No quotes for {pair}.",
        nt_title="<b>Recently Added Coins</b>",
        nt_empty="No new coins found right now.",
        nt_hint="Tip: type <code>info TON</code> (replace with any symbol) for details.\nNot financial advice — DYOR.",
        info_not_found="No info for that symbol.",
        info_title="<b>{symbol}</b> — {name}",
        info_price="Price: ${price}",
        info_mcap="Market cap: ${mcap}",
        info_vol="24h volume: ${vol}",
        info_change="24h change: {chg}%",
        info_note="Not financial advice — DYOR.",
    ),
    "ru": dict(
        scan_now="Сканировать",
        change_pair="Пара",
        top="Топ возможностей",
        auto_on="Авто: ВКЛ",
        auto_off="Авто: ВЫКЛ",
        back="Назад",
        language="Язык",
        new_tokens="Новые токены",
        lang_pick="Выберите язык:",
        lang_en="English",
        lang_ru="Русский",
        lang_uz="Oʻzbekcha",
        home_pair="Пара: <b>{pair}</b>\nНажмите <b>Сканировать</b> для получения цен.",
        ask_pair="Введите символ: <b>btc</b>, <b>BTCUSDT</b> или <b>BTC/USDT</b>.",
        bad_pair="Не понял. Пример: <b>eth</b> или <b>ETHUSDT</b>.",
        pair_set="Пара установлена: <b>{pair}</b>.",
        no_spreads="Сейчас нет положительного спреда.",
        top_title="<b>Топ возможностей</b>",
        auto_now="Авто-сканирование: <b>{state}</b>.",
        new_opp="🔥 Новая возможность: <b>{pair}</b> — <b>{pct:.2f}%</b>\nПокупка @ {bx} {bp} | Продажа @ {sx} {sp}",
        thresholds_note="(комиссии/проскальзывание не учтены)",
        exchanges_title="биржа        bid        ask",
        no_quotes="Нет котировок для {pair}.",
        nt_title="<b>Недавно добавленные монеты</b>",
        nt_empty="Сейчас нет новых монет.",
        nt_hint="Подсказка: введите <code>info TON</code> (любой символ) для деталей.\nНе финсовет — DYOR.",
        info_not_found="Нет данных по этому символу.",
        info_title="<b>{symbol}</b> — {name}",
        info_price="Цена: ${price}",
        info_mcap="Капитализация: ${mcap}",
        info_vol="Объём 24ч: ${vol}",
        info_change="Изм. 24ч: {chg}%",
        info_note="Не финсовет — DYOR.",
    ),
    "uz": dict(
        scan_now="Skan Qil",
        change_pair="Juftlik",
        top="Eng yaxshi imkoniyatlar",
        auto_on="Avto: YOQILGAN",
        auto_off="Avto: O‘CHIRILGAN",
        back="Orqaga",
        language="Til",
        new_tokens="Yangi tokenlar",
        lang_pick="Tilni tanlang:",
        lang_en="English",
        lang_ru="Русский",
        lang_uz="Oʻzbekcha",
        home_pair="Juftlik: <b>{pair}</b>\nNarxlarni olish uchun <b>Skan Qil</b> tugmasini bosing.",
        ask_pair="Belgini yozing: <b>btc</b>, <b>BTCUSDT</b> yoki <b>BTC/USDT</b>.",
        bad_pair="Tushunmadim. Masalan: <b>eth</b> yoki <b>ETHUSDT</b>.",
        pair_set="Juftlik o‘rnatildi: <b>{pair}</b>.",
        no_spreads="Hozir ijobiy spreddan yo‘q.",
        top_title="<b>Eng yaxshi imkoniyatlar</b>",
        auto_now="Avto skan: <b>{state}</b>.",
        new_opp="🔥 Yangi imkoniyat: <b>{pair}</b> — <b>{pct:.2f}%</b>\nSotib olish @ {bx} {bp} | Sotish @ {sx} {sp}",
        thresholds_note="(komissiya/slippage hisobga olinmagan)",
        exchanges_title="birja        bid        ask",
        no_quotes="{pair} uchun narxlar yo‘q.",
        nt_title="<b>Yaqinda qo‘shilgan tanga</b>",
        nt_empty="Hozircha yangi tanga yo‘q.",
        nt_hint="Maslahat: tafsilotlar uchun <code>info TON</code> deb yozing.\nMoliyaviy maslahat emas — DYOR.",
        info_not_found="Bu simbol uchun ma’lumot yo‘q.",
        info_title="<b>{symbol}</b> — {name}",
        info_price="Narx: ${price}",
        info_mcap="Bozor kapit.: ${mcap}",
        info_vol="24 soat hajm: ${vol}",
        info_change="24 soat o‘zgarish: {chg}%",
        info_note="Moliyaviy maslahat emas — DYOR.",
    ),
}

def ui_words_all() -> set:
    words = set()
    for l in LANGS.values():
        words |= {l["scan_now"], l["change_pair"], l["top"],
                  l["auto_on"], l["auto_off"], l["back"],
                  l["language"], l["new_tokens"],
                  l["lang_en"], l["lang_ru"], l["lang_uz"]}
    return {w.upper() for w in words}

UI_WORDS = ui_words_all()

# ----------------------- TELEGRAM HELPERS -----------------------

def tg(method: str, **payload):
    r = requests.post(f"{API}/{method}", json=payload, timeout=25)
    if r.status_code != 200:
        log.warning("TG %s -> %s %s", method, r.status_code, r.text[:200])
    try:
        return r.json()
    except Exception:
        return {}

def send(chat_id: int, text: str, kb: List[List[str]] = None, parse: str = "HTML"):
    reply_markup = {"keyboard":[[{"text":b} for b in row] for row in (kb or [])],
                    "resize_keyboard": True}
    return tg("sendMessage", chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode=parse)

def get_updates(offset: int):
    return tg("getUpdates", timeout=25, offset=offset, allowed_updates=["message"])

# ----------------------- STATE -----------------------

STATE: Dict[int, Dict[str, Any]] = {}

def st(chat_id: int) -> Dict[str, Any]:
    if chat_id not in STATE:
        STATE[chat_id] = {
            "pair": DEFAULT_PAIR,
            "auto": False,
            "last_scan": 0.0,
            "threshold": 0.10,   # % min spread to notify during auto
            "lang": "en",
            "awaiting": None,    # None | "pair" | "lang"
            "auto_last_key": "", # to avoid repeats (pair|bx|sx)
        }
    return STATE[chat_id]

def T(chat_id: int) -> Dict[str, str]:
    return LANGS.get(st(chat_id)["lang"], LANGS["en"])

# ----------------------- PAIR UTILS -----------------------

def to_usdt_pair(symbol: str) -> str:
    s = symbol.strip().upper()
    if s in UI_WORDS:
        return ""  # ignore UI words
    if "/" in s:
        base, quote = s.split("/", 1)
        if not quote: quote = "USDT"
        return f"{base}/USDT"
    if s.endswith("USDT"):
        return f"{s[:-4]}/USDT"
    if 2 <= len(s) <= 12 and s.isalpha():
        return f"{s}/USDT"
    return ""

def norm_pair_for_exch(pair: str, exch: str) -> str:
    base, quote = pair.split("/")
    if exch in ("binance", "mexc", "bitget", "bybit"):
        return f"{base}{quote}"
    if exch in ("okx", "kucoin"):
        return f"{base}-{quote}"
    if exch == "gate":
        return f"{base}_{quote}"
    if exch == "htx":  # Huobi/HTX uses lowercase
        return f"{base}{quote}".lower()
    return pair

def fmt_price(x: float) -> str:
    s = f"{x:.10f}".rstrip("0").rstrip(".")
    return s if len(s) >= 8 else s + " " * (8 - len(s))

# ----------------------- EXCHANGE QUOTES -----------------------

def q_binance(s: str):
    r = requests.get("https://api.binance.com/api/v3/ticker/bookTicker",
                     params={"symbol": s}, timeout=10)
    if r.ok:
        j = r.json()
        return float(j["bidPrice"]), float(j["askPrice"])
    return None, None

def q_bitget(s: str):
    r = requests.get("https://api.bitget.com/api/spot/v1/market/bestBidAsk",
                     params={"symbol": s}, timeout=10)
    if r.ok:
        j = r.json()
        if j.get("data"):
            d = j["data"][0]
            return float(d["bestBid"]), float(d["bestAsk"])
    return None, None

def q_mexc(s: str):
    r = requests.get("https://api.mexc.com/api/v3/ticker/bookTicker",
                     params={"symbol": s}, timeout=10)
    if r.ok:
        j = r.json()
        return float(j["bidPrice"]), float(j["askPrice"])
    return None, None

def q_htx(s: str):
    r = requests.get("https://api.huobi.pro/market/detail/merged",
                     params={"symbol": s}, timeout=10)
    if r.ok:
        j = r.json()
        if j.get("tick"):
            t = j["tick"]
            return float(t["bid"][0]), float(t["ask"][0])
    return None, None

def q_kucoin(s: str):
    r = requests.get("https://api.kucoin.com/api/v1/market/orderbook/level1",
                     params={"symbol": s}, timeout=10)
    if r.ok:
        j = r.json()
        if j.get("data"):
            d = j["data"]
            return float(d["bestBid"]), float(d["bestAsk"])
    return None, None

def q_bybit(s: str):
    r = requests.get("https://api.bybit.com/v5/market/tickers",
                     params={"category": "spot", "symbol": s}, timeout=10)
    if r.ok:
        j = r.json()
        if j.get("result") and j["result"].get("list"):
            d = j["result"]["list"][0]
            return float(d["bid1Price"]), float(d["ask1Price"])
    return None, None

def q_okx(s: str):
    r = requests.get("https://www.okx.com/api/v5/market/ticker",
                     params={"instId": s}, timeout=10)
    if r.ok:
        j = r.json()
        if j.get("data"):
            d = j["data"][0]
            return float(d["bidPx"]), float(d["askPx"])
    return None, None

def q_gate(s: str):
    r = requests.get("https://api.gateio.ws/api/v4/spot/tickers",
                     params={"currency_pair": s}, timeout=10)
    if r.ok:
        j = r.json()
        if j:
            d = j[0]
            return float(d["highest_bid"]), float(d["lowest_ask"])
    return None, None

EXCHS = [
    ("🟡 binance", "binance", q_binance),
    ("🔵 bitget",  "bitget",  q_bitget),
    ("🟢 mexc",    "mexc",    q_mexc),
    ("🔴 htx",     "htx",     q_htx),
    ("🟠 kucoin",  "kucoin",  q_kucoin),
    ("🟤 bybit",   "bybit",   q_bybit),
    ("⚫ okx",     "okx",     q_okx),
    ("🔷 gate",    "gate",    q_gate),
]

def fetch_all(pair: str) -> List[Tuple[str,float,float]]:
    out = []
    for label, key, fn in EXCHS:
        sym = norm_pair_for_exch(pair, key)
        try:
            bid, ask = fn(sym)
            if bid and ask and bid > 0 and ask > 0:
                out.append((label, bid, ask))
        except Exception as e:
            log.warning("fetch %s %s failed: %s", key, sym, e)
    return out

def best_spread(rows: List[Tuple[str,float,float]]) -> Tuple[float,str,str,float,float]:
    if not rows: return (0,"","",0,0)
    best = (0, "", "", 0.0, 0.0)
    for b in rows:
        for s in rows:
            pct = (b[1] - s[2]) / s[2] * 100.0
            if pct > best[0]:
                best = (pct, s[0], b[0], s[2], b[1])
    return best

def render_table(pair: str, rows: List[Tuple[str,float,float]], tr: Dict[str,str]) -> str:
    head = f"<b>Arbitrage — {pair}</b>\n<pre>{tr['exchanges_title']}</pre>\n"
    body = ""
    for label, bid, ask in rows:
        name = (label + "           ")[:12]
        body += f"<pre>{name} {fmt_price(bid):>10} {fmt_price(ask):>10}</pre>\n"
    pct, bx, sx, bp, sp = best_spread(rows)
    if pct > 0:
        tail = (f"\n📥 Buy @ <b>{bx}</b> ask <b>{fmt_price(sp)}</b>\n"
                f"📤 Sell @ <b>{sx}</b> bid <b>{fmt_price(bp)}</b>\n"
                f"🧮 Gross spread ≈ <b>{pct:.2f}%</b> {tr['thresholds_note']}")
    else:
        tail = "\nℹ️ No positive spread right now."
    return head + body + tail

# ----------------------- CoinPaprika: New Tokens -----------------------

def cp_get(path: str, params: dict = None):
    try:
        r = requests.get(f"{PAPR_BASE}{path}", params=params or {}, timeout=15)
        if r.ok:
            return r.json()
    except Exception as e:
        log.warning("CoinPaprika error %s: %s", path, e)
    return None

def list_new_coins(limit: int = 10) -> List[dict]:
    data = cp_get("/coins")
    if not data:
        return []
    # CoinPaprika marks very new assets with "is_new": True
    new = [c for c in data if c.get("is_new")]
    # Sort by first_data_at desc (most recent first)
    def ts(c):
        v = c.get("first_data_at") or c.get("last_data_at") or "1970-01-01T00:00:00Z"
        try:
            return datetime.fromisoformat(v.replace("Z","+00:00")).timestamp()
        except Exception:
            return 0
    new.sort(key=ts, reverse=True)
    return new[:limit]

def ticker_by_symbol(symbol: str) -> Optional[dict]:
    # Map SYMBOL -> coin id (first match)
    coins = cp_get("/coins")
    if not coins: return None
    sym = symbol.upper()
    cid = None
    for c in coins:
        if c.get("symbol","").upper() == sym:
            cid = c.get("id"); break
    if not cid: 
        return None
    t = cp_get(f"/tickers/{cid}")
    return t

def fmt_usd(x) -> str:
    try:
        v = float(x)
    except Exception:
        return "-"
    if v >= 1_000_000_000: return f"{v/1_000_000_000:.2f}B"
    if v >= 1_000_000:     return f"{v/1_000_000:.2f}M"
    if v >= 1_000:         return f"{v:,.0f}"
    if v >= 1:             return f"{v:.4f}"
    if v > 0:              return f"{v:.8f}".rstrip("0").rstrip(".")
    return "-"

def render_new_tokens(tr: Dict[str,str]) -> str:
    coins = list_new_coins(10)
    if not coins:
        return tr["nt_empty"]
    lines = [tr["nt_title"]]
    for c in coins:
        sym = c.get("symbol","?")
        name = c.get("name","?")
        dt  = (c.get("first_data_at") or "")[:10]
        lines.append(f"• {sym} — {name}  (since {dt})")
    lines.append("")
    lines.append(tr["nt_hint"])
    return "\n".join(lines)

def render_info_for(symbol: str, tr: Dict[str,str]) -> str:
    t = ticker_by_symbol(symbol)
    if not t:
        return tr["info_not_found"]
    sym = t.get("symbol", symbol.upper())
    name = t.get("name", "")
    price = t.get("quotes",{}).get("USD",{}).get("price")
    mcap  = t.get("quotes",{}).get("USD",{}).get("market_cap")
    vol   = t.get("quotes",{}).get("USD",{}).get("volume_24h")
    chg   = t.get("quotes",{}).get("USD",{}).get("percent_change_24h")
    lines = [
        tr["info_title"].format(symbol=sym, name=name),
        tr["info_price"].format(price=fmt_usd(price)),
        tr["info_mcap"].format(mcap=fmt_usd(mcap)),
        tr["info_vol"].format(vol=fmt_usd(vol)),
        tr["info_change"].format(chg=f"{chg:.2f}" if chg is not None else "-"),
        tr["info_note"]
    ]
    return "\n".join(lines)

# ----------------------- MENUS -----------------------

def main_kb(s: Dict[str,Any]) -> List[List[str]]:
    tr = LANGS[s["lang"]]
    auto = tr["auto_on"] if s["auto"] else tr["auto_off"]
    return [
        [tr["scan_now"], tr["top"]],
        [tr["change_pair"], tr["new_tokens"]],
        [auto],
        [tr["language"], tr["back"]],
    ]

def lang_kb() -> List[List[str]]:
    return [[LANGS["en"]["lang_en"], LANGS["ru"]["lang_ru"], LANGS["uz"]["lang_uz"]]]

def show_home(chat_id: int):
    s = st(chat_id); tr = T(chat_id)
    send(chat_id, tr["home_pair"].format(pair=s["pair"]), kb=main_kb(s))

# ----------------------- COMMANDS -----------------------

def do_scan(chat_id: int):
    s = st(chat_id); tr = T(chat_id)
    rows = fetch_all(s["pair"])
    text = render_table(s["pair"], rows, tr) if rows else tr["no_quotes"].format(pair=s["pair"])
    send(chat_id, text, kb=main_kb(s))

def do_change_pair(chat_id: int, txt: str = ""):
    s = st(chat_id); tr = T(chat_id)
    if not txt:
        s["awaiting"] = "pair"
        send(chat_id, tr["ask_pair"], kb=main_kb(s))
        return
    p = to_usdt_pair(txt)
    if not p:
        send(chat_id, tr["bad_pair"], kb=main_kb(s))
    else:
        s["pair"] = p
        s["awaiting"] = None
        send(chat_id, tr["pair_set"].format(pair=p), kb=main_kb(s))

def do_top(chat_id: int):
    s = st(chat_id); tr = T(chat_id)
    lines = []
    for pair in WATCHLIST:
        rows = fetch_all(pair)
        pct, bx, sx, bp, sp = best_spread(rows)
        if pct > 0:
            lines.append( (pct, pair, bx, sx, bp, sp) )
    lines.sort(reverse=True)
    if not lines:
        send(chat_id, tr["no_spreads"], kb=main_kb(s)); return
    lines = lines[:5]
    msg = tr["top_title"] + "\n"
    for i,(pct,pair,bx,sx,bp,sp) in enumerate(lines,1):
        msg += (f"\n<b>{i}) {pair}</b> — <b>{pct:.2f}%</b>\n"
                f"  Buy @ {bx} {fmt_price(bp)} | Sell @ {sx} {fmt_price(sp)}")
    send(chat_id, msg, kb=main_kb(s))

def toggle_auto(chat_id: int):
    s = st(chat_id); tr = T(chat_id)
    s["auto"] = not s["auto"]
    send(chat_id, tr["auto_now"].format(state=("ON" if s["auto"] else "OFF")), kb=main_kb(s))

def ask_language(chat_id: int):
    s = st(chat_id); tr = T(chat_id)
    s["awaiting"] = "lang"
    send(chat_id, tr["lang_pick"], kb=lang_kb())

def set_language_by_button(chat_id: int, text: str):
    s = st(chat_id)
    if text == LANGS["en"]["lang_en"]: s["lang"] = "en"
    elif text == LANGS["ru"]["lang_ru"]: s["lang"] = "ru"
    elif text == LANGS["uz"]["lang_uz"]: s["lang"] = "uz"
    s["awaiting"] = None
    show_home(chat_id)

def do_new_tokens(chat_id: int):
    s = st(chat_id); tr = T(chat_id)
    msg = render_new_tokens(tr)
    send(chat_id, msg, kb=main_kb(s))

# ----------------------- POLLER -----------------------

def handle_text(chat_id: int, text: str):
    s = st(chat_id); tr = T(chat_id)
    t = text.strip()
    u = t.upper()

    # language selection step
    if s.get("awaiting") == "lang":
        set_language_by_button(chat_id, t); return

    # pair typing step
    if s.get("awaiting") == "pair":
        do_change_pair(chat_id, t); return

    # commands by labels in current language
    if u in ("/START",):
        show_home(chat_id); return

    if t == tr["back"]:
        show_home(chat_id); return

    if t == tr["scan_now"]:
        do_scan(chat_id); return

    if t == tr["change_pair"]:
        do_change_pair(chat_id); return

    if t == tr["top"]:
        do_top(chat_id); return

    if t == tr["language"]:
        ask_language(chat_id); return

    if t == tr["new_tokens"]:
        do_new_tokens(chat_id); return

    if t in (tr["auto_on"], tr["auto_off"]):
        toggle_auto(chat_id); return

    # typed pair shortcut
    if t.lower().startswith("info "):
        sym = t.split(" ",1)[1].strip()
        send(chat_id, render_info_for(sym, tr), kb=main_kb(s)); return

    cand = to_usdt_pair(t)
    if cand:
        s["pair"] = cand
        s["awaiting"] = None
        send(chat_id, tr["pair_set"].format(pair=cand), kb=main_kb(s))
        return

    # fallback
    send(chat_id, tr["ask_pair"], kb=main_kb(s))

def poll_loop():
    log.info("Polling started")
    offset = 0
    while True:
        try:
            upd = get_updates(offset)
            if not upd or not upd.get("ok"):
                time.sleep(2); continue
            for u in upd.get("result", []):
                offset = max(offset, u["update_id"] + 1)
                msg = u.get("message") or {}
                chat = msg.get("chat", {})
                chat_id = chat.get("id")
                text = msg.get("text", "")
                if chat_id and isinstance(text, str) and text:
                    handle_text(chat_id, text)
        except Exception as e:
            log.warning("poll error: %s", e)
            time.sleep(2)

# ----------------------- AUTO WATCHER -----------------------
# Scans WATCHLIST and pushes a notification when a better opportunity
# appears (above threshold) that wasn't sent recently.

def autoscan_loop():
    while True:
        time.sleep(5)
        now = time.time()
        for chat_id, s in list(STATE.items()):
            if not s.get("auto"): 
                continue
            if now - s.get("last_scan", 0) < SCAN_PERIOD:
                continue

            s["last_scan"] = now
            tr = LANGS[s["lang"]]

            best: Tuple[float,str,str,str,float,float] = (0.0, "", "", "", 0.0, 0.0)
            best_rows: Optional[List[Tuple[str,float,float]]] = None

            for pair in WATCHLIST:
                rows = fetch_all(pair)
                pct, bx, sx, bp, sp = best_spread(rows)
                if pct > best[0]:
                    best = (pct, pair, bx, sx, bp, sp)
                    best_rows = rows

            pct, pair, bx, sx, bp, sp = best
            if pct < s.get("threshold", 0.1) or not best_rows:
                continue

            key = f"{pair}|{bx}|{sx}"
            if key == s.get("auto_last_key", ""):
                continue
            s["auto_last_key"] = key

            alert = tr["new_opp"].format(
                pair=pair, pct=pct, bx=bx, sx=sx,
                bp=fmt_price(bp), sp=fmt_price(sp)
            )
            send(chat_id, alert, kb=main_kb(s))
            send(chat_id, render_table(pair, best_rows, tr), kb=main_kb(s))

# ----------------------- KEEP-ALIVE (Replit) -----------------------

    app = Flask(__name__)

    @app.get("/")
    def ping():
        return "OK", 200

    def run_flask():
        port = int(os.getenv("PORT", 8080))
        app.run(host="0.0.0.0", port=port, debug=False)


# ----------------------- BOOT -----------------------

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    me = tg("getMe")
    log.info("Bot up as @%s", (me.get("result") or {}).get("username", "?"))
    threading.Thread(target=autoscan_loop, daemon=True).start()
    poll_loop()
