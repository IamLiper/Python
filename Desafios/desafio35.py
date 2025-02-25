reta1 = float(input("Digite a primeira reta em cm: "))
reta2 = float(input("Digite a segunda reta em cm: "))
reta3 = float(input("Digite a terceira reta em cm: "))


if reta1 < reta2 + reta3 and reta2 < reta1 + reta3 and reta3 < reta1 + reta2:
    print("Um triângulo poderá ser feito!")
else:
    print("Um triângulo não poderá ser feito!")