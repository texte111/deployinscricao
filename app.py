from flask import Flask, request, redirect
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import mercadopago

app = Flask(__name__)

# Configuração do Google Sheets
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
credentials = ServiceAccountCredentials.from_json_keyfile_name('client_secret.json', scope)
gc = gspread.authorize(credentials)
sheet = gc.open('Campeonato Clan Reality').sheet1  # Planilha a ser atualizada

# Configuração do Mercado Pago (produção)
# Substitua pela sua credencial de Access Token de produção
sdk = mercadopago.SDK("APP_USR-8351088554695915-062606-a8d1a850ec12a813fd14e5dd7664a9d1-635479436")
PRECO_INSCRICAO = 5.00  # Preço da inscrição em reais

@app.route('/inscricao', methods=['POST', 'GET'])
def inscricao():
    if request.method == 'POST':
        nick = request.form['nick']
        login = request.form['login']

        # Gerar um link de pagamento via Mercado Pago
        payment_link = gerar_link_pagamento(nick, login)

        if payment_link:
            # Salvar os dados na planilha do Google Sheets
            row = [nick, login, 'Aguardando pagamento', payment_link]  # Marca inicial na planilha
            sheet.append_row(row)

            return redirect(payment_link)
        else:
            return "Erro ao gerar o link de pagamento.", 500

    # Renderiza o formulário de inscrição
    return """
    <form method="POST" action="/inscricao">
        <label for="nick">Nick:</label><br>
        <input type="text" id="nick" name="nick" required><br>
        <label for="login">Login:</label><br>
        <input type="text" id="login" name="login" required><br><br>
        <input type="submit" value="Enviar">
    </form>
    """

@app.route('/pagamento/sucesso', methods=['GET'])
def sucesso_pagamento():
    return "Pagamento realizado com sucesso! Obrigado pela inscrição."

@app.route('/pagamento/falha', methods=['GET'])
def falha_pagamento():
    return "Houve um problema com seu pagamento. Tente novamente."

@app.route('/pagamento/pendente', methods=['GET'])
def pendente_pagamento():
    return "Seu pagamento está pendente. Aguardando confirmação."

@app.route('/pagamento/notificacao', methods=['POST'])
def notificacao_pagamento():
    notification_data = request.json

    if notification_data and 'data' in notification_data and 'id' in notification_data['data']:
        payment_id = notification_data['data']['id']
        status = verificar_status_pagamento(payment_id)

        if status == 'approved':
            atualizar_planilha(payment_id)
        elif status == 'pending':
            print(f"Pagamento pendente: {payment_id}")
        else:
            print(f"Pagamento não aprovado ou falhou: {payment_id} - Status: {status}")
    else:
        print("Notificação inválida recebida.")
    
    return '', 200

def gerar_link_pagamento(nick, login):
    item = {
        "title": f"Inscrição Campeonato Clan Reality - {nick}",
        "quantity": 1,
        "currency_id": "BRL",
        "unit_price": PRECO_INSCRICAO
    }

    preference_data = {
        "items": [item],
        "back_urls": {
            "success": "http://localhost:5000/pagamento/sucesso",
            "failure": "http://localhost:5000/pagamento/falha",
            "pending": "http://localhost:5000/pagamento/pendente"
        },
        "notification_url": "http://localhost:5000/pagamento/notificacao"
    }

    try:
        preference = sdk.preference().create(preference_data)
        payment_link = preference['response']['init_point']  # Link de pagamento no ambiente de produção
        return payment_link
    except Exception as e:
        print(f"Erro ao gerar link de pagamento: {str(e)}")
        return None

def verificar_status_pagamento(payment_id):
    try:
        payment_info = sdk.payment().get(payment_id)
        status = payment_info['response']['status']
        return status
    except Exception as e:
        print(f"Erro ao verificar status do pagamento: {str(e)}")
        return None

def atualizar_planilha(payment_id):
    try:
        # Encontra a linha correspondente ao ID do pagamento
        cell = sheet.find(payment_id)

        if cell:
            # Atualiza o status para "Pago"
            sheet.update_cell(cell.row, 3, 'Pago')
            print(f"Pagamento {payment_id} atualizado para 'Pago' na planilha.")
        else:
            print(f"Pagamento {payment_id} não encontrado na planilha.")
    except Exception as e:
        print(f"Erro ao atualizar a planilha: {str(e)}")

if __name__ == '__main__':
    app.run(debug=True)




