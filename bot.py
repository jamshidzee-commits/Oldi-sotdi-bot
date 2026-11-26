"""Oldi sotdi: kanal uchun e'lonlar boti (oldi-sotdi).

- Sotuvchi botda forma to'ldiradi (nom, toifa, narx, manzil, mo'ljal, rasm).
- Telefon raqami FAQAT Telegram'ning "kontakt yuborish" tugmasi orqali olinadi (qo'lda yozib bo'lmaydi).
- Har bir e'lon avval adminga (kanal egasiga) tasdiqlash uchun keladi.
- E'lon berish uchun foydalanuvchi kanalga NEED ta odam taklif qilishi kerak (shaxsiy havola orqali).
- "Sotildi" tugmasi: postdan telefon va manzil o'chadi.
"""
import os, re, json, time, html, base64, hashlib, requests
from cryptography.fernet import Fernet

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHANNEL = os.environ.get("CHANNEL_ID") or "@oldisotdichennel"
CHANNEL_LINK = "https://t.me/" + CHANNEL.lstrip("@") if CHANNEL.startswith("@") else ""
NEED = int(os.environ.get("INVITES_NEEDED") or 5)
DAILY_LIMIT = int(os.environ.get("DAILY_LIMIT") or 3)
MAX_PHOTOS = 5
RUN_SECONDS = int(os.environ.get("RUN_SECONDS") or 55 * 60)
STATE = os.environ.get("STATE_FILE") or "state.json"
TG = f"https://api.telegram.org/bot{TOKEN}/"
# Telefon raqami state.json'da faqat shifrlangan holda (tasdiqlashni kutayotganda) turadi.
FERNET = Fernet(base64.urlsafe_b64encode(hashlib.sha256(TOKEN.encode()).digest()))

CATS = {  # kalit: (emoji, uz, ru, hashtag)
    "auto": ("🚗", "Avto", "Авто", "avto"),
    "estate": ("🏠", "Ko'chmas mulk", "Недвижимость", "kochmas_mulk"),
    "electro": ("📱", "Elektronika", "Электроника", "elektronika"),
    "clothes": ("👕", "Kiyim-kechak", "Одежда", "kiyim"),
    "home": ("🛋", "Uy-ro'zg'or", "Дом и быт", "uy_rozgor"),
    "other": ("📦", "Boshqa", "Другое", "boshqa"),
}

