from random import randint
import os


def menu():
    while True:
        print("\n1 - Criar Personagem")
        print("2 - Carregar Personagem")
        print("3 - Iniciar Jogo")
        print("4 - Sair")
        opcao = input("Digite a opção desejada: ")
        if opcao == "1":
            criar_personagem()
        elif opcao == "2":
            carregar_personagem()
        elif opcao == "3":
            iniciar_jogo()
        else:
            exit()

def criar_personagem():
    nome = input("Digite o nome do seu personagem: ")
    personagem = {
        "nome": nome,
        "level": 1,
        "dano": 25,  # Padronizado para minúsculo
        "hp": 100,   # Padronizado para minúsculo
        "hp_max": 100, # Padronizado para minúsculo
        "exp": 0,
        "exp_max": 30,
        "gold": 0,   # Padronizado para minúsculo
        "arma": "Espada de madeira"
    }

    save_dir = "Projeto-RPG/Personagens"
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    save_path = os.path.join(save_dir, f"{personagem['nome']}_Personagens.txt")
    with open(save_path, 'w') as f:
        for key, value in personagem.items():
            f.write(f"{key}: {value}\n")

def carregar_personagem(save_dir="Projeto-RPG/Personagens"):
    try:
        personagens = os.listdir(save_dir)
        if not personagens:
            print("Nenhum personagem encontrado")
            return None
        
        print("Personagens disponíveis:")
        for i, p in enumerate(personagens, 1):
            print(f"{i} - {p.replace('_Personagens.txt', '')}")

        escolha = int(input("Escolha o personagem (número): "))
        if 1 <= escolha <= len(personagens):
            arquivo_personagem = os.path.join(save_dir, personagens[escolha - 1])
            personagem = {}
            with open(arquivo_personagem, 'r') as f:
                for linha in f:
                    key, value = linha.strip().split(': ')
                    # Convert numeric values to integers
                    if key in ['level', 'dano', 'hp', 'hp_max', 'exp', 'exp_max', 'gold']:
                        personagem[key] = int(value)
                    else:
                        personagem[key] = value
            print(f"Personagem {personagem['nome']} carregado com sucesso!")
            return personagem
    except FileNotFoundError:
        print("Nenhum personagem encontrado")
        return None
    except ValueError:
        print("Opção inválida")
        return None

def salvar_personagem(personagem):
    save_dir = "Projeto-RPG/Personagens"
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    save_path = os.path.join(save_dir, f"{personagem['nome']}_Personagens.txt")
    with open(save_path, 'w') as f:
        for key, value in personagem.items():
            f.write(f"{key}: {value}\n")

def exit():
    print("Até mais!")
    os._exit(0)

lista_npcs = []

def criar_npc(level):  # Changed parameter name for clarity
    novo_npc = {
        "nome": f"Monstro #{level}",
        "level": level,  # Remove f-string, keep as integer
        "dano": 5 * level,  # Remove f-string, multiply integers
        "hp": 100 * level,  # Remove f-string, multiply integers
        "hp_max": 100 * level,  # Remove f-string, multiply integers
        "exp": 7 * level,  # Remove f-string, multiply integers
    }
    return novo_npc

def gerar_npcs(n_npcs):
    lista_npcs.clear()  # Clear previous NPCs
    for x in range(n_npcs):
        npc = criar_npc(x + 1)
        lista_npcs.append(npc)

def exibir_npcs():
    for npc in lista_npcs:
        exibir_npc(npc)    

def exibir_npc(npc):
    print(f"Nome: {npc['nome']} // Level: {npc['level']} // Dano: {npc['dano']} // HP: {npc['hp']} // EXP: {npc['exp']}")

def exibir_status_personagem(player):
    print(f"Nome: {player['nome']} // Level: {player['level']} // Dano: {player['dano']} // HP: {player['hp']}/{player['hp_max']} // EXP: {player['exp']}/{player['exp_max']}")

def reset_player(player):
    player['hp'] = player['hp_max']  # Corrigido para usar as mesmas chaves

def reset_npc(npc):
    npc['hp'] = npc['hp_max']

def level_up(player):
    if player['exp'] >= player['exp_max']:
        player['level'] += 1
        player['exp'] = 0
        player['exp_max'] = player['exp_max'] * 2
        player['hp_max'] += 20
        salvar_personagem(player)
        print(f"{player['nome']} subiu de level!")
        exibir_status_personagem(player)  # Adicionado o parâmetro player

def iniciar_batalha(player, npc):
    while player['hp'] > 0 and npc['hp'] > 0:  # Corrigido para usar as mesmas chaves
        atacar_npc(player, npc)
        atacar_player(player, npc)
        exibir_info_batalha(player, npc)
    
    # Moved battle results outside the while loop
    if player['hp'] > 0:
        print(f"{player['nome']}, venceu e ganhou {npc['exp']} de EXP!")
        player['exp'] += npc['exp']
        exibir_status_personagem(player)
        if player['exp'] >= player['exp_max']:
            level_up(player)
    else:
        print(f"{npc['nome']} venceu!")
        exibir_npc(npc)
    
    reset_player(player)
    reset_npc(npc)
    salvar_personagem(player)

def atacar_npc(player, npc):
    npc['hp'] -= player['dano']  # Corrigido para usar 'dano' em vez de 'Dano'

def atacar_player(player, npc):
    player['hp'] -= npc['dano']  # Corrigido para usar as mesmas chaves


def exibir_info_batalha(player, npc):
    print(f"Player: {player['hp']}/{player['hp_max']}")  # Corrigido para usar as mesmas chaves
    print(f"NPC: {npc['nome']}: {npc['hp']}/{npc['hp_max']}")
    print("_______________________\n")

def iniciar_jogo():
    while True:
        player = carregar_personagem()
        if player is None:
            return
        print("\n1 - Batalhar contra um NPC")
        print("2 - Exibir status do personagem")
        print("3 - Salvar e sair")
        escolha = input("Digite a opção desejada: ")
        if escolha == "1":
            gerar_npcs(5)
            npc_selecionado = lista_npcs[0]
            iniciar_batalha(player, npc_selecionado)
        elif escolha == "2":
            exibir_status_personagem(player)
        else:
            save_dir = "Projeto-RPG/Personagens"
            if not os.path.exists(save_dir):
                os.makedirs(save_dir)

            save_path = os.path.join(save_dir, f"{player['nome']}_Personagens.txt")
            with open(save_path, 'w') as f:
                for key, value in player.items():
                    f.write(f"{key}: {value}\n")
            print("Personagem salvo com sucesso!")
            exit()

if __name__ == "__main__":
    menu()