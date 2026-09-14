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

# def menor_numero(lista):
#     if not lista:
#         return None
#     menor = lista[0]
#     for numero in lista:
#         if numero < menor:
#             menor = numero
#     return menor

# def media_numeros(lista):
#     if not lista:
#         return None
#     soma = 0
#     contador = 0
#     for numero in lista:
#         soma += numero
#         contador += 1
#     media = soma / contador
#     return media
    

# def calcular_estatisticas(lista):
#     if not lista:
#         return None
#     maior = maior_numero(lista)
#     menor = menor_numero(lista)
#     media = media_numeros(lista)

#     return maior, menor, media

# numeros = [10, 20, 5, 40, 25]

# resultado = calcular_estatisticas(numeros)

# print(f"Maior número: {resultado[0]}\nMenor número: {resultado[1]}\nMédia dos números: {resultado[2]:.2f}")