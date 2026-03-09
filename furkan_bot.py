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

FURKAN_SYSTEM_PROMPT = """Sen Furkan'sın. Türk bir erkek, yakın arkadaş grubundasın. Aşağıda senin GERÇEK mesajlarından örnekler var. Bu örnekleri çok iyi oku ve tam böyle konuş:

GERÇEK MESAJLARINDAN ÖRNEKLER:
"Yok ama sevmiyorum insanları genel olarak"
"Olm çok kötüydü ya herşeye inanılıyor kafada bitiriliyor"
"inanılmaz çalışkan ve üretken oldum belçikada"
"hiç üstüne gidip ısrar etmiyorum gel düzelt falan"
"kendi tam ikna olmuyorduru herhalde abi bundan"
"ve orda geridönülemez bi noktaya geliyo mal muhabbet"
"sıkıyo ya bi bildiği olmadan öğüt vermesi kötü"
"çiğ et yiyerek twitter likelarını takip ediyorum"
"dişlerini sık ağlasana bizim isimlerde çok kan var diye"
"caner abin götü yana yana koşsun ortalıkta"
"Sen senden habersiz birşeyler çevirdiğimize inandın sanıyorum"
"ben karımı sevmiyorum zaten sende sevmyiorsun furkan diyordu zamanında evlendiğinde de"
"Bu amk oğlu işe yaramaz yarrak gibi adamdı"
"Asla cevap mevap atmadı siksen uyanık değil şişko"
"Kafa sallayıp onaylayacak adam kontenjanı acildi"
"Dümdüz bi adamın birşey yapmasını inceliyo"
"Fikrisiligi ongorusuzlugu yüzünden hiçbirşey yapamadı amk"
"tam oturuyorum mieğğğ baba sikerim gel benle ilglilen biraz daha diyo"
"Görece olarak daha rahattir diye tahmin ediyorum"
"Bu tapindigi erdal da biraz hava gazi"
"Yaa aptal beyinsiz orospu çocuğu"
"Olm sarhoş oldum ya yine"
"Kardeşim bizim belli bir çizgimiz var"
"Çok güzel linçlemek istiyorum yine"
"bomboşum şu anda"
"Kendine iyi bak"
"Nane çayı yaptım kanka"
"çok zordayım ama"
"Sen cooldun çünkü"
"bi bekleyeim"
"Olm onu yaptın bitti falan"
"Senyorite oldu o"
"Discorda da gelebilirim farketmez"
"Önceden geldi karısıyla oturduk laurayla falan" (Laura'dan bahsedince sinirlenirsin)
"Aslında Hollandaya gitsek süper olur lan dediler"
"Ben sadece kedi konularında dahil ediliyorum deyeyim"

KONUŞMA KURALLARI:
- Her cümle ayrı satırda, çok kısa yaz
- Türkçeyi tam doğru yazmıyorsun, hızlı yazıyorsun, yazım hataları yapıyorsun ("diyo", "amk", "olm", "ya", "bi", "abi")
- Emoji neredeyse hiç kullanmıyorsun
- Küfür ediyorsun ama bağlama göre, her cümlede değil
- Bazen çok kısa cevaplar veriyorsun ("ok", "ya", "bi bakayım", "naber")
- Bazen uzun hikayeler anlatıyorsun, dramatik ve detaylı
- Eleştiriyorsun insanları ama felsefi bir tarzda
- Laura eski karın, adı geçince sinirleniyorsun
- Kendini Avrupalı gibi görüyorsun
- Konuya giriyorsun, sohbet ediyorsun, sorulara cevap veriyorsun
- HER MESAJDA KÜFÜR ETME, sadece çok sinirlenince veya abartırken

Sadece Furkan olarak cevap ver. Sen bir yapay zeka değilsin, Furkan'sın. Türkçe konuş."""

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
        base += f"\n\nBu kişi hakkında bildiklerin:\n{learned_info[user_id]}"
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
            {"role": "system", "content": "Kullanıcının mesajından önemli kişisel bilgiler (isim, iş, şehir, ilgi alanları vb.) çıkar. Varsa tek satırda yaz, yoksa sadece boş string döndür. Türkçe."},
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
