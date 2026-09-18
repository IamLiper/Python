# # Desafio 1

# frutas = ["Maça", "Banana", "Laranja", "Uva"]

# print(f"Lista inicial: {frutas}")
# print(f"Primeira fruta: {frutas[0]}")
# frutas.append("Manga")
# frutas.remove("Banana")
# alterar = frutas.index("Laranja")
# frutas[alterar] = "Abacaxi"

# print(f"Lista Final: {frutas}")

# # Desafio 2

# configuracao_tela = (
#     "1920",
#     "1080",
#     "60"
# )

# print(f"Largura: {configuracao_tela[0]}\nAltura: {configuracao_tela[1]}\nFPS: {configuracao_tela[2]}")
# print(f"Largura: {configuracao_tela[0]}")
# print(f"FPS: {configuracao_tela[2]}")
# configuracao_tela.append("2560")

# # Desafio 3

# configuracao_tela = (1920, 1080, 60)
# configuracao_nova = (2560, 1080, 144)

# print(f"COnfiguração antiga: {configuracao_tela}")
# print(f"Configuração nova: {configuracao_nova}")


# # Desafio 4

# usuario = {
#     "nome": "Felipe",
#     "idade": 19,
#     "cidade": "Salvador",
#     "profissao": "Programador",
# }

# print(usuario["nome"])
# print(usuario["profissao"])
# usuario["idade"] = 20
# usuario["linguagem"] = "Python"
# print(usuario)

# # Desafio 5

# usuarios = [
#     {
#         "nome": "Felipe",
#         "idade": 20,
#         "profissao": "Programador"
#     },

#     {
#         "nome": "Maria",
#         "idade": 25,
#         "profissao": "Designer"
#     },

#     {
#         "nome": "João",
#         "idade": 30,
#         "profissao": "Engenheiro"
#     }
# ]

# print(usuarios[0]["nome"])
# print(usuarios[1]["profissao"])
# usuarios[2]["idade"] = 24
# usuarios[0]["linguagem"] = "Python"
# print(usuarios)
# print(f'Somente nomes: Nome 1 {usuarios[0]["nome"]}, Nome 2 {usuarios[1]["nome"]}, Nome 3 {usuarios[2]["nome"]}')

# # Desafio 6

# usuarios = [
#     {"nome": "Felipe", "idade": 20, "profissao": "Programador"},
#     {"nome": "Maria", "idade": 25, "profissao": "Designer"},
#     {"nome": "João", "idade": 24, "profissao": "Engenheiro"}
# ]

# for usuario in usuarios:
#     print(f'\nNome: {usuario["nome"]}\nIdade: {usuario["idade"]}\nProfissão: {usuario["profissao"]}')

# # Desafio 7

# usuarios = [
#     {"nome": "Felipe", "idade": 20, "profissao": "Programador"},
#     {"nome": "Maria", "idade": 25, "profissao": "Designer"},
#     {"nome": "João", "idade": 24, "profissao": "Engenheiro"},
#     {"nome": "Ana", "idade": 17, "profissao": "Estudante"}
# ]

# for usuario in usuarios:
#     if usuario["idade"] > 18:
#         print(f'Nome: {usuario["nome"]} - Idade: {usuario["idade"]} anos')

# # Desadio 8

# usuarios = [
#     {"nome": "Felipe", "idade": 20, "profissao": "Programador"},
#     {"nome": "Maria", "idade": 25, "profissao": "Designer"},
#     {"nome": "João", "idade": 24, "profissao": "Engenheiro"},
#     {"nome": "Ana", "idade": 17, "profissao": "Estudante"}
# ]

# pesquisa = input("Digite o nome que procura: ")

# for usuario in usuarios:
#     if pesquisa == usuario["nome"]:
#         print("Usuário encontrado!")
#         print(f'Nome: {usuario["nome"]}\nIdade: {usuario["idade"]}\nProfissão: {usuario["profissao"]}')
#         break
# else:
#     print("Usuário não encontrado!")

# # Desafio 9

# usuarios = [
#     {"nome": "Felipe", "idade": 20, "profissao": "Programador"},
#     {"nome": "Maria", "idade": 25, "profissao": "Designer"},
#     {"nome": "João", "idade": 24, "profissao": "Engenheiro"},
#     {"nome": "Ana", "idade": 17, "profissao": "Estudante"}
# ]

# def buscar_usuario(usuarios, nome):
#     for usuario in usuarios:
#         if nome == usuario["nome"]:
#             return usuario
#     else:
#         return None

# nome = input("Digite o nome que procura: ")

# print(buscar_usuario(usuarios, nome))

# # Desafio 10

# usuarios = [
#     {"nome": "Felipe", "idade": 20, "profissao": "Programador"},
#     {"nome": "Maria", "idade": 25, "profissao": "Designer"},
#     {"nome": "João", "idade": 24, "profissao": "Engenheiro"},
#     {"nome": "Ana", "idade": 17, "profissao": "Estudante"},
#     {"nome": "José", "idade": 27, "profissao": "Programador"}
# ]

# def buscar_por_profissao(usuarios, profissao):
#     encontrados = []
#     for usuario in usuarios:
#         if profissao == usuario["profissao"]:
#             encontrados.append(usuario)
#     return encontrados

# profissao = input("Digite a profissão que deseja buscar: ")

# print(buscar_por_profissao(usuarios, profissao))