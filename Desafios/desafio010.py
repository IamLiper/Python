valor = float(input("Digite o valor da sua carteira em real: R$"))

conversao = valor / 3.27

print("Com R${} você consegue comprar US${:.2f}".format(valor, conversao))