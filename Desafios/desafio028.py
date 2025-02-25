from random import randint
escolha = int(input("Advinhe um número entre 0 e 5: "))
escolhaCp = randint(0, 5)
if escolha == escolhaCp:
    print("Sua escolha foi {} e a do computador foi {}, Você venceu, parabéns!".format(escolha, escolhaCp))
else:
    print("Sua escolha foi {} e a do computador foi {}, O computador venceu, mais sorte na próxima!".format(escolha, escolhaCp))