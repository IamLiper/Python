largura = float(input("Qual a largura da parede? "))
altura = float(input("Qual a altura da parede? "))

area = largura * altura
tinta = area / 2

print("Para pintar uma area de {:.2f}m é necessário {:.2f}L de tinta".format(area, tinta))