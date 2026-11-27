"""Testry kontent boti.

GitHub Actions har 10 daqiqada ishga tushiradi. Har safar:
  1. Telegram'dan yangi xabarlarni o'qiydi (Tasdiqlash / Rad etish tugmalari, izohlar, /start).
  2. queue/ dagi yangi postlarni adminga ko'rib chiqish uchun yuboradi.
  3. Tasdiqlangan va vaqti kelgan postlarni kanalga chiqaradi.
Holat state/ papkasida saqlanadi va Actions uni omborga qaytarib yozadi.

Post tuzilmasi: queue/<post_id>/post.json
{
  "platform": "telegram" | "instagram",
  "scheduled_at": "2026-12-01T09:00",      # Toshkent vaqti
  "type": "text" | "photo" | "album" | "video" | "poll",
  "text": "...",                            # post matni / caption
  "media": ["1.png", "2.png"],              # shu papkadagi fayllar
  "poll": {"question": "...", "options": ["...", "..."]}
}
"""
import datetime as dt
import json
import os
import pathlib
import sys

import requests

ROOT = pathlib.Path(__file__).resolve().parent.parent
QUEUE = ROOT / "queue"
STATE_DIR = ROOT / "state"
STATE_FILE = STATE_DIR / "status.json"
CONFIG = json.loads((ROOT / "bot" / "config.json").read_text(encoding="utf-8"))

TOKEN = os.environ.get("TG_BOT_TOKEN", "").strip()
API = f"https://api.telegram.org/bot{TOKEN}"
TZ = dt.timezone(dt.timedelta(hours=5))  # Asia/Tashkent

STATUS_UZ = {
    "review": "Tasdiqlashda",
    "approved": "Tasdiqlandi",
    "rejected": "Rad etildi",
    "published": "Chop etildi",
    "waiting_instagram": "Instagram ulanishini kutmoqda",
    "error": "Xato",
}


def now():
    return dt.datetime.now(TZ)


def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"offset": 0, "admin_chat_id": None, "posts": {}}


