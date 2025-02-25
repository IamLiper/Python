distancia = int(input("Digite a distância da viagem em Km: "))
if distancia >= 200:
    print("Você vai pagar R${} em {}Km".format(distancia * 0.45, distancia))
else:
    print("Você vai pagar R${} em {}Km".format(distancia * 0.5, distancia))