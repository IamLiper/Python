import json
import os
import difflib

# Nome do arquivo que guarda o conhecimento
arquivo = "Chat-inteligente/cerebro.json"

# Carregar cérebro existente ou criar um novo
if os.path.exists(arquivo):
    with open(arquivo, "r", encoding="utf-8") as f:
        cerebro = json.load(f)
else:
    cerebro = {}

# Padroniza entradas antigas para o novo formato
for pergunta, valor in list(cerebro.items()):
    if isinstance(valor, str):
        cerebro[pergunta] = {
            "resposta": valor,
            "palavras_chave": [palavra for palavra in pergunta.split()]
        }

# Salva o cérebro atualizado
with open(arquivo, "w", encoding="utf-8") as f:
    json.dump(cerebro, f, ensure_ascii=False, indent=4)

# Lista de palavras-chave para encerrar a conversa
palavras_saida = ["tchau", "bye", "adeus"]

print("🤖 Olá! Eu sou o ChatBot Inteligente. Digite algo ou 'tchau' para encerrar.")

# Loop de conversa
while True:
    pergunta = input("Você: ").strip().lower()

    # Verifica se alguma palavra de saída aparece na frase
    if any(palavra in pergunta for palavra in palavras_saida):
        print("ChatBot: Até logo! 👋")
        break

    # Procura a pergunta exata no cérebro
    if pergunta in cerebro:
        print(f"ChatBot: {cerebro[pergunta]['resposta']}")
    else:
        # Se não achou, usa similaridade para procurar algo parecido
        perguntas_existentes = list(cerebro.keys())
        correspondencias = difflib.get_close_matches(pergunta, perguntas_existentes, n=1, cutoff=0.6)
        
        if correspondencias:
            similar = correspondencias[0]
            # Verifica se a entrada é um dicionário
            if isinstance(cerebro[similar], dict):
                print(f"ChatBot: {cerebro[similar]['resposta']}")
            else:
                print(f"ChatBot: {cerebro[similar]}")
        else:
            # Se não encontrou nada parecido, pergunta ao usuário e aprende
            resposta = input("ChatBot: Não sei a resposta. O que eu deveria responder? ").strip()
            
            # Extraindo palavras-chave simples
            palavras_chave = [palavra for palavra in pergunta.split() if palavra not in palavras_saida]

            # Armazenando a pergunta, resposta e palavras-chave
            cerebro[pergunta] = {
                "resposta": resposta,
                "palavras_chave": palavras_chave
            }

            # Salva o cérebro atualizado
            with open(arquivo, "w", encoding="utf-8") as f:
                json.dump(cerebro, f, ensure_ascii=False, indent=4)

            print("ChatBot: Entendido! Vou lembrar disso da próxima vez.")
