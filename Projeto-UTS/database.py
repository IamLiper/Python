class GerenciadorEquipes:
    def __init__(self):
        self.equipes = {'Treinamento Kelly': []}

    def adicionar_membro(self, nome, telefone, equipe):
        if equipe not in self.equipes:
            raise ValueError("Equipe não existe")
        self.equipes[equipe].append({
            'name': nome,
            'phone': telefone
        })

    def listar_equipe(self, equipe):
        return self.equipes.get(equipe, [])