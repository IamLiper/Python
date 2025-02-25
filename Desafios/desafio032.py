ano = int(input("Digite o ano: "))
if ano % 4 == 0:
    print("O ano {} é um ano Bissexto!".format(ano))
else:
    print("O ano {} nao é um ano Bissexto!".format(ano))