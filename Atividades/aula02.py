# # Desafio 1

# def saudacao():
#     print("Olá! Seja bem-vindo ao programa!")

# saudacao()
# saudacao()
# saudacao()

# # Desafio 2

# def saudacao(nome):
#     print(f"Olá, {nome}!")

# nome = input("Digite o seu nome: ")
# saudacao(nome)

# # Desafio 3

# def tabuada(numero):
#     for i in range(1, 11):
#         resultado = numero * i
#         print(f"{numero} x {i} = {resultado}")

# numero = int(input("Digite um número: "))
# tabuada(numero)

# # Desafio 4

# def soma_print(a, b):
#     resultado = a + b
#     print(resultado)

# def soma_return(a, b):
#     resultado = a + b
#     return resultado

# resultado1 = soma_print(10, 5)
# resultado2 = soma_return(10, 5)

# print(resultado1)
# print(resultado2)

# # Desafio 5

# def tabuada(numero):
#     resultados = []
#     for i in range(1, 11):
#         resultado = numero * i
#         resultados.append(f"{numero} x {i} = {resultado}")
#     return resultados

# resultado = tabuada(5)
# print(resultado)

# # Desafio 6

# def maior_numero(lista):
#     if not lista:
#         return None
#     maior = lista[0]
#     for numero in lista:
#         if numero > maior:
#             maior = numero
#     return maior


# numeros = [10, 25, 7, 42, 18]

# resultado = maior_numero(numeros)

# print(resultado)

# # Desafio 7

# def contar_pares(lista):
#     contador = 0
#     pares = []
#     if not lista:
#         return None
#     par = lista[0]
#     for numero in lista:
#         if numero % 2 == 0:
#             pares.append(numero)
#             contador += 1
#     return contador, pares

# numeros = [1, 2, 4, 7, 8, 10]

# resultado = contar_pares(numeros)

# print(f"Quantidade de pares {resultado[0]}, pares: {resultado[1]}")

# # Desafio 8

# def calcular_estatisticas(lista):
#     maior = 0
#     menor = 0
#     soma = 0
#     contador = 0
#     if not lista:
#         return None
#     maior = lista[0]
#     menor = lista[0]
#     for numero in lista:
#         if numero > maior:
#             maior = numero
#         if numero < menor:
#             menor = numero
#         contador += 1
#         soma += numero
#     media = soma / contador if contador > 0 else 0

#     return maior, menor, media

# numeros = [10, 20, 5, 40, 25]

# resultado = calcular_estatisticas(numeros)

# print(f"Maior número: {resultado[0]}\nMenor número: {resultado[1]}\nMédia dos números: {resultado[2]:.2f}")

# # Desafio 9

# numero = 20

# def teste():
#     numero = 10
#     print("Dentro:", numero)

# teste()

# print("Fora:", numero)

# # Desafio 10

# numero = 20

# def teste():
#     numero = 10
#     return numero

# resultado = teste()

# print("Resultado:", resultado)
# print("Fora:", numero)

# # desafio 11

# numero = 100

# def calcular(numero):
#     numero = numero * 2
#     return numero

# resultado = calcular(10)

# print("Resultado:", resultado)
# print("Numero:", numero)

# # Desafio 12

# numero = 10

# def teste(numero):
#     numero += 5
#     return numero

# numero = teste(numero)

# print(numero)

# # Desafio 13

# saldo = 100

# def depositar(saldo, valor):
#     saldo += valor
#     return saldo

# depositar(saldo, 50)

# print(saldo)

# # Desafio 14

# def adicionar(a, b):
#     resultado = a + b
#     return resultado

# x = 10
# y = 20

# x = adicionar(x, y)

# print(x)
# print(y)

# # Desafio 15

# def cumprimentar(nome, mensagem="Olá"):
#     return f"{mensagem}, {nome}!"

# print(cumprimentar("Felipe"))
# print(cumprimentar("Felipe", "Bom dia"))

# # Desafio 16

# def apresentar(nome, idade=20, cidade="Salvador"):
#     return f"{nome} tem {idade} anos e mora em {cidade}."

# print(apresentar("João"))
# print(apresentar("Maria", 25))
# print(apresentar("Carlos", 30, "Recife"))

# # Desafio 17

# def produto(nome, preco, quantidade=1):
#     total = preco * quantidade
#     return f"{quantidade}x {nome} = R${total:.2f}"

# print(produto("Mouse", 50))
# print(produto("Teclado", 100, 2))
# print(produto(nome="Monitor", preco=800, quantidade=2))

# # Desafio 18

# def somar_todos(*numeros):
#     soma = 0
#     for numero in numeros:
#         soma += numero
#     resultado = soma
#     return resultado

# print(somar_todos(10, 20))
# print(somar_todos(1, 2, 3, 4, 5))
# print(somar_todos(100, 50, 25, 10))

# # Desafio 19

# def contar_maiores_que(limite, *numeros):
#     contador = 0
#     for numero in numeros:
#         if numero > limite:
#             contador += 1
#     return contador

# print(contar_maiores_que(10, 5, 15, 20, 8, 12))

# # Desafio 20

# def mostrar_dados(**dados):
#     for chave, valor in dados.items():
#         print(f"{chave}: {valor}")
    

# mostrar_dados(nome="Felipe", idade=20, cidade="Salvador")