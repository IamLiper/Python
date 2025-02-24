numero = input("Digite um numero de 0 a 9999: ")
numero.split()

unidade = numero[3]
dezena = numero[2]
centena = numero[1]
milhar = numero[0]

print("""
Unidade = {}
Dezena = {}
Centena = {}
Milhar = {}""".format(unidade, dezena, centena, milhar))