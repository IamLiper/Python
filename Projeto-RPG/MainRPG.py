from random import randint
import os

<<<<<<< HEAD

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
=======
class CriarPersonagem:
    def __init__(self):
        # Status iniciais do personagem
        self.lvl = 1
        self.exp = 0
        self.vida_maxima = 100
        self.vida = self.vida_maxima
        self.ataque = 10
        self.defesa = 10
        self.agilidade = 10
        self.ataque_magico = 10
        self.defesa_magica = 10
        self.chance_de_critico = 10
        self.critico = (self.ataque + self.agilidade) * 2
        
        self.nome = input("Digite o nome do personagem: ")
        while True:
            self.sexo = input("Escolha o sexo (M/F): ").upper()
            if self.sexo in ['M', 'F']:
                break
            print("Opção inválida!")
            
        print("\nClasses disponíveis:")
        print("1 - Guerreiro")
        print("2 - Mago")
        print("3 - Assassino")
        
        while True:
            escolha = input("Escolha sua classe (1-3): ")
            if escolha in ['1', '2', '3']:
                self.classe = {'1': 'Guerreiro', '2': 'Mago', '3': 'Assassino'}[escolha]
                break
            print("Opção inválida!")
            
        self.salvar_personagem()
    
    def salvar_personagem(self):
        caminho = os.path.join(os.path.dirname(__file__), 'Personagens')
        if not os.path.exists(caminho):
            os.makedirs(caminho)
            
        arquivo_path = os.path.join(caminho, f'{self.nome}.txt')
        with open(arquivo_path, 'w') as arquivo:
            dados = [
                f"Nome: {self.nome}",
                f"Sexo: {self.sexo}",
                f"Classe: {self.classe}",
                f"Level: {self.lvl}",
                f"EXP: {self.exp}",
                f"Vida Máxima: {self.vida_maxima}",
                f"Vida: {self.vida}",
                f"Ataque: {self.ataque}",
                f"Defesa: {self.defesa}",
                f"Agilidade: {self.agilidade}",
                f"Ataque Mágico: {self.ataque_magico}",
                f"Defesa Mágica: {self.defesa_magica}",
                f"Chance de Crítico: {self.chance_de_critico}",
                f"Crítico: {self.critico}"
            ]
            arquivo.write('\n'.join(dados))

    def aumentar_status(self):
        self.vida_maxima += 20
        self.vida = self.vida_maxima
        self.ataque += 5
        self.defesa += 5
        self.agilidade += 3
        self.ataque_magico += 3
        self.defesa_magica += 3

class CarregarPersonagem:
    def __init__(self):
        # Usa o caminho absoluto para a pasta Personagens
        caminho = os.path.join(os.path.dirname(__file__), 'Personagens')
        if not os.path.exists(caminho):
            print("Nenhum personagem encontrado!")
            return
            
        try:
            # Lista os personagens usando o caminho correto
            personagens = os.listdir(caminho)
            if not personagens:
                print("Nenhum personagem encontrado!")
                return
                
            print("\nPersonagens disponíveis:")
            for i, p in enumerate(personagens, 1):
                print(f"{i} - {p.replace('.txt', '')}")
                
            while True:
                try:
                    escolha = int(input("\nEscolha um personagem: ")) - 1
                    if 0 <= escolha < len(personagens):
                        self.carregar(personagens[escolha])
                        break
                    print("Escolha inválida!")
                except ValueError:
                    print("Por favor, digite um número válido!")
        except Exception as e:
            print(f"Erro ao carregar personagem: {str(e)}")
    
    def carregar(self, arquivo):
        try:
            caminho = os.path.join(os.path.dirname(__file__), 'Personagens')
            arquivo_path = os.path.join(caminho, arquivo)
            with open(arquivo_path, 'r') as f:
                dados = {}
                for linha in f:
                    if ':' in linha:
                        chave, valor = linha.split(':', 1)
                        dados[chave.strip()] = valor.strip()
                
                # Carrega os dados usando get() para evitar KeyError
                self.nome = dados.get('Nome', '')
                self.sexo = dados.get('Sexo', '')
                self.classe = dados.get('Classe', '')
                self.lvl = int(dados.get('Level', 1))
                self.exp = int(dados.get('EXP', 0))
                self.vida_maxima = int(dados.get('Vida Máxima', 100))
                self.vida = int(dados.get('Vida', self.vida_maxima))
                self.ataque = int(dados.get('Ataque', 10))
                self.defesa = int(dados.get('Defesa', 10))
                self.agilidade = int(dados.get('Agilidade', 10))
                self.ataque_magico = int(dados.get('Ataque Mágico', 10))
                self.defesa_magica = int(dados.get('Defesa Mágica', 10))
                self.chance_de_critico = int(dados.get('Chance de Crítico', 10))
                self.critico = int(dados.get('Crítico', 40))
                
                # Mostra os status do personagem
                print("\n=== Status do Personagem ===")
                print(f"Nome: {self.nome}")
                print(f"Sexo: {self.sexo}")
                print(f"Classe: {self.classe}")
                print(f"Level: {self.lvl}")
                print(f"EXP: {self.exp}")
                print(f"Vida: {self.vida}/{self.vida_maxima}")
                print(f"Ataque: {self.ataque}")
                print(f"Defesa: {self.defesa}")
                print(f"Agilidade: {self.agilidade}")
                print(f"Ataque Mágico: {self.ataque_magico}")
                print(f"Defesa Mágica: {self.defesa_magica}")
                print(f"Chance de Crítico: {self.chance_de_critico}")
                print(f"Crítico: {self.critico}")
                print("=" * 25)
                
                # Adiciona o método aumentar_status
                def aumentar_status(self):
                    self.vida_maxima += 20
                    self.vida = self.vida_maxima
                    self.ataque += 5
                    self.defesa += 5
                    self.agilidade += 3
                    self.ataque_magico += 3
                    self.defesa_magica += 3
                
                # Adiciona o método como atributo da instância
                self.aumentar_status = aumentar_status.__get__(self)
                
        except Exception as e:
            print(f"Erro ao ler arquivo do personagem: {str(e)}")
            print("Verifique se o arquivo do personagem está correto ou crie um novo personagem.")

class Monstro:
    def __init__(self, nome, nivel):
        self.nome = nome
        self.nivel = nivel
        self.vida_maxima = 50 + (nivel * 10)
        self.vida = self.vida_maxima
        self.exp = nivel * 10
        self.vivo = True
        self.ataque = 5 + (nivel * 2)

    def receber_dano(self, dano):
        self.vida -= dano
        if self.vida <= 0:
            self.vivo = False
            return True
        return False

    def respawn(self):
        self.vida = self.vida_maxima
        self.vivo = True

class Dungeon:
    def __init__(self, nome, personagem):
        self.nome = nome
        self.total_andares = 100
        self.andar_atual = 1
        self.personagem = personagem
        self.requisito_nivel = 50 if nome == "Dungeon of Water" else 1
        self.monstros = []
        self.gerar_monstros()

    def gerar_monstros(self):
        self.monstros.clear()
        nivel_base = 1 + ((self.andar_atual - 1) * 5)
        
        if self.nome == "Dungeon of Wind":
            monstros_info = [
                ("Goblin", nivel_base),
                ("Slime", nivel_base + 1),
                ("Lobo", nivel_base + 2),
                ("Aranha", nivel_base + 3),
                ("Wind Guardian", nivel_base + 4)
            ]
        else:  # Dungeon of Water
            monstros_info = [
                ("Water Sprite", nivel_base),
                ("Coral Beast", nivel_base + 1),
                ("Deep One", nivel_base + 2),
                ("Sea Serpent", nivel_base + 3),
                ("Water Guardian", nivel_base + 4)
            ]
        
        self.monstros = [Monstro(nome, nivel) for nome, nivel in monstros_info]

    def mostrar_monstros(self):
        print("\n=== Monstros Disponíveis ===")
        for i, monstro in enumerate(self.monstros, 1):
            if monstro.vivo:
                print(f"{i} - {monstro.nome} (Nível {monstro.nivel}) - Vida: {monstro.vida}")
        print("=" * 25)

    def batalhar(self):
        while True:
            os.system('clear')
            self.mostrar_info()
            self.mostrar_monstros()
            
            if self.personagem.vida <= 0:
                print("\nVocê morreu! Voltando ao menu...")
                self.personagem.vida = self.personagem.vida_maxima
                break
                
            print("\n0 - Voltar ao menu da Dungeon")
            escolha = input("Escolha um monstro para atacar: ")
            
            if escolha == "0":
                break
                
            try:
                escolha = int(escolha) - 1
                if 0 <= escolha < len(self.monstros):
                    monstro = self.monstros[escolha]
                    if not monstro.vivo:
                        print("\nEste monstro já foi derrotado!")
                        monstro.respawn()
                        print("O monstro reapareceu!")
                        continue
                        
                    # Sistema de dano
                    dano_personagem = self.personagem.ataque
                    dano_monstro = monstro.ataque
                    
                    # Personagem ataca primeiro
                    if monstro.receber_dano(dano_personagem):
                        print(f"\nVocê derrotou {monstro.nome}!")
                        self.personagem.exp += monstro.exp
                        print(f"Ganhou {monstro.exp} de experiência!")
                        
                        # Cura após vitória
                        self.personagem.vida = self.personagem.vida_maxima
                        print("Sua vida foi restaurada!")
                        
                        # Sistema de level up
                        exp_necessaria = self.personagem.lvl * 100
                        print(f"\nEXP para próximo nível: {exp_necessaria - self.personagem.exp}")
                        
                        if self.personagem.exp >= exp_necessaria:
                            self.personagem.lvl += 1
                            print(f"\nLevel Up! Você agora é nível {self.personagem.lvl}!")
                            # Aumenta os status ao subir de nível
                            self.personagem.aumentar_status()
                            
                        # Respawn do monstro
                        monstro.respawn()
                    else:
                        # Monstro contra-ataca
                        print(f"\nVocê causou {dano_personagem} de dano em {monstro.nome}")
                        print(f"Vida restante do monstro: {monstro.vida}")
                        
                        self.personagem.vida -= dano_monstro
                        print(f"\n{monstro.nome} causou {dano_monstro} de dano em você!")
                        print(f"Sua vida restante: {self.personagem.vida}")
                else:
                    print("\nEscolha inválida!")
            except ValueError:
                print("\nPor favor, digite um número válido!")
            
            input("\nPressione ENTER para continuar...")

    def pode_entrar(self):
        if self.nome == "Dungeon of Water" and self.personagem.lvl < self.requisito_nivel:
            print(f"\nAVISO: Você precisa ser nível {self.requisito_nivel} para entrar na {self.nome}!")
            print(f"Seu nível atual: {self.personagem.lvl}")
            return False
        return True

    def mostrar_info(self):
        print(f"\n=== {self.nome} ===")
        print(f"Andar atual: {self.andar_atual}/{self.total_andares}")
        print(f"Personagem: {self.personagem.nome} (Nível {self.personagem.lvl})")
        print(f"EXP: {self.personagem.exp}")
        print("=" * 25)

def menu_dungeon(personagem):
    while True:
        os.system('clear')
        print("\n=== Selecione uma Dungeon ===")
        print("1 - Dungeon of Wind (Nível Recomendado: 1)")
        print("2 - Dungeon of Water (Nível Requerido: 50)")
        print("3 - Voltar ao Menu Principal")
        
        opcao = input("\nEscolha uma opção: ")
        
        if opcao == '1':
            dungeon = Dungeon("Dungeon of Wind", personagem)
            if personagem.lvl >= dungeon.requisito_nivel:
                dungeon.batalhar()
                salvar_progresso(personagem)
            else:
                print(f"\nNível mínimo requerido: {dungeon.requisito_nivel}")
                input("\nPressione ENTER para continuar...")
        elif opcao == '2':
            dungeon = Dungeon("Dungeon of Water", personagem)
            if personagem.lvl >= dungeon.requisito_nivel:
                dungeon.batalhar()
                salvar_progresso(personagem)
            else:
                print(f"\nNível mínimo requerido: {dungeon.requisito_nivel}")
                input("\nPressione ENTER para continuar...")
        elif opcao == '3':
            # Salva o progresso antes de voltar ao menu principal
            salvar_progresso(personagem)
            break
        else:
            print("\nOpção inválida!")
            input("Pressione ENTER para continuar...")

def salvar_progresso(personagem):
    """Função para salvar o progresso do personagem"""
    try:
        caminho = os.path.join(os.path.dirname(__file__), 'Personagens')
        if not os.path.exists(caminho):
            os.makedirs(caminho)
            
        arquivo_path = os.path.join(caminho, f'{personagem.nome}.txt')
        with open(arquivo_path, 'w') as arquivo:
            dados = [
                f"Nome: {personagem.nome}",
                f"Sexo: {personagem.sexo}",
                f"Classe: {personagem.classe}",
                f"Level: {personagem.lvl}",
                f"EXP: {personagem.exp}",
                f"Vida Máxima: {personagem.vida_maxima}",
                f"Vida: {personagem.vida}",
                f"Ataque: {personagem.ataque}",
                f"Defesa: {personagem.defesa}",
                f"Agilidade: {personagem.agilidade}",
                f"Ataque Mágico: {personagem.ataque_magico}",
                f"Defesa Mágica: {personagem.defesa_magica}",
                f"Chance de Crítico: {personagem.chance_de_critico}",
                f"Crítico: {personagem.critico}"
            ]
            arquivo.write('\n'.join(dados))
            print("\nProgresso salvo com sucesso!")
    except Exception as e:
        print(f"\nErro ao salvar progresso: {str(e)}")

def menu_principal():
    personagem = None
    while True:
        os.system('clear')
        print("=== RPG GAME ===")
        print("1 - Criar Novo Personagem")
        print("2 - Carregar Personagem")
        print("3 - Entrar na Dungeon")
        print("4 - Sair")
        
        opcao = input("\nEscolha uma opção: ")
        
        if opcao == '1':
            personagem = CriarPersonagem()
            input("\nPressione ENTER para continuar...")
        elif opcao == '2':
            personagem = CarregarPersonagem()
            input("\nPressione ENTER para continuar...")
        elif opcao == '3':
            if personagem is None:
                print("\nVocê precisa criar ou carregar um personagem primeiro!")
                input("Pressione ENTER para continuar...")
            else:
                menu_dungeon(personagem)
        elif opcao == '4':
            print("\nObrigado por jogar!")
            break
        else:
            print("\nOpção inválida!")
            input("Pressione ENTER para continuar...")

if __name__ == "__main__":
    menu_principal()
>>>>>>> e573e9a9b83a48c008631302eb794854b1dd1393
