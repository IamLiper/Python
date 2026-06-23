def minha_funcao(valor1, valor2):
    return valor1 + valor2

while True:
    valor1 = input("Digite o primeiro valor: ")
    valor2 = input("Digite o segundo valor: ")
    
    resposta = minha_funcao(int(valor1), int(valor2))
    print(valor1, "+", valor2, "=", resposta)