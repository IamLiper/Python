n1 = int(input("Digite o primeiro número: "))  
n2 = int(input("Digite o segundo número: "))  
n3 = int(input("Digite o terceiro número: "))
if n1 > n2 and n1 > n3:
    print("O número {} é o maior!".format(n1))
if n2 > n1 and n2 > n3:
    print("O número {} é o maior!".format(n2))
else:
    print("O número {} é o maior!".format(n3))