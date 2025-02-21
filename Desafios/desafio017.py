from math import sqrt
cateto1 = float(input("Digite o valor do cateto 1: "))
cateto2 = float(input("Digite o valor do cateto 2: "))

hipotenusa = sqrt(cateto1*cateto1 + cateto2*cateto2)

print("A hipotenusa de catetoA {} e catetoB {} é {:.2f}".format(cateto1, cateto2, hipotenusa))