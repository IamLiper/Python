valor = int(input("Digite um valor: "))

print("==== Tabuada de {} ====".format(valor))
for conta in range(10):
    print("{} x {} = {}".format(valor, conta+1, valor * (conta + 1)))