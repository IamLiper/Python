// Wait for DOM content to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
    // Get form elements
    const form = document.querySelector('form');
    const loginInput = document.querySelector('#login');
    const passwordInput = document.querySelector('#password');

    // Form submission handler
    if (form) {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            
            // Get input values
            const login = loginInput.value.trim();
            const password = passwordInput.value.trim();

            // Basic validation
            if (!login || !password) {
                alert('Por favor, preencha todos os campos!');
                return;
            }

            // Here you can add your login logic
            // For example:
            validateLogin(login, password);
        });
    }

    // Example validation function
    function validateLogin(login, password) {
        // Add your authentication logic here
        // This is just a basic example
        if (login === "admin" && password === "admin123") {
            alert('Login realizado com sucesso!');
            // Redirect or perform other actions
        } else {
            alert('Login ou senha inválidos!');
        }
    }

    const memberForm = document.getElementById('memberForm');
    const traineeTable = document.getElementById('traineeTable').getElementsByTagName('tbody')[0];
    const completedTable = document.getElementById('completedTable').getElementsByTagName('tbody')[0];
    const officialsTable = document.getElementById('officialsTable').getElementsByTagName('tbody')[0];

    memberForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const name = document.getElementById('name').value;
        const role = document.getElementById('role').value;

        // Enviar dados para o backend
        fetch('/add_member', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                name: name,
                role: role
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                updateTables();
                memberForm.reset();
            } else {
                alert('Erro ao adicionar membro: ' + data.error);
            }
        });
    });

    function updateTables() {
        // Atualizar tabela de trainees
        fetch('/get_trainees')
            .then(response => response.json())
            .then(data => {
                traineeTable.innerHTML = data.map(trainee => `
                    <tr>
                        <td>${trainee.name}</td>
                        <td>${trainee.recruited}</td>
                        <td>${trainee.instagram}</td>
                        <td>${trainee.prints}</td>
                        <td>${trainee.status}</td>
                    </tr>
                `).join('');
            });

        // Atualizar outras tabelas similarmente
    }

    // Carregar dados iniciais
    updateTables();
});