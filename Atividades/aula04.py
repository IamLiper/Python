# # Desafio 1

# def ler_idade():
#     try:
#         idade = int(input("Digite sua idade: "))
#         if idade < 0:
#             print("A idade não pode ser negativa.")
#         else:
#             return idade
#     except ValueError:
#         print("Digite apenas número.")

# print(ler_idade())

# # Desafio 2

# def ler_idade():
#     while True:
#         try:
#             idade = int(input("Digite a sua idade: "))
#             if idade < 0:
#                 print("A idade não pode ser negativa.")
#             else:
#                 return idade
#         except ValueError:
#             print("Digite apenas número.")

# idade = ler_idade()
# print(f"Idade válida: {idade}")

# # Desafio 3

# def validar_idade(idade):
#     return idade >= 0
        

# def ler_idade():
#     while True:    
#         try:
#             idade = int(input("Digite a sua idade: "))
#             if validar_idade(idade):
#                 return idade
#             else:
#                 print("A idade não pode ser negativa.")
#         except ValueError:
#             print("Digite apenas número.")

# idade = ler_idade()
# print(f"Idade válida: {idade}")

# # Desafio 4

# def validar_idade(idade):
#     return idade >= 18 and idade <= 120

# def ler__idade():
#     while True:
#         try:
#             idade = int(input("Digite a sua idade: "))
#             if validar_idade(idade):
#                 return idade
#             else:
#                 print("Você precisa ter pelo menos entre 18 a 120 anos.")
#         except ValueError:
#             print("Digite apenas números.")

# idade = ler__idade()
# print(f"Idade válida: {idade}")

# # Desafio 5

# def validar_idade(idade, mensagem):
#     if idade < 18:
#         mensagem = "A idade minima é 18 anos."
#         return mensagem
#     elif idade > 120:
#          mensagem =  "A idade máxima é 120 anos."
#          return mensagem
#     else:
#         mensagem = "Idade válida."
#         return mensagem

# def ler_idade():
#     while True:
#         try:
#             idade = int(input("Digite a sua idade: "))
#             mensagem = validar_idade(idade, mensagem)
#             if mensagem == "Idade válida.":
#                 validacao = True
#             elif mensagem == "A idade minima é 18 anos.":
#                 validacao = False
#             else:
#                 validacao = False
#             match validacao:
#                 case True:
#                     return idade
#                 case False:
#                     print(mensagem)

#         except ValueError:
#             print("Digite apenas números.")

# idade = ler_idade()
# print(f"Idade válida: {idade}")

# # Desafio 6

# def validar_idade(idade):
#     if idade < 18:
#         return False, "A idade minima é 18 anos."
#     elif idade > 120:
#         return False, "A idade maxima é 120 anos."
#     else:
#         return True, "Idade válida."

# def ler_idade():
#     while True:
#         try:
#             idade = int(input("Digite a sua idade: "))
#             valido, mensagem = validar_idade(idade)
#             if valido:
#                 return idade
#             else:
#                 print(mensagem)

#         except ValueError:
#             print("Digite apenas numeros.")

# # Desafio 7

# def validar_nome(nome):
#     leitura = len(nome)
#     if leitura >= 3:
#         return True, "Nome, válido."
#     elif leitura == 0:
#         return False, "O nome não pode estar vazio."
#     else:
#         return False, "O nome deve ter pelo menos 3 caracteres."

# def ler_nome():
#     while True:
#             nome = input("Digite o seu nome: ")
#             valido, mensagem = validar_nome(nome)
#             if valido:
#                 return nome
#             else:
#                 print(mensagem)


# # Desafio 8
# def cadastrar_usuario():
#     nome = ler_nome()
#     idade = ler_idade()
#     usuario = {"nome": nome, "idade": idade}

#     return usuario

# # Desafio 9
# def cadastrar_usuarios():
#     usuarios = []
#     while True:
#         print("\n=== Cadastro de Usuarios ===\n")
#         resposta = input("Deseja adicionar um usuário? (s/n): ").lower()

#         if resposta == 's':
#             usuarios.append(cadastrar_usuario())
#         elif resposta == 'n':
#             print(usuarios)
#             break
#         else:
#             print("Opção inválida, tente novamente.")

# # Desafio 10

# def listar_usuarios(usuarios):
#     for usuario in usuarios:
#         print(f"Nome: {usuario['nome']}\nIdade: {usuario['idade']}")

# def buscar_usuario(usuarios, nome):
#     for usuario in usuarios:
#         if nome == usuario["nome"]:
#             return True, usuario
#     else:
#         return False, usuario


# def sistema_usuario():
#     usuarios = []

#     while True:
#         print("\n=== SISTEMA DE USUÁRIOS ===\n")
#         print("""
# 1 - Cadastrar usuário
# 2 - Listar usuários
# 3 - Buscar usuário
# 4 - Sair
# """)
#         resposta = input("escolha uma opção: (1 a 4)")

#         if resposta == '1':
#             usuarios.append(cadastrar_usuario())
#         elif resposta == '2':
#             listar_usuarios(usuarios)
#         elif resposta == '3':
#             nome = input("Digite o nome a ser buscado: ")
#             valido, retorno = buscar_usuario(usuarios, nome)
#             if valido == False:
#                 print("Usuario não encontrado.")
#             else:
#                 print(f"Nome: {retorno}")
#         elif resposta == '4':
#             print("Encerrando cadastro...")
#             break
#         else:
#             print("Digite uma opeção válida, tente novamente.;")

# sistema_usuario()