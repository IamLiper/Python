nome = "Débora"
idade = 18
peso = 72.5

print(f"Formatos de saida")

#Forma antiga
print("%s tem %d de idade e pesa %.1f kg" % (nome, idade, peso))

#Forma nova
print("{} tem {} de idade e pesa {:.1f} kg.".format(nome, idade, peso))

#Forma nova da nova
print(f"{nome} tem {idade} de idade e pesa {peso:.1f} kg.")