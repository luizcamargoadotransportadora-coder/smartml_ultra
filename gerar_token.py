import urllib.request, urllib.parse, json, urllib.error

print("\n--- GERADOR DE TOKEN VITALICIO ---")
client_id = input("1. Cole seu App ID e aperte Enter: ").strip()
client_secret = input("2. Cole sua Chave Secreta e aperte Enter: ").strip()
code = input("3. Cole o codigo (TG-...) e aperte Enter: ").strip()

payload = {
    'grant_type': 'authorization_code',
    'client_id': client_id,
    'client_secret': client_secret,
    'code': code,
    'redirect_uri': 'https://httpbin.org/get'
}

data = urllib.parse.urlencode(payload).encode('utf-8')
req = urllib.request.Request('https://api.mercadolibre.com/oauth/token', data=data)

try:
    r = urllib.request.urlopen(req)
    token_data = json.loads(r.read())
    with open('credenciais.json', 'w') as f:
        json.dump({'refresh_token': token_data['refresh_token']}, f)
    print('\n[SUCESSO] credenciais.json criado com sucesso!')
except urllib.error.HTTPError as e:
    print('\n[ERRO DETALHADO DO ML]:', e.read().decode('utf-8'))
except Exception as e:
    print('\n[ERRO LOCAL]:', str(e))