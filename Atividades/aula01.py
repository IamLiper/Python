# Desafio 1
nome = input("Digite o seu nome: ")
idade = input("Digite a sua idade: ")

print(f"Olá {nome}!\nVocê tem {idade} anos.")

# Desafio 2
num1 = int(input("Digite o primeiro número: "))
num2 = int(input("Digite o segundo número: "))

if num1 > num2:
    print(f"Maior: {num1}")
    print(f"Menor: {num2}")
else:
    print(f"Maior: {num2}")
    print(f"Menor: {num1}")
# Desafio 3
nota = float(input("Digite a nota do aluno: "))

if nota >= 7:
    print("Aprovado")
elif nota >= 5:
    print("Recuperação")
else:
    print("Reprovado")

# Desafio 4
tabuada = int(input("Digite um número para ver a tabuada: "))
for i in range(1, 11):
    resultado = tabuada * i
    print(f"{tabuada} x {i} = {resultado}")

# Desafio 5
numeros = []
while True:
    try:
        numero = int(input("Digite um número (ou '0' para encerrar): "))
        if numero == 0 and len(numeros) == 0:
            print("Você deve digitar pelo menos um número antes de encerrar.")
        elif numero != 0:
            numeros.append((numero))
            print(numeros)
        else:
            break

    except ValueError:
        print("Entrada inválida. Por favor, digite apenas números.")

media = sum(numeros) / len(numeros)
print("\nQuantidade de números: ", len(numeros))
print("Soma dos números: ", sum(numeros))
print("Maior número: ", max(numeros))
print("Menor número: ", min(numeros))
print(f"Média dos números: {media:.2f}")