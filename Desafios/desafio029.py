velocidade = int(input("Qual a velocidade do carro? "))
if velocidade > 80:
    print("Você foi multado em R${}, por exerder o limite de velocidade acima dos 80Km/h, vc estava em {}Km/h".format((velocidade - 80) * 7, velocidade))