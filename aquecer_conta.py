import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

print("Iniciando navegador para login manual...")
opts = Options()
opts.add_argument("--start-maximized")
opts.add_experimental_option("excludeSwitches", ["enable-automation"])
opts.add_experimental_option("useAutomationExtension", False)

# Aponta para a MESMA pasta que o nosso robô usa
profile_dir = os.path.join(os.getcwd(), "chrome_profile")
opts.add_argument(f"--user-data-dir={profile_dir}")

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opts)
driver.get("https://www.mercadolivre.com.br/")

print("\n" + "="*60)
print("🚨 NAVEGADOR ABERTO! 🚨")
print("1. Vá para a janela do Chrome que acabou de abrir.")
print("2. Clique em 'Entrar' e faça login na sua conta do Mercado Livre.")
print("3. Resolva qualquer quebra-cabeça/CAPTCHA que ele pedir.")
print("4. Só quando estiver logado e vendo a página inicial normal...")
print("   ...volte nesta tela preta (CMD) e aperte ENTER.")
print("="*60 + "\n")

input("Pressione ENTER aqui para salvar o perfil e fechar...")
driver.quit()
print("✅ Perfil salvo com sucesso! O robô agora está autenticado.")