import os

# Status iniciais do personagem
lvl = 1
exp = 0
vida = 100
ataque = 10
defesa = 10
agilidade = 10
ataque_magico = 10
defesa_magica = 10
chance_de_critico = 10
critico = (ataque + agilidade) * 2

class CriarPersonagem:
    def __init__(self):
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
        if not os.path.exists('Personagens'):
            os.makedirs('Personagens')
            
        with open(f'Personagens/{self.nome}.txt', 'w') as arquivo:
            arquivo.write(f"Nome: {self.nome}\n")
            arquivo.write(f"Sexo: {self.sexo}\n")
            arquivo.write(f"Classe: {self.classe}\n")

class CarregarPersonagem:
    def __init__(self):
        try:
            personagens = os.listdir('Personagens')
            print("\nPersonagens disponíveis:")
            for i, p in enumerate(personagens, 1):
                print(f"{i} - {p.replace('.txt', '')}")
                
            escolha = int(input("\nEscolha um personagem: ")) - 1
            self.carregar(personagens[escolha])
        except:
            print("Erro ao carregar personagem!")
    
    def carregar(self, arquivo):
        with open(f'Personagens/{arquivo}', 'r') as f:
            dados = f.readlines()
            self.nome = dados[0].split(': ')[1].strip()
            self.sexo = dados[1].split(': ')[1].strip()
            self.classe = dados[2].split(': ')[1].strip()