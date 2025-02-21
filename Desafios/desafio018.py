from math import cos, sin, tan, radians
angulo = float(input("Digite um ângulo: "))

radiacao = radians(angulo)

seno = sin(radiacao)
cosseno = cos(radiacao)
tangente = tan(radiacao)

print("Esses são os Cosseno {:.4f}, tangente {:.4f} e seno {:.4f} do angulo {}".format(cosseno, tangente, seno, angulo))