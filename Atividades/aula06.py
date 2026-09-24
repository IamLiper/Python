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

# Desafio 14, 15

# def alterar_idade(nome, nova_idade):
#     with open("usuarios.json", "r") as arquivo:
#         usuarios_carregados = json.load(arquivo)
#         for usuario in usuarios_carregados:
#             if nome == usuario['nome']:
#                usuario['idade'] = nova_idade
#                with open("usuarios.json", "w") as arquivo:
#                     json.dump(usuarios_carregados, arquivo, indent=4)
#                return True, usuarios_carregados
#         else:
#             return False

# def excluir_usuario(nome):
#     with open("usuarios.json", "r") as arquivo:
#         carregados = json.load(arquivo)
#         for usuario in carregados:
#             if nome == usuario['nome']:
#                 carregados.remove(usuario)
#                 with open("usuarios.json", "w") as arquivo:
#                     json.dump(carregados, arquivo, indent=4)
#                 return True
#         else:
#             return False

# nome = input("Digite o nome do usuario a ser excljuido: ")
# validacao = excluir_usuario(nome)
# if validacao:
#     print("Usuário excluido com sucesso!")
# else:
#     print("Usuário não encontrado.")
# nova_idade = int(input("Digite a idade nova: "))
# validacao, lista = alterar_idade(nome, nova_idade)

# if validacao:
#     for usuario in lista:
#         print(f"Nome: {usuario['nome']} - Idade: {usuario['idade']} - Profissão: {usuario['profissao']}")
# else:
#     print("Usuário não encontrado.")

# # Desafio 16

# def cadastrar_usuario(nome, idade, profissao):
#     novo_usuario = {"nome": nome, "idade": idade, "profissao": profissao}
#     with open("usuarios.json", "r")as arquivo:
#         carregados = json.load(arquivo)
#     carregados.append(novo_usuario)
#     with open("usuarios.json", "w") as arquivo:
#         json.dump(carregados, arquivo, indent=4)
#     return carregados

# nome = input("Digite um nome: ")
# idade = int(input("Digite a idade: "))
# profissao = input("Digite a profissao: ")

# cadastro = cadastrar_usuario(nome, idade, profissao)

# print(cadastro)

# Desafio 17

def listar_usuarios():
    with open("usuarios.json", "r") as arquivo:
        carregados = json.load(arquivo)
    for indice, usuario in enumerate(carregados, start=1):
        print(indice, f"Nome: {usuario['nome']} - Idade: {usuario['idade']} - Profissão: {usuario['profissao']}")

listar_usuarios()