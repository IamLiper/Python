# utils/chart.py

import matplotlib.pyplot as plt
import json
import os

def gerar_grafico_lucro(arquivo_json="scheduler/earnings.json", output_path="scheduler/lucro_semanal.png"):
    if not os.path.exists(arquivo_json):
        return None

    with open(arquivo_json, "r") as f:
        dados = json.load(f)

    if len(dados) < 2:
        return None

    datas = list(dados.keys())[-7:]
    valores = [dados[d] for d in datas]

    plt.figure(figsize=(8, 4))
    plt.plot(datas, valores, marker='o', linestyle='-', color='lime')
    plt.title("Lucro Líquido Diário")
    plt.ylabel("USDT")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()

    return output_path
