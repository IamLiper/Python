d = int(input("Por quantos dias você alugou? "))
km = float(input("Quantos km você rodou? "))

valorTotal = (60 * d) + (km * 0.15)

print("O total a pagar é R${:.2f}".format(valorTotal))