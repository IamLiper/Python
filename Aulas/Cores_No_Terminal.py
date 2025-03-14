nome = "Lipe"
cores = {
    "limpa": "\033[0m",
    "pretoebranco": "\033[30;47m",
    "azul": "\033[34m",
    "amarelo": "\033[33m"
}

print("Olá! Muito prazer em te conhecer, {}{}{}!!".format(cores['azul'],nome, cores['limpa']))