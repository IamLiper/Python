nome_completo = input("Insira o seu nome: ")
apelido = nome_completo.split()

firstN = apelido[0]
lastN = apelido[-1]

print('Primeiro nome: {}, Segundo nome: {}'.format(firstN, lastN))