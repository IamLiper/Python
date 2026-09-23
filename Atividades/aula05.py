# # Desafio 1

# nome = input("Digite um nome: ")

# with open("usuarios.txt", "w") as arquivo:
#     arquivo.write(nome)

# with open("usuarios.txt", "r") as arquivo:
#     conteudo = arquivo.read()

# print(conteudo)

# # Desafio 2

# nome = input("Digite o nome a ser adicionado: ")

# with open("usuarios.txt", "a") as arquivo:
#     arquivo.write(nome + "\n")

# with open("usuarios.txt", "r") as arquivo:
#     conteudo = arquivo.read()

# print(conteudo)

# # Desafio 3

# def salvar_nome(nome):
#     with open("usuarios.txt", "a") as arquivo:
#         arquivo.write(nome + "\n")

# def listar_nomes():
#     with open("usuarios.txt", "r") as arquivo:
#         conteudo = arquivo.read()
#         print(conteudo)

# listar_nomes()

# # Desafio 4

# def listar_nomes():
#     try:
#         with open("usuarios.txt", "r") as arquivo:
#             conteudo = arquivo.read()
#             print(conteudo)
#     except FileNotFoundError:
#         print("Nenhum usuario cadastrado ainda.")

# nome = input("Digite um nome para ser adicionado: ")
# salvar_nome(nome)
# listar_nomes()

# # Desafio 5

# def listar_nomes():
#     try:
#         with open("usuarios.txt", "r") as arquivo:
#                 for conteudo in arquivo:
#                     print(conteudo.strip())  
                    
#     except FileNotFoundError:
#         print("Nenhum usuario cadastrado ainda.")

# listar_nomes()

# # Desafio 6

# def listar_nomes():
#     nomes = []
#     try:
#         with open("usuarios.txt", "r") as arquivo:
#             for conteudo in arquivo:
#                 nomes.append(conteudo.strip())
#             if not nomes:
#                 print("Nenhum usuário cadastrado.")
#             else:
#                 return nomes
#     except FileNotFoundError:
#         print("Arquivo não encontrado.")

# # Desafio 7, 8, 9, 10

# def buscar_usuario(nome):
#         nomes = listar_nomes()
#         for usuario in nomes:
#             if nome == usuario:
#                 return True
#         else:
#             return False

# def cadastrar_usuarios():
#     while True:
#         print("""
# \n1 - Cadatrar
# 2 - Listar
# 3 - Sair\n
# """)
#         opcao = input("Escolha uma opcão: (1 a 3): ")

#         if opcao == '1':
#             nome = input("Digite um nome para o cadastro: ")
#             valido = buscar_usuario(nome)
#             if valido:
#                 print("Usuário ja cadastrado!")
#                 continue
#             else:
#                 salvar_nome(nome)
#                 print("\nNome cadastrdo com sucesso!")
#         elif opcao == '2':
#             nomes = listar_nomes()
#             if nomes == None:
#                 continue
#             else:
#                 for indice, nome in enumerate(nomes, start=1):
#                     print(indice, nome)
#         elif opcao == '3':
#             print("Cadastro encerrado!")
#             break
#         else:
#             print("opcão inválida, tente novamente.")

# cadastrar_usuarios()

# Dessafio 11

import json

usuario = {
    "nome": "Felipe",
    "idade": 20,
    "profissao": "Programador"
}

with open("usuario.json", "w")as arquivo:
    json.dump(usuario, arquivo)
