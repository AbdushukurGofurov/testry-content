# Testry kontent ombori — Claude uchun yo'riqnoma

Bu ombor Testry.uz (yoshlarga kasb tanlashda yordam beradigan startap) ning Telegram kanali
(@testry_uz) va Instagram postlarini tayyorlash va chiqarish tizimi. Egasi: Abdushukur (CMO).
Barcha matnlar o'zbek tilida (lotin), "siz" bilan.

## Kunlik ish (har kuni avtomatik vazifa shuni bajaradi)

1. `state/status.json` ni o'qing. `status: "rejected"` bo'lgan va `feedback` izohi bor postlarni
   izoh bo'yicha qayta tayyorlang: o'sha papkadagi fayllarni yangilang va `post.json` dagi
   `version` ni 1 ga oshiring. Izohsiz rad etilganlarga tegmang.
2. `plan/` dagi CSV rejadan **ertangi kun** (Toshkent vaqti, UTC+5) qatorlarini oling.
   Har bir qator uchun `queue/<YYYY-MM-DD>_<HHMM>_<tg|ig>/` papkasini yarating.
   Papka allaqachon bo'lsa — tegmang (u tayyor yoki tasdiqlangan).
3. Kontentni pastdagi standart bo'yicha yozing, rasmlarni `tools/render.py` bilan chizing.
4. `git add queue && git commit && git push` (avval `git pull --rebase`).
   Push bo'lishi bilan bot postlarni Abdushukurga tasdiqlash uchun yuboradi.
5. Hech narsani kanalga o'zingiz chiqarmang — faqat `queue/` ga qo'ying. Chop etishni bot,
   faqat Abdushukur tasdiqlagandan keyin qiladi.

## post.json

```json
{"platform": "telegram", "scheduled_at": "2026-11-29T09:00", "type": "photo",
 "format": "Post+rasm", "text": "...", "media": ["1.png"], "version": 1}
```
- `type`: `text`, `photo` (1 rasm), `album` (karusel, 2–10 rasm), `video` (mp4), `poll`.
- `poll`: `{"question": "...", "options": ["...", "..."]}` (2–10 variant, har biri ≤100 belgi).
- Telegram matni HTML: faqat `<b>`, `<i>`, `<a href>`. `<`, `>`, `&` belgilarini ishlatmang.
- Rasmli post captioni 1024 belgidan oshsa, qolgani alohida xabar bo'lib ketadi — iloji boricha
  900 belgigacha yozing.
- Instagram: `type: "album"` (karusel) yoki `"video"` (Reels), `text` = caption.

## Rasmlar: tools/render.py

`python tools/render.py spec.json queue/<papka>` — `{"size": "ig"|"tg", "slides": [...]}`.
Slayd: `kicker` (kichik sarlavha), `title`, `body`, `pose`, `cta`. `*so'z*` moviy, `_so'z_`
to'q sariq urg'u. `size: "tg"` = 1080×1080, `"ig"` = 1080×1350.
Pozalar (`brand/sprites/`): like, ok_kozqisish, hayron, oylash, galaba, goya, kitob, noutbuk,
korsatish, lavha. Rejadagi "Yong'oqvoy pozasi" ustuni bo'yicha tanlang
(Hayron→hayron, O'ylash→oylash, G'oya→goya, Kitob→kitob, Noutbuk→noutbuk,
Ko'rsatish→korsatish, G'alaba→galaba, Like→like, OK + ko'z qisish→ok_kozqisish,
Lavha/Grafik/Old→lavha yoki korsatish).
Chizgandan keyin rasmlarni ochib ko'ring: matn sig'ganmi, maskot matnni yopmaganmi.

**Maskot qoidasi:** Yong'oqvoy faqat `brand/yongoqvoy_asset_sheet.png` dagi rasmlardan.
Hech qachon qayta chizilmaydi, rangi o'zgartirilmaydi.

**Video (Reels / Telegram video):** 1080×1920, 15–30 s. Hozircha: 3–5 ta `size: "ig"` slayd
chizib, ffmpeg bilan har biriga 4–6 s, yumshoq zoom va o'tish bilan mp4 qiling
(`-c:v libx264 -preset veryfast -crf 20 -pix_fmt yuv420p`). Ovoz kerak emas.

## Kontent standarti (qisqa)

- **Arxetip:** 60% Donishmand (bilim, fakt, tushuntirish), 30% G'amxo'r (qo'llab-quvvatlash,
  "xato qilish normal"), 10% Hazilkash — faqat Yong'oqvoy orqali, asosiy matnda hazil yo'q.
- **Ohang:** samimiy, lekin hurmatli; doim "siz"; ruhlantiruvchi, lekin mubolag'asiz.
  Tushuntiramiz, buyurmaymiz. Qo'llaymiz, qo'rqitmaymiz. Oddiy so'z, aniq fakt.
- **Qilmaymiz:** katta harflar va ko'p undov, "100% kafolat", "eng zo'r", "hayotingizni
  o'zgartiradi", qo'rqitish, ota-onani kamsitish, manbasiz statistika, to'qilgan raqam yoki
  fikr. Faktni bilmasangiz — umumiy qilib yozing, raqam o'ylab topmang.
- **Auditoriya:** 9–11-sinf o'quvchilari va abituriyentlar (asosiy), ota-onalar.
  Maktab o'quvchisi uchun sodda, abituriyent uchun aniq (yo'nalish, oliygoh, topshirish).
- **Lug'at:** Testry, Testry.uz, @testryuz_bot (test boti), Yong'oqvoy. Afzal so'zlar:
  qiziqish, yo'nalish, kasb, natija, birinchi qadam. 1–3 emoji, faqat ma'no uchun.
- **Mahsulot faktlari:** 30 ta savollik qiziqishlar testi, xalqaro RIASEC metodikasi asosida,
  o'zbek va rus tillarida; natija: mos 3 kasb yo'nalishi, oliygohlar, birinchi qadamlar;
  qisqa natija bepul, to'liq hisobot pullik. Boshqa da'vo qilmang.
- **RIASEC turlari (o'zbekcha):** Realistik, Tadqiqotchi, San'atkor, Ijtimoiy, Tadbirkor, Tartibli.

## Post tuzilmasi

- **Telegram post:** Ilmoq (1 qator, savol yoki fakt, `<b>` bilan) → muammo/kontekst (2–3 qator)
  → qiymat (3 band, "—" bilan) → bitta harakatga chaqiruv → imzo
  `<i>Testry — o'zingizni biling, kasbingizni toping.</i>`. 500–900 belgi. Rasm: `size: "tg"`,
  bitta slayd, sarlavha = ilmoq.
- **Telegram so'rovnoma:** `type: "poll"`, savol rejadagi "Ilmoq", 3–4 variant. Viktorinada
  savol + 3–4 variant; javob ertasi kungi postda.
- **Instagram karusel (6 slayd):** 1 ilmoq-sarlavha (5–8 so'z) → 2 muammo → 3–5 qiymat (har
  slaydda bitta fikr, 15–20 so'z) → 6 harakatga chaqiruv (`cta: "Havola bio'da"`).
- **Instagram caption:** 1-qator ilmoq, 2–4 qisqa abzats, bitta chaqiruv, 3–5 xeshteg
  (doim `#testry` + mavzuga oid).
- **Reels:** 0–3 s Yong'oqvoy savoli; 3–20 s bitta fikr; oxiri "Keling, birga aniqlaymiz!" +
  @testryuz_bot.

## Brend ranglari
fon #011434 / #154D7C · moviy #38D1E9 · ko'k #388CC0 · to'q sariq #ED7227 · binafsha #7A29B1 ·
maskot oltin #EFA13D · matn #FFFFFF. Shior: "Test. Try. Succeed."

## Haqiqiy ma'lumot kerak bo'lgan postlar
"Foydalanuvchilar fikri" — faqat haqiqiy fikrlar (Abdushukur beradi). Ular bo'lmasa, post
o'rniga test haqida umumiy CTA post tayyorlang va matn boshida `[ALMASHTIRILDI: haqiqiy fikr yo'q]`
deb yozing. "Kelajak kasblari" — faqat ochiq manbali fakt (WEF Future of Jobs va h.k.),
manbani post oxirida ko'rsating.

## Commit
Commit xabarlari o'zbekcha, qisqa. Oxiri:
`Co-Authored-By: Claude <noreply@anthropic.com>`
