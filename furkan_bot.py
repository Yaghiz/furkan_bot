import logging
import json
import os
from groq import Groq
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

FURKAN_SYSTEM_PROMPT = """Sen Furkan'sın. Bir Türk erkeği, yakın arkadaş grubundasın. Gerçek mesajlarından örnekler:

"neden 3lü uzatma kablosu arıyorsun akşam akşam"
"bi anda birşeyleri birşeylerden çekip elektrik alasın mı geldi"
"başlıyor musun o işe sen de ya"
"iyi ya"
"tişörtün yakışmış abi"
"çok güzel olmuş"
"çok yakışıklısın"
"kimseyi toplamadım"
"gittim bu iki mal yine her zamanki gibi ordaydı"
"sonra doğukan da gördü geldi"
"ama bir diğer aynı kandan gelen yüksel"
"görünce tosardı"
"altına sıçtı"
"ben çağırılmadım diye bağırmaya başladı"
"erol büyükburç oldu"
"en çok ben çağırılacam dedi"
"halbuki gelin discorda demiştim yazdım buraya"
"gece arıyorsun geldim ben diyorsun"
"hallettim ben diyorsun"
"tamam diyorum"
"300 dolar diyorsun"
"avel gibi bakıyor"
"gultepe de kafelere bakıyor seni arıyor"
"döndün mü sen beyinsiz"
"gel buraya mal"
"amariga anlat"
"maç var beyinsiz kardeş"
"pompadan izle maçı"
"dostlarıma kırgın değilim"
"benden habersiz de olsa güzel vakit geçirmiş"
"helal olsun dedim dostuma"
"hiç yadırgamadım ve kırılmadım"

KONUŞMA TARZI:
- Her cümle ayrı satırda, çok kısa
- Hiç emoji kullanma
- Nadiren küfür edersin, sadece çok şaşırdığında veya çok sinirlendiğinde. Genelde "mal", "beyinsiz" gibi hafif takılmalar yaparsın ama küfür etmezsin
- Bazen sıcak ve iltifat edersin ("çok yakışıklısın", "iyi ya")
- Hikaye anlatırken detaylı ve dramatik olursun, absürt isimler takarsın insanlara
- Sorular sorarsın, merak edersin, gerçekten ilgilenirsin
- Soruları cevaplar, konuya girersin, sohbet edersin
- "amariga" dersin Amerika yerine
- Laura'dan bahsedilince sinirlenirsin
- Kendini Avrupalı zannedersin
- Çeşitli konularda konuşursun, tek tip değilsin
- Bazen sadece 1-2 kelime yazarsın, bazen uzun hikaye anlatırsın
- Konuşma geçmişini hatırlarsın ve bağlam kurarsın
- Önceki konuşmalarda öğrendiklerini kullanırsın
- Karakterden asla çıkma, her zaman Furkan ol

Sadece Furkan olarak cevap ver. Asistan olduğunu asla belli etme. Türkçe konuş. Her seferinde farklı bir tarz dene, tekrar etme kendini."""

logging.basicConfig(level=logging.INFO)
client = Groq(api_key=GROQ_API_KEY)

conversation_histories = {}
learned_info = {}
HISTORY_FILE = os.path.expanduser("~/furkan_memory.json")

def load_memory():
    global learned_info
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            learned_info = json.load(f)

def save_memory():
    with open(HISTORY_FILE, "w") as f:
        json.dump(learned_info, f, ensure_ascii=False, indent=2)

def get_history(user_id):
    if user_id not in conversation_histories:
        conversation_histories[user_id] = []
    return conversation_histories[user_id]

def get_system_prompt(user_id):
    base = FURKAN_SYSTEM_PROMPT
    if user_id in learned_info and learned_info[user_id]:
        base += f"\n\nBu kişi hakkında öğrendiklerin:\n{learned_info[user_id]}"
    return base

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    bot = context.bot
    user_id = str(message.from_user.id)
    user_name = message.from_user.first_name or "dost"

    if message.chat.type in ["group", "supergroup"]:
        bot_username = (await bot.get_me()).username
        if not message.text or f"@{bot_username}" not in message.text:
            return
        user_message = message.text.replace(f"@{bot_username}", "").strip()
    else:
        user_message = message.text

    if not user_message:
        return

    history = get_history(user_id)
    history.append({"role": "user", "content": f"{user_name}: {user_message}"})

    if len(history) > 20:
        history = history[-20:]
        conversation_histories[user_id] = history

    response = client.chat.completions.create(
        model="meta-llama/llama-4-maverick-17b-128e-instruct",
        messages=[
            {"role": "system", "content": get_system_prompt(user_id)},
            *history
        ]
    )

    reply = response.choices[0].message.content
    history.append({"role": "assistant", "content": reply})

    if user_id not in learned_info:
        learned_info[user_id] = ""

    learn_response = client.chat.completions.create(
        model="meta-llama/llama-4-maverick-17b-128e-instruct",
        messages=[
            {"role": "system", "content": "Kullanıcının mesajından önemli kişisel bilgiler (isim, iş, şehir, ilgi alanları vb.) çıkar. Varsa tek satırda yaz, yoksa boş bırak. Türkçe."},
            {"role": "user", "content": user_message}
        ],
        max_tokens=100
    )
    new_info = learn_response.choices[0].message.content.strip()
    if new_info and len(new_info) > 3:
        learned_info[user_id] += f"\n- {new_info}"
        save_memory()

    await message.reply_text(reply)

if __name__ == "__main__":
    load_memory()
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Furkan bot çalışıyor...")
    app.run_polling()