def save_state(state):
    STATE_DIR.mkdir(exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def tg(method, files=None, **params):
    for k, v in list(params.items()):
        if isinstance(v, (dict, list)):
            params[k] = json.dumps(v, ensure_ascii=False)
    r = requests.post(f"{API}/{method}", data=params, files=files, timeout=60)
    data = r.json()
    if not data.get("ok"):
        raise RuntimeError(f"{method}: {data.get('description')}")
    return data["result"]


def admin_id(state):
    return os.environ.get("ADMIN_CHAT_ID", "").strip() or state.get("admin_chat_id")


# ---------- yuborish (adminga ham, kanalga ham bir xil) ----------

def send_post(chat_id, post, folder, caption_extra="", reply_markup=None):
    """Postni chat_id ga yuboradi. Oxirgi yuborilgan xabar id sini qaytaradi."""
    text = post.get("text", "")
    if caption_extra:
        text = f"{caption_extra}\n\n{text}" if text else caption_extra
    kind = post.get("type", "text")
    media = [folder / m for m in post.get("media", [])]
    extra = {"reply_markup": reply_markup} if reply_markup else {}

    if kind == "poll":
        p = post["poll"]
        if caption_extra:
            tg("sendMessage", chat_id=chat_id, text=caption_extra)
        msg = tg("sendPoll", chat_id=chat_id, question=p["question"], options=p["options"],
                 is_anonymous=True, **extra)
        return msg["message_id"]

    if kind == "photo":
        with open(media[0], "rb") as f:
            msg = tg("sendPhoto", files={"photo": f}, chat_id=chat_id, caption=text[:1024],
                     parse_mode="HTML", **extra)
        if len(text) > 1024:
            msg = tg("sendMessage", chat_id=chat_id, text=text[1024:], parse_mode="HTML")
        return msg["message_id"]

    if kind == "video":
        with open(media[0], "rb") as f:
            msg = tg("sendVideo", files={"video": f}, chat_id=chat_id, caption=text[:1024],
                     parse_mode="HTML", supports_streaming=True, **extra)
        return msg["message_id"]

    if kind == "album":
        files, group = {}, []
        for i, m in enumerate(media[:10]):
            key = f"f{i}"
            files[key] = open(m, "rb")
            item = {"type": "video" if m.suffix == ".mp4" else "photo", "media": f"attach://{key}"}
            if i == 0:
                item["caption"] = text[:1024]
                item["parse_mode"] = "HTML"
            group.append(item)
        try:
            msgs = tg("sendMediaGroup", files=files, chat_id=chat_id, media=group)
        finally:
            for f in files.values():
                f.close()
        last = msgs[-1]["message_id"]
        if reply_markup:  # albomga tugma biriktirib bo'lmaydi — alohida xabar
            last = tg("sendMessage", chat_id=chat_id, text="Shu postni tasdiqlaysizmi?",
                      reply_markup=reply_markup)["message_id"]
        return last

    msg = tg("sendMessage", chat_id=chat_id, text=text, parse_mode="HTML",
             disable_web_page_preview=True, **extra)
    return msg["message_id"]


def review_keyboard(post_id):
    return {"inline_keyboard": [[
        {"text": "✅ Tasdiqlash", "callback_data": f"ok:{post_id}"},
        {"text": "❌ Rad etish", "callback_data": f"no:{post_id}"},
    ]]}


# ---------- 1. yangi xabarlarni o'qish ----------

def handle_updates(state):
    updates = tg("getUpdates", offset=state.get("offset", 0), timeout=0,
                 allowed_updates=["message", "callback_query"])
    admin = admin_id(state)
    for u in updates:
        state["offset"] = u["update_id"] + 1

        if "callback_query" in u:
            cq = u["callback_query"]
            if str(cq["from"]["id"]) != str(admin):
                tg("answerCallbackQuery", callback_query_id=cq["id"], text="Ruxsat yo'q")
                continue
            action, post_id = cq["data"].split(":", 1)
            info = state["posts"].setdefault(post_id, {})
            if action == "ok":
                info["status"] = "approved"
                info["approved_at"] = now().isoformat(timespec="minutes")
                tg("answerCallbackQuery", callback_query_id=cq["id"], text="Tasdiqlandi ✅")
                tg("sendMessage", chat_id=admin,
                   text=f"✅ Tasdiqlandi: {post_id}\nBelgilangan vaqtda chiqadi: {info.get('scheduled_at', '')}")
            else:
                info["status"] = "rejected"
                tg("answerCallbackQuery", callback_query_id=cq["id"], text="Rad etildi")
                m = tg("sendMessage", chat_id=admin,
                       text=f"❌ Rad etildi: {post_id}\nNimani o'zgartiray? Shu xabarga javob (reply) qilib yozing.",
                       reply_markup={"force_reply": True})
                info["feedback_prompt_id"] = m["message_id"]
            continue

        msg = u.get("message")
        if not msg:
            continue
        chat_id = msg["chat"]["id"]
        text = msg.get("text", "")

        if text.startswith("/start"):
            if not admin:
                state["admin_chat_id"] = chat_id
                admin = chat_id
                tg("sendMessage", chat_id=chat_id,
                   text="Salom! Siz Testry kontent botining admini sifatida belgilandingiz. "
                        "Har kuni tayyor postlar shu yerga tasdiqlash uchun keladi.")
            elif str(chat_id) == str(admin):
                tg("sendMessage", chat_id=chat_id, text="Bot ishlayapti. Yangi postlar shu yerga keladi.")
            continue

        if str(chat_id) != str(admin):
            continue

        # Rad etilgan postga izoh (reply orqali)
        reply_to = (msg.get("reply_to_message") or {}).get("message_id")
        target = None
        for pid, info in state["posts"].items():
            if reply_to and reply_to in (info.get("feedback_prompt_id"), info.get("review_message_id")):
                target = pid
        if target:
            state["posts"][target].setdefault("feedback", []).append(text)
            tg("sendMessage", chat_id=chat_id,
               text=f"📝 Izoh saqlandi ({target}). Keyingi tayyorlashda hisobga olaman.")
        elif text == "/holat":
            send_status(state, chat_id)


def send_status(state, chat_id):
    lines = []
    for pid, info in sorted(state["posts"].items()):
        lines.append(f"{pid} — {STATUS_UZ.get(info.get('status'), info.get('status'))}")
    tg("sendMessage", chat_id=chat_id, text="\n".join(lines[-40:]) or "Navbat bo'sh.")


# ---------- 2. yangi postlarni tasdiqqa yuborish ----------

def send_new_for_review(state):
    admin = admin_id(state)
    if not admin:
        return
    for folder in sorted(p for p in QUEUE.glob("*") if (p / "post.json").exists()):
        post_id = folder.name
        info = state["posts"].get(post_id, {})
        post = json.loads((folder / "post.json").read_text(encoding="utf-8"))
        version = post.get("version", 1)
        if info.get("status") in ("review", "approved", "published") and info.get("version") == version:
            continue
        if info.get("status") == "rejected" and info.get("version") == version:
            continue  # yangi versiya kelishini kutamiz
        when = post.get("scheduled_at", "")
        head = (f"🆕 Tasdiqlash uchun: {post_id}\n"
                f"📍 {post.get('platform', '').capitalize()} · {post.get('format', post.get('type'))} · {when.replace('T', ' ')}")
        try:
            mid = send_post(admin, post, folder, caption_extra=head, reply_markup=review_keyboard(post_id))
            state["posts"][post_id] = {"status": "review", "version": version, "scheduled_at": when,
                                       "platform": post.get("platform"), "review_message_id": mid,
                                       "feedback": info.get("feedback", [])}
        except Exception as e:  # noqa: BLE001
            state["posts"][post_id] = {**info, "status": "error", "error": str(e), "version": version}
            tg("sendMessage", chat_id=admin, text=f"⚠️ {post_id} ni yuborishda xato: {e}")


# ---------- 3. vaqti kelgan postlarni chiqarish ----------

def publish_due(state):
    admin = admin_id(state)
    for post_id, info in state["posts"].items():
        if info.get("status") not in ("approved", "waiting_instagram"):
            continue
        when = dt.datetime.fromisoformat(info["scheduled_at"]).replace(tzinfo=TZ)
        if when > now():
            continue
        folder = QUEUE / post_id
        post = json.loads((folder / "post.json").read_text(encoding="utf-8"))
        try:
            if post.get("platform") == "instagram":
                if not os.environ.get("IG_ACCESS_TOKEN"):
                    info["status"] = "waiting_instagram"
                    continue
                import instagram  # noqa: PLC0415
                instagram.publish(post, folder)
            else:
                send_post(CONFIG["telegram_channel"], post, folder)
            info["status"] = "published"
            info["published_at"] = now().isoformat(timespec="minutes")
            if admin:
                tg("sendMessage", chat_id=admin, text=f"📤 Chop etildi: {post_id}")
        except Exception as e:  # noqa: BLE001
            info["status"] = "error"
            info["error"] = str(e)
            if admin:
                tg("sendMessage", chat_id=admin, text=f"⚠️ {post_id} ni chiqarishda xato: {e}")


def main():
    if not TOKEN:
        print("TG_BOT_TOKEN topilmadi — GitHub Secrets'ga qo'shing.")
        sys.exit(0)
    state = load_state()
    handle_updates(state)
    send_new_for_review(state)
    publish_due(state)
    save_state(state)


if __name__ == "__main__":
    main()
