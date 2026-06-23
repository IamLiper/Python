notas = []

contador = 1

while contador <=5:
    id_aluno = input("ID: ")
    nota = float(input("Nota: "))
    resultado = (id_aluno, nota)
    notas.append(resultado)
    
    contador += 1

    print("Quantidade de notas: ", len(notas))