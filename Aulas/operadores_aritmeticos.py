n1 = int(input("Digite o primeiro valor: "))
n2 = int(input("Digite o segundo valor: "))

s = n1 + n2
m = n1 * n2
d = n1 / n2
di = n1 // n2
e = n1 ** n2

print("A soma é: {}\nA multiplicação é: {}\nA divisão é: {:.3f}".format(s, m, di),)
print("A divisão inteira é {}\nA potencia é: {}".format(di, e))