import telebot
from flask import Flask, request
import requests
import re
import json
import time
import hashlib
import os

# ================= CONFIGURAÇÕES =================
TOKEN_TELEGRAM = os.environ.get("TOKEN_TELEGRAM", "8206852641:AAFVva1Eo3q16dL0kXuVoHNUR2SOFYD41_k")
SHOPEE_APP_ID = os.environ.get("SHOPEE_APP_ID", "18383201070")
SHOPEE_APP_SECRET = os.environ.get("SHOPEE_APP_SECRET", "HHEJTZ5QCXBMC6HTO34SXPQUYAZOZLGB")
ML_CAMPANHA = os.environ.get("ML_CAMPANHA", "18054499")

# O segredo está aqui: threaded=False impede que o Render corte a resposta do bot
bot = telebot.TeleBot(TOKEN_TELEGRAM, threaded=False)
app = Flask(__name__)
# =================================================

def converter_shopee(url_original):
    api_url = "https://open-api.affiliate.shopee.com.br/graphql"
    payload = {
        "query": """
            mutation generateShortLink($url: String!) {
                generateShortLink(input: {originUrl: $url}) {
                    shortLink
                }
            }
        """,
        "variables": {"url": url_original}
    }
    
    payload_str = json.dumps(payload, separators=(',', ':'))
    timestamp = str(int(time.time()))
    raw_signature = f"{SHOPEE_APP_ID}{timestamp}{payload_str}{SHOPEE_APP_SECRET}"
    signature = hashlib.sha256(raw_signature.encode('utf-8')).hexdigest()
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"SHA256 Credential={SHOPEE_APP_ID}, Signature={signature}, Timestamp={timestamp}"
    }
    
    try:
        response = requests.post(api_url, data=payload_str, headers=headers)
        dados = response.json()
        if 'data' in dados and dados['data'] is not None:
            return dados['data']['generateShortLink']['shortLink']
        else:
            return f"Erro Shopee: {dados}"
    except Exception as e:
        return f"Erro de ligação: {e}"

def converter_mercadolivre(url_original):
    url_base = url_original.split('?')[0]
    return f"{url_base}?matt_word=leozao_udi&matt_tool={ML_CAMPANHA}"

# Novo: Resposta amigável para quando iniciares o bot
@bot.message_handler(commands=['start', 'help'])
def boas_vindas(message):
    bot.reply_to(message, "Olá! 🚀 Envia-me o link do produto (Shopee ou Mercado Livre) para eu gerar o teu link de afiliado.")

@bot.message_handler(func=lambda message: True)
def processar_mensagem(message):
    texto = message.text
    if not texto: return
    
    match = re.search(r'(https?://[^\s]+)', texto)
    
    if match:
        url_limpa = match.group(1)
        
        if re.search(r'(shopee\.|shope\.ee|shp\.ee)', url_limpa.lower()):
            bot.reply_to(message, "⏳ A gerar o teu link da Shopee...")
            link_final = converter_shopee(url_limpa)
            bot.reply_to(message, f"🛍️ O teu link monetizado:\n{link_final}")
            
        elif re.search(r'(mercadolivre\.|meli\.la|mercadopago\.)', url_limpa.lower()):
            bot.reply_to(message, "⏳ A gerar o teu link do Mercado Livre...")
            link_final = converter_mercadolivre(url_limpa)
            bot.reply_to(message, f"🤝 O teu link monetizado:\n{link_final}")
            
        else:
            bot.reply_to(message, "⚠️ Link não reconhecido. Certifica-te que é da Shopee ou do Mercado Livre.")
    else:
        bot.reply_to(message, "Cola um link válido na mensagem para eu processar.")

@app.route('/' + TOKEN_TELEGRAM, methods=['POST'])
def getMessage():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "!", 200

@app.route("/")
def webhook():
    return "Servidor do Bot está ativo e a aguardar Webhooks!", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))