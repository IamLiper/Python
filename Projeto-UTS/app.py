from flask import Flask, request, jsonify, send_from_directory
from database import GerenciadorEquipes
import os

app = Flask(__name__)
gerenciador = GerenciadorEquipes()

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/style.css')
def css():
    return send_from_directory('.', 'style.css')

@app.route('/script.js')
def js():
    return send_from_directory('.', 'script.js')

@app.route('/add_member', methods=['POST'])
def add_member():
    data = request.json
    try:
        gerenciador.adicionar_membro(
            data['name'],
            data.get('phone', ''),
            'Treinamento Kelly'  # ou data['team'] se quiser permitir escolha
        )
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/get_trainees')
def get_trainees():
    trainees = gerenciador.listar_equipe('Treinamento Kelly')
    return jsonify(trainees)

if __name__ == '__main__':
    app.run(debug=True)