T = {
    "uz": {
        "lang_prompt": "Tilni tanlang / Выберите язык",
        "welcome": "Assalomu alaykum! 👋\nBu yerda e'lon berishingiz mumkin. Pastdagi tugmalardan foydalaning.",
        "btn_new": "➕ E'lon berish", "btn_my": "📋 E'lonlarim", "btn_link": "🔗 Taklif havolam", "btn_lang": "🌐 Til / Язык",
        "btn_cancel": "❌ Bekor qilish", "btn_done": "✅ Tayyor", "btn_phone": "📞 Raqamni yuborish",
        "locked": "🔒 E'lon berish uchun kanalga {n} ta odamni taklif qiling.\n\nSizning havolangiz:\n{link}\n\nHozircha: {k}/{n}\nOdamlar shu havola orqali kanalga qo'shilishi va kanalda qolishi kerak.",
        "unlocked": "🎉 Tabriklaymiz! {n} ta odam qo'shildi. Endi e'lon berishingiz mumkin.",
        "progress": "👥 Yangi a'zo qo'shildi: {k}/{n}",
        "link_msg": "Sizning taklif havolangiz:\n{link}\n\nQo'shilganlar: {k}/{n}",
        "ask_title": "Nima sotmoqchisiz? Qisqa nom yozing (masalan: iPhone 13, 128 GB).",
        "ask_cat": "Toifani tanlang:",
        "ask_price": "Narxini yozing (masalan: 5 000 000 so'm yoki kelishiladi).",
        "ask_addr": "Manzilni yozing (shahar, tuman, ko'cha).",
        "ask_land": "Mo'ljalni yozing (masalan: bozor yonida).",
        "ask_photo": "Rasm yoki video yuboring (jami {m} tagacha). Tugagach «✅ Tayyor» tugmasini bosing.",
        "photo_ok": "Qabul qilindi: {k}/{m}",
        "need_photo": "Kamida 1 ta rasm yoki video yuboring.",
        "ask_phone": "Oxirgi qadam: telefon raqamingizni Telegram orqali tasdiqlang. Pastdagi tugmani bosing. Qo'lda yozilgan raqam qabul qilinmaydi.",
        "bad_contact": "Faqat o'zingizning raqamingizni yuborishingiz mumkin. Pastdagi tugmani bosing.",
        "too_long": "Juda uzun matn. Qisqaroq yozing (eng ko'pi {m} belgi).",
        "text_only": "Iltimos, matn yozing.",
        "sent": "✅ E'loningiz tekshirishga yuborildi. Tasdiqlangach kanalda chiqadi.",
        "limit": "24 soat ichida {n} tadan ortiq e'lon berib bo'lmaydi. Keyinroq urinib ko'ring.",
        "approved": "✅ E'loningiz kanalga joylandi:\n{url}",
        "rejected": "❌ E'loningiz rad etildi.\nSabab: {reason}",
        "my_empty": "Sizda faol e'lonlar yo'q.",
        "my_title": "Faol e'lonlaringiz. Sotilgan bo'lsa tugmani bosing:",
        "sold_btn": "✅ Sotildi: {t}",
        "sold_ok": "✅ E'lon «sotildi» deb belgilandi, aloqa ma'lumotlari o'chirildi.",
        "cancelled": "Bekor qilindi.",
        "lang_set": "Til o'rnatildi.",
        "sold_label": "✅ SOTILDI",
    },
    "ru": {
        "lang_prompt": "Tilni tanlang / Выберите язык",
        "welcome": "Здравствуйте! 👋\nЗдесь можно подать объявление. Пользуйтесь кнопками ниже.",
        "btn_new": "➕ Подать объявление", "btn_my": "📋 Мои объявления", "btn_link": "🔗 Моя ссылка", "btn_lang": "🌐 Til / Язык",
        "btn_cancel": "❌ Отмена", "btn_done": "✅ Готово", "btn_phone": "📞 Отправить номер",
        "locked": "🔒 Чтобы подать объявление, пригласите в канал {n} человек.\n\nВаша ссылка:\n{link}\n\nПока: {k}/{n}\nЛюди должны вступить в канал по этой ссылке и остаться в нём.",
        "unlocked": "🎉 Поздравляем! Вступили {n} человек. Теперь можно подавать объявления.",
        "progress": "👥 Новый участник: {k}/{n}",
        "link_msg": "Ваша ссылка-приглашение:\n{link}\n\nВступили: {k}/{n}",
        "ask_title": "Что продаёте? Напишите короткое название (например: iPhone 13, 128 GB).",
        "ask_cat": "Выберите категорию:",
        "ask_price": "Напишите цену (например: 5 000 000 сум или договорная).",
        "ask_addr": "Напишите адрес (город, район, улица).",
        "ask_land": "Напишите ориентир (например: возле рынка).",
        "ask_photo": "Отправьте фото или видео (всего до {m}). Когда закончите, нажмите «✅ Готово».",
        "photo_ok": "Принято: {k}/{m}",
        "need_photo": "Отправьте хотя бы 1 фото или видео.",
        "ask_phone": "Последний шаг: подтвердите номер телефона через Telegram. Нажмите кнопку ниже. Номер, написанный вручную, не принимается.",
        "bad_contact": "Можно отправить только свой номер. Нажмите кнопку ниже.",
        "too_long": "Слишком длинный текст. Напишите короче (не больше {m} символов).",
        "text_only": "Пожалуйста, напишите текстом.",
        "sent": "✅ Ваше объявление отправлено на проверку. После одобрения оно появится в канале.",
        "limit": "Нельзя подавать больше {n} объявлений за 24 часа. Попробуйте позже.",
        "approved": "✅ Ваше объявление опубликовано в канале:\n{url}",
        "rejected": "❌ Ваше объявление отклонено.\nПричина: {reason}",
        "my_empty": "У вас нет активных объявлений.",
        "my_title": "Ваши активные объявления. Если продано, нажмите кнопку:",
        "sold_btn": "✅ Продано: {t}",
        "sold_ok": "✅ Объявление отмечено как «продано», контакты удалены.",
        "cancelled": "Отменено.",
        "lang_set": "Язык установлен.",
        "sold_label": "✅ ПРОДАНО",
    },
}


# ---------------------------------------------------------------- Telegram API
def api(method, **params):
    for _ in range(3):
        try:
            r = requests.post(TG + method, json=params, timeout=60)
            d = r.json()
        except Exception as e:  # tarmoq xatosi
            print("tarmoq xato", method, e)
            time.sleep(2)
            continue
        if d.get("ok"):
            return d["result"]
        if d.get("error_code") == 429:
            time.sleep(int(d.get("parameters", {}).get("retry_after", 3)) + 1)
            continue
        if d.get("error_code") == 409:  # boshqa nusxa ishlayapti
            time.sleep(5)
            continue
        print("API xato", method, d.get("description"))
        return None
    return None


# ---------------------------------------------------------------- holat
def new_state():
    return {"offset": 0, "next_id": 1, "admin": None, "users": {}, "ads": {}, "drafts": {}, "links": {}, "admin_wait": None}


def load():
    try:
        s = json.load(open(STATE, encoding="utf-8"))
    except Exception:
        s = {}
    base = new_state()
    base.update(s)
    return base


def save():
    tmp = STATE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(S, f, ensure_ascii=False, indent=1)
    os.replace(tmp, STATE)


S = load()


def user(uid):
    u = S["users"].setdefault(str(uid), {"lang": None, "link": None, "invited": [], "unlocked": False, "ads_ts": []})
    return u


def tr(uid, key, **kw):
    lang = user(uid).get("lang") or "uz"
    return T[lang][key].format(**kw) if kw else T[lang][key]


def e(x):
    return html.escape(str(x), quote=False)


def is_admin(uid):
    return S.get("admin") and str(uid) == str(S["admin"])


def ensure_admin():
    env = os.environ.get("ADMIN_CHAT_ID")
    if env:
        S["admin"] = str(env)
        return
    res = api("getChatAdministrators", chat_id=CHANNEL) or []
    for a in res:
        if a.get("status") == "creator":
            S["admin"] = str(a["user"]["id"])
            return


# ---------------------------------------------------------------- klaviaturalar
def menu_kb(uid):
    return {"keyboard": [[{"text": tr(uid, "btn_new")}], [{"text": tr(uid, "btn_my")}, {"text": tr(uid, "btn_link")}],
                         [{"text": tr(uid, "btn_lang")}]], "resize_keyboard": True}


def cancel_kb(uid):
    return {"keyboard": [[{"text": tr(uid, "btn_cancel")}]], "resize_keyboard": True}


def photo_kb(uid):
    return {"keyboard": [[{"text": tr(uid, "btn_done")}], [{"text": tr(uid, "btn_cancel")}]], "resize_keyboard": True}


def phone_kb(uid):
    return {"keyboard": [[{"text": tr(uid, "btn_phone"), "request_contact": True}], [{"text": tr(uid, "btn_cancel")}]],
            "resize_keyboard": True}


def say(uid, key, kb=None, **kw):
    p = {"chat_id": int(uid), "text": tr(uid, key, **kw), "disable_web_page_preview": True}
    if kb:
        p["reply_markup"] = kb
    return api("sendMessage", **p)


def all_labels(key):
    return {T["uz"][key], T["ru"][key]}


# ---------------------------------------------------------------- taklif (5 kishi)
def make_link(uid):
    u = user(uid)
    if not u["link"]:
        r = api("createChatInviteLink", chat_id=CHANNEL, name=f"u{uid}"[:32])
        if r and r.get("invite_link"):
            u["link"] = r["invite_link"]
            S["links"][u["link"]] = str(uid)
    return u["link"] or CHANNEL_LINK


def valid_invited(uid):
    ok = []
    for v in user(uid)["invited"]:
        r = api("getChatMember", chat_id=CHANNEL, user_id=int(v))
        if r and r.get("status") in ("member", "administrator", "creator"):
            ok.append(v)
    return ok


def can_post(uid):
    """Foydalanuvchiga e'lon berish ochiqmi? Admin uchun doim ochiq."""
    u = user(uid)
    if is_admin(uid) or u["unlocked"]:
        return True
    if len(valid_invited(uid)) >= NEED:
        u["unlocked"] = True
        return True
    return False


def on_chat_member(cm):
    chat = cm.get("chat", {})
    if ("@" + (chat.get("username") or "")).lower() != CHANNEL.lower():
        return
    old, new = cm["old_chat_member"]["status"], cm["new_chat_member"]["status"]
    joined = cm["new_chat_member"]["user"]
    if new != "member" or old not in ("left", "kicked") or joined.get("is_bot"):
        return
    link = (cm.get("invite_link") or {}).get("invite_link")
    inviter = S["links"].get(link or "")
    if not inviter or inviter == str(joined["id"]):
        return
    u = user(inviter)
    if str(joined["id"]) not in u["invited"]:
        u["invited"].append(str(joined["id"]))
    if u["unlocked"]:
        return
    k = len(valid_invited(inviter))
    if k >= NEED:
        u["unlocked"] = True
        say(inviter, "unlocked", kb=menu_kb(inviter), n=NEED)
    else:
        say(inviter, "progress", k=k, n=NEED)


# ---------------------------------------------------------------- e'lon matni
def clean(s, n):
    return re.sub(r"\s+", " ", s).strip()[:n]


def build_caption(ad, phone=None, sold=False):
    emoji, _, _, tag = CATS[ad["cat"]]
    title = e(ad["title"])
    foot = f'👉 <a href="{CHANNEL_LINK}">OLDI SOTDI</a> 👈' if CHANNEL_LINK else "👉 OLDI SOTDI 👈"
    if sold:
        return f"{T['uz']['sold_label']} / {T['ru']['sold_label']}\n\n{emoji} <s>{title}</s>\n💰 <s>{e(ad['price'])}</s>\n\n#{tag}\n{foot}"
    lines = [f"{emoji} <b>{title}</b>", "", f"💰 Narxi: {e(ad['price'])}", f"📍 Manzil: {e(ad['addr'])}",
             f"🧭 Mo'ljal: {e(ad['land'])}", f"📞 Tel: {e(phone)}"]
    if ad.get("uname"):
        lines.append(f"✍️ Telegram: @{e(ad['uname'])}")
    lines += ["", f"#{tag}", foot]
    return "\n".join(lines)


def norm_phone(p):
    p = re.sub(r"[^\d+]", "", p or "")
    return p if p.startswith("+") else "+" + p


# ---------------------------------------------------------------- forma
def start_draft(uid):
    S["drafts"][str(uid)] = {"step": "title", "photos": []}
    say(uid, "ask_title", kb=cancel_kb(uid))


def cat_kb(uid):
    lang = user(uid).get("lang") or "uz"
    idx = 1 if lang == "uz" else 2
    rows, row = [], []
    for k, v in CATS.items():
        row.append({"text": f"{v[0]} {v[idx]}", "callback_data": f"ct:{k}"})
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return {"inline_keyboard": rows}


def cancel(uid):
    S["drafts"].pop(str(uid), None)
    say(uid, "cancelled", kb=menu_kb(uid))


def draft_message(uid, m):
    d = S["drafts"][str(uid)]
    step = d["step"]
    text = (m.get("text") or "").strip()
    if step in ("title", "price", "addr", "land"):
        if not text:
            return say(uid, "text_only")
        limit = {"title": 80, "price": 40, "addr": 120, "land": 120}[step]
        if len(text) > limit:
            return say(uid, "too_long", m=limit)
        d[step] = clean(text, limit)
        if step == "title":
            d["step"] = "cat"
            return say(uid, "ask_cat", kb=cat_kb(uid))
        if step == "price":
            d["step"] = "addr"
            return say(uid, "ask_addr")
        if step == "addr":
            d["step"] = "land"
            return say(uid, "ask_land")
        d["step"] = "photos"
        return say(uid, "ask_photo", kb=photo_kb(uid), m=MAX_PHOTOS)
    if step == "cat":
        return say(uid, "ask_cat", kb=cat_kb(uid))
    if step == "photos":
        if m.get("photo") or m.get("video"):
            if len(d["photos"]) < MAX_PHOTOS:
                d["photos"].append({"t": "photo", "f": m["photo"][-1]["file_id"]} if m.get("photo")
                                   else {"t": "video", "f": m["video"]["file_id"]})
            return say(uid, "photo_ok", k=len(d["photos"]), m=MAX_PHOTOS)
        if text in all_labels("btn_done"):
            if not d["photos"]:
                return say(uid, "need_photo")
            d["step"] = "phone"
            return say(uid, "ask_phone", kb=phone_kb(uid))
        return say(uid, "ask_photo", kb=photo_kb(uid), m=MAX_PHOTOS)
    if step == "phone":
        c = m.get("contact")
        if not c or str(c.get("user_id")) != str(m["from"]["id"]):
            return say(uid, "bad_contact", kb=phone_kb(uid))
        return submit_ad(uid, m, norm_phone(c["phone_number"]))


def submit_ad(uid, m, phone):
    u = user(uid)
    now = time.time()
    u["ads_ts"] = [t for t in u["ads_ts"] if now - t < 86400]
    if not is_admin(uid) and len(u["ads_ts"]) >= DAILY_LIMIT:
        S["drafts"].pop(str(uid), None)
        return say(uid, "limit", kb=menu_kb(uid), n=DAILY_LIMIT)
    d = S["drafts"].pop(str(uid))
    aid = str(S["next_id"])
    S["next_id"] += 1
    ad = {"uid": str(uid), "uname": (m["from"].get("username") or ""), "title": d["title"], "cat": d["cat"], "price": d["price"],
          "addr": d["addr"], "land": d["land"], "photos": d["photos"], "status": "pending", "ts": int(now),
          "phone_enc": FERNET.encrypt(phone.encode()).decode(), "chan_ids": [], "group": None}
    S["ads"][aid] = ad
    u["ads_ts"].append(now)
    say(uid, "sent", kb=menu_kb(uid))
    send_to_admin(aid, ad, phone, m["from"])


def send_media(chat, items, caption=None):
    """Bitta fayl bo'lsa sendPhoto/sendVideo, bir nechta bo'lsa albom. Xabar id'lari ro'yxatini qaytaradi."""
    kw = {"caption": caption, "parse_mode": "HTML"} if caption else {}
    if len(items) == 1:
        x = items[0]
        r = api("sendPhoto" if x["t"] == "photo" else "sendVideo", chat_id=chat, **{x["t"]: x["f"]}, **kw)
        return [r["message_id"]] if r else []
    media = [{"type": x["t"], "media": x["f"]} for x in items]
    media[0].update(kw)
    r = api("sendMediaGroup", chat_id=chat, media=media)
    return [x["message_id"] for x in r] if r else []


def send_to_admin(aid, ad, phone, frm):
    adm = S.get("admin")
    if not adm:
        print("admin topilmadi")
        return
    send_media(int(adm), ad["photos"])
    who = f'<a href="tg://user?id={frm["id"]}">{e(frm.get("first_name") or "user")}</a>'
    if frm.get("username"):
        who += f" (@{e(frm['username'])})"
    body = f"🆕 Новое объявление #{aid}\nАвтор: {who}\n\n{build_caption(ad, phone)}"
    api("sendMessage", chat_id=int(adm), text=body, parse_mode="HTML", disable_web_page_preview=True,
        reply_markup={"inline_keyboard": [[{"text": "✅ Одобрить", "callback_data": f"ap:{aid}"},
                                            {"text": "❌ Отклонить", "callback_data": f"rj:{aid}"}]]})


# ---------------------------------------------------------------- admin: tasdiqlash / rad etish
def publish(aid):
    ad = S["ads"].get(aid)
    if not ad or ad["status"] != "pending":
        return False
    phone = FERNET.decrypt(ad["phone_enc"].encode()).decode()
    cap = build_caption(ad, phone)
    ids = send_media(CHANNEL, ad["photos"], cap)
    if not ids:
        return False
    ad["chan_ids"] = ids
    ad["status"] = "live"
    ad.pop("phone_enc", None)  # telefon endi state'da saqlanmaydi
    if CHANNEL.startswith("@"):
        url = f"{CHANNEL_LINK}/{ids[0]}"
        say(ad["uid"], "approved", url=url)
    return True


def reject(aid, reason):
    ad = S["ads"].get(aid)
    if not ad or ad["status"] != "pending":
        return
    ad["status"] = "rejected"
    ad.pop("phone_enc", None)
    say(ad["uid"], "rejected", reason=reason or "-")


def mark_sold(aid, uid):
    ad = S["ads"].get(aid)
    if not ad or ad["uid"] != str(uid) or ad["status"] != "live":
        return False
    cap = build_caption(ad, sold=True)
    api("editMessageCaption", chat_id=CHANNEL, message_id=ad["chan_ids"][0], caption=cap, parse_mode="HTML",
        reply_markup={"inline_keyboard": []})
    g = ad.get("group")  # muhokama guruhidagi nusxa (imkon bo'lsa)
    if g:
        api("editMessageCaption", chat_id=g["chat"], message_id=g["msg"], caption=cap, parse_mode="HTML")
    ad["status"] = "sold"
    return True


def on_callback(cb):
    uid = str(cb["from"]["id"])
    data = cb.get("data") or ""
    msg = cb.get("message") or {}
    api("answerCallbackQuery", callback_query_id=cb["id"])
    if data.startswith("lg:"):
        user(uid)["lang"] = data[3:] if data[3:] in T else "uz"
        say(uid, "lang_set", kb=menu_kb(uid))
        say(uid, "welcome", kb=menu_kb(uid))
    elif data.startswith("ct:"):
        d = S["drafts"].get(uid)
        if d and d["step"] == "cat" and data[3:] in CATS:
            d["cat"] = data[3:]
            d["step"] = "price"
            say(uid, "ask_price")
    elif data.startswith("ap:") and is_admin(uid):
        ok = publish(data[3:])
        api("editMessageReplyMarkup", chat_id=msg["chat"]["id"], message_id=msg["message_id"],
            reply_markup={"inline_keyboard": [[{"text": "✅ Опубликовано" if ok else "⚠️ Не удалось / уже обработано", "callback_data": "noop"}]]})
    elif data.startswith("rj:") and is_admin(uid):
        ad = S["ads"].get(data[3:])
        if ad and ad["status"] == "pending":
            S["admin_wait"] = data[3:]
            api("sendMessage", chat_id=int(uid), text="Укажите причину отказа одним сообщением (или отправьте «-»):")
            api("editMessageReplyMarkup", chat_id=msg["chat"]["id"], message_id=msg["message_id"],
                reply_markup={"inline_keyboard": [[{"text": "❌ Отклоняется…", "callback_data": "noop"}]]})
    elif data.startswith("sd:"):
        if mark_sold(data[3:], uid):
            say(uid, "sold_ok", kb=menu_kb(uid))


# ---------------------------------------------------------------- xabarlar
def show_my(uid):
    mine = [(i, a) for i, a in S["ads"].items() if a["uid"] == str(uid) and a["status"] == "live"]
    if not mine:
        return say(uid, "my_empty", kb=menu_kb(uid))
    rows = [[{"text": tr(uid, "sold_btn", t=a["title"][:25]), "callback_data": f"sd:{i}"}] for i, a in mine[-10:]]
    say(uid, "my_title", kb={"inline_keyboard": rows})


def on_message(m):
    chat = m.get("chat", {})
    if chat.get("type") != "private":
        # muhokama guruhidagi avtomatik nusxani eslab qolamiz (sotildi bo'lsa tahrirlash uchun)
        if m.get("is_automatic_forward") and m.get("forward_from_message_id"):
            for ad in S["ads"].values():
                if ad.get("chan_ids") and ad["chan_ids"][0] == m["forward_from_message_id"]:
                    ad["group"] = {"chat": chat["id"], "msg": m["message_id"]}
        return
    uid = str(m["from"]["id"])
    text = (m.get("text") or "").strip()
    u = user(uid)
    if text.startswith("/start"):
        if not u["lang"]:
            return api("sendMessage", chat_id=int(uid), text=T["uz"]["lang_prompt"],
                       reply_markup={"inline_keyboard": [[{"text": "🇺🇿 O'zbekcha", "callback_data": "lg:uz"},
                                                           {"text": "🇷🇺 Русский", "callback_data": "lg:ru"}]]})
        S["drafts"].pop(uid, None)
        return say(uid, "welcome", kb=menu_kb(uid))
    # admin rad etish sababini yozmoqda
    if is_admin(uid) and S.get("admin_wait") and text:
        aid, S["admin_wait"] = S["admin_wait"], None
        reject(aid, None if text == "-" else text)
        return api("sendMessage", chat_id=int(uid), text=f"❌ Объявление #{aid} отклонено.")
    if not u["lang"]:
        return api("sendMessage", chat_id=int(uid), text=T["uz"]["lang_prompt"],
                   reply_markup={"inline_keyboard": [[{"text": "🇺🇿 O'zbekcha", "callback_data": "lg:uz"},
                                                       {"text": "🇷🇺 Русский", "callback_data": "lg:ru"}]]})
    if text in all_labels("btn_cancel") or text == "/cancel":
        return cancel(uid)
    if uid in S["drafts"]:
        return draft_message(uid, m)
    if text in all_labels("btn_new"):
        if not can_post(uid):
            k = len(valid_invited(uid))
            return say(uid, "locked", kb=menu_kb(uid), n=NEED, k=k, link=make_link(uid))
        return start_draft(uid)
    if text in all_labels("btn_my"):
        return show_my(uid)
    if text in all_labels("btn_link"):
        return say(uid, "link_msg", kb=menu_kb(uid), link=make_link(uid), k=len(valid_invited(uid)), n=NEED)
    if text in all_labels("btn_lang"):
        u["lang"] = None
        return api("sendMessage", chat_id=int(uid), text=T["uz"]["lang_prompt"],
                   reply_markup={"inline_keyboard": [[{"text": "🇺🇿 O'zbekcha", "callback_data": "lg:uz"},
                                                       {"text": "🇷🇺 Русский", "callback_data": "lg:ru"}]]})
    say(uid, "welcome", kb=menu_kb(uid))


def handle(upd):
    if "message" in upd:
        on_message(upd["message"])
    elif "callback_query" in upd:
        on_callback(upd["callback_query"])
    elif "chat_member" in upd:
        on_chat_member(upd["chat_member"])


def main():
    api("deleteWebhook")
    ensure_admin()
    save()
    print("Oldi sotdi bot ishga tushdi. Admin:", S.get("admin"))
    end = time.time() + RUN_SECONDS
    while time.time() < end:
        wait = int(min(25, max(1, end - time.time())))
        ups = api("getUpdates", offset=S["offset"], timeout=wait,
                  allowed_updates=["message", "callback_query", "chat_member"])
        if ups is None:
            time.sleep(3)
            continue
        for upd in ups:
            try:
                handle(upd)
            except Exception as ex:
                print("xato:", ex)
            S["offset"] = upd["update_id"] + 1
        if ups:
            save()
    save()


if __name__ == "__main__":
    main()
