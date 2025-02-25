salario = float(input("Digite seu sálario: "))
if salario >= 1250:
    aumento = salario * 0.10
    print("Seu novo sálario é R${} com o aumento de R${}!".format(salario + aumento, aumento))
else:
    aumento = salario * 0.15
    print("Seu novo salário é R${} com o aumento de R${}!".format(salario + aumento, aumento))