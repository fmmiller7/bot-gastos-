import os, re, requests
from flask import Flask, request
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

app = Flask(__name__)

WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_ID = os.getenv("PHONE_ID")
SHEET_ID = os.getenv("SHEET_ID")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "mi_token_secreto_123")

def get_sheet():
    scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
    client = gspread.authorize(creds)
    return client.open_by_key(SHEET_ID).sheet1

def enviar_whatsapp(to, texto):
    url = f"https://graph.facebook.com/v20.0/{PHONE_ID}/messages"
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"}
    data = {"messaging_product": "whatsapp", "to": to, "type": "text", "text": {"body": texto}}
    requests.post(url, headers=headers, json=data)

@app.route('/')
def home():
    return "Bot de gastos activo"

@app.route('/webhook', methods=['GET'])
def verificar():
    if request.args.get('hub.verify_token') == VERIFY_TOKEN:
        return request.args.get('hub.challenge'), 200
    return "Error", 403

@app.route('/webhook', methods=['POST'])
def recibir():
    try:
        data = request.json
        entry = data['entry'][0]['changes'][0]['value']
        if 'messages' not in entry:
            return "ok", 200
        msg_info = entry['messages'][0]
        de = msg_info['from']
        texto = msg_info['text']['body'].lower().strip()
        sheet = get_sheet()

        if texto.startswith("balance") or texto.startswith("saldo"):
            valores = sheet.get_all_records()
            saldo = sum([int(r['Monto']) if r['Tipo']=='INGRESO' else -int(r['Monto']) for r in valores])
            enviar_whatsapp(de, f"💰 Saldo: ${saldo:,}")
            return "ok", 200

        m = re.match(r'(gaste|gasto|ingrese|ingreso)\s+(\d+)\s*(.*)', texto)
        if m:
            tipo = "EGRESO" if "gast" in m[1] else "INGRESO"
            monto = int(m[2])
            nota = m[3] or "-"
            fecha = datetime.now().strftime("%d/%m/%Y %H:%M")
            sheet.append_row([fecha, tipo, monto, nota])
            enviar_whatsapp(de, f"✅ Anotado: {tipo} ${monto:,} ({nota})")
    except Exception as e:
        print(e)
    return "ok", 200
