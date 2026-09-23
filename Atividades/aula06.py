# # Desafio 12
import json

# with open("usuario.json", "r") as arquivo:
#     usuario = json.load(arquivo)

# print(usuario)

# # Desafio 13

# usuarios = [
#     {"nome": "Felipe", "idade": 20, "profissao": "Programador"},
#     {"nome": "Maria", "idade": 25, "profissao": "Designer"},
#     {"nome": "João", "idade": 24, "profissao": "Engenheiro"}
# ]

# with open("usuarios.json", "w") as arquivo:
#     json.dump(usuarios, arquivo, indent=4)

# with open("usuarios.json", "r") as arquivo:
#     usuarios_carregados = json.load(arquivo)

# for usuario in usuarios_carregados:
#     print(f"Nome: {usuario['nome']} - Idade: {usuario['idade']} - Profissão: {usuario['profissao']}")

# Desafio 14

def alterar_idade(nome, nova_idade):
    with open("usuarios.json", "r") as arquivo:
        usuarios_carregados = json.load(arquivo)
        for usuario in usuarios_carregados:
            if nome == usuario['nome']:
               usuario['idade'] = nova_idade
               with open("usuarios.json", "w") as arquivo:
                    json.dump(usuarios_carregados, arquivo, indent=4)
               return True, usuarios_carregados
        else:
            return False

nome = input("Digite o nome do usuario a ser atualizado: ")
nova_idade = int(input("Digite a idade nova: "))
validacao, lista = alterar_idade(nome, nova_idade)

if validacao:
    for usuario in lista:
        print(f"Nome: {usuario['nome']} - Idade: {usuario['idade']} - Profissão: {usuario['profissao']}")
else:
    print("Usuário não encontrado.")