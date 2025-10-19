// Manejo del formulario Simplex
document.getElementById('simplexForm').addEventListener('submit', function(e) {
    e.preventDefault();
    solveSimplex();
});

// Actualizar coeficientes cuando cambia el número de variables
document.getElementById('varCount').addEventListener('change', function() {
    updateObjectiveCoefficients();
    updateConstraints();
});

function updateObjectiveCoefficients() {
    const varCount = parseInt(document.getElementById('varCount').value);
    const container = document.getElementById('objectiveCoefficients');
    container.innerHTML = '';
    
    for (let i = 0; i < varCount; i++) {
        const input = document.createElement('input');
        input.type = 'number';
        input.className = 'form-control mb-1';
        input.placeholder = `Coef x${i+1}`;
        input.required = true;
        container.appendChild(input);
    }
}

function updateConstraints() {
    const varCount = parseInt(document.getElementById('varCount').value);
    const constraints = document.querySelectorAll('.constraint');
    
    constraints.forEach(constraint => {
        const coefficientsContainer = constraint.querySelector('.row');
        coefficientsContainer.innerHTML = '';
        
        for (let i = 0; i < varCount; i++) {
            const col = document.createElement('div');
            col.className = 'col-4';
            if (i > 0) col.className = 'col-4 mt-1';
            
            const input = document.createElement('input');
            input.type = 'number';
            input.className = 'form-control';
            input.placeholder = `Coef x${i+1}`;
            input.required = true;
            
            col.appendChild(input);
            coefficientsContainer.appendChild(col);
        }
        
        // Agregar operador y RHS
        const operatorCol = document.createElement('div');
        operatorCol.className = 'col-2';
        const operatorSelect = document.createElement('select');
        operatorSelect.className = 'form-select';
        operatorSelect.innerHTML = `
            <option value="<=">&lt;=</option>
            <option value=">=">&gt;=</option>
            <option value="==">=</option>
        `;
        operatorCol.appendChild(operatorSelect);
        coefficientsContainer.appendChild(operatorCol);
        
        const rhsCol = document.createElement('div');
        rhsCol.className = 'col-2';
        const rhsInput = document.createElement('input');
        rhsInput.type = 'number';
        rhsInput.className = 'form-control';
        rhsInput.placeholder = 'RHS';
        rhsInput.required = true;
        rhsCol.appendChild(rhsInput);
        coefficientsContainer.appendChild(rhsCol);
    });
}

function addConstraint() {
    const varCount = parseInt(document.getElementById('varCount').value);
    const container = document.getElementById('constraintsContainer');
    
    const constraintDiv = document.createElement('div');
    constraintDiv.className = 'constraint mb-2';
    
    let coefficientsHTML = '<div class="row">';
    for (let i = 0; i < varCount; i++) {
        coefficientsHTML += `
            <div class="col-4 ${i > 0 ? 'mt-1' : ''}">
                <input type="number" class="form-control" placeholder="Coef x${i+1}" required>
            </div>
        `;
    }
    coefficientsHTML += `
        <div class="col-2">
            <select class="form-select">
                <option value="<=">&lt;=</option>
                <option value=">=">&gt;=</option>
                <option value="==">=</option>
            </select>
        </div>
        <div class="col-2">
            <input type="number" class="form-control" placeholder="RHS" required>
        </div>
    </div>`;
    
    constraintDiv.innerHTML = coefficientsHTML;
    container.appendChild(constraintDiv);
}

async function solveSimplex() {
    const form = document.getElementById('simplexForm');
    const resultsContainer = document.getElementById('resultsContainer');
    
    try {
        form.classList.add('loading');
        resultsContainer.innerHTML = '<div class="text-center"><div class="spinner-border"></div><p class="mt-2">Resolviendo...</p></div>';
        
        // Recopilar datos del formulario
        const varCount = parseInt(document.getElementById('varCount').value);
        const objectiveType = document.getElementById('objectiveType').value;
        
        // Coeficientes objetivo
        const objectiveCoefficients = [];
        const objectiveInputs = document.querySelectorAll('#objectiveCoefficients input');
        objectiveInputs.forEach(input => {
            objectiveCoefficients.push(parseFloat(input.value));
        });
        
        // Restricciones - VERSIÓN MEJORADA
        const constraints = [];
        const constraintElements = document.querySelectorAll('.constraint');
        
        constraintElements.forEach((constraint, index) => {
            const coefficients = [];
            const inputs = constraint.querySelectorAll('input[type="number"]');
            
            // Todos los inputs excepto el último (RHS)
            for (let i = 0; i < inputs.length - 1; i++) {
                coefficients.push(parseFloat(inputs[i].value));
            }
            
            const operator = constraint.querySelector('select').value;
            const rhs = parseFloat(inputs[inputs.length - 1].value);
            
            constraints.push({
                coefficients: coefficients,
                type: operator,
                rhs: rhs
            });
        });
        
        console.log('Enviando datos:', {
            var_count: varCount,
            objective: { type: objectiveType, coefficients: objectiveCoefficients },
            constraints: constraints
        });
        
        // Enviar solicitud con mejor manejo de errores
        const response = await fetch('/api/solve_simplex', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                var_count: varCount,
                objective: {
                    type: objectiveType,
                    coefficients: objectiveCoefficients
                },
                constraints: constraints
            })
        });
        
        // Verificar si la respuesta es JSON
        const contentType = response.headers.get('content-type');
        if (!contentType || !contentType.includes('application/json')) {
            const text = await response.text();
            console.error('Respuesta no JSON:', text.substring(0, 200));
            throw new Error(`El servidor devolvió HTML en lugar de JSON. ¿La ruta /api/solve_simplex existe?`);
        }
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || `Error HTTP: ${response.status}`);
        }
        
        if (data.error) {
            throw new Error(data.error);
        }
        
        // Mostrar resultados
        displaySimplexResults(data);
        
    } catch (error) {
        console.error('Error completo:', error);
        resultsContainer.innerHTML = `
            <div class="alert alert-danger">
                <h5>Error al resolver</h5>
                <strong>Detalles:</strong> ${error.message}
                <br><br>
                <small>Verifica la consola (F12) para más información</small>
            </div>
        `;
    } finally {
        form.classList.remove('loading');
    }
}
async function solveGraphical() {
    const form = document.getElementById('graphicalForm');
    const resultsContainer = document.getElementById('resultsContainer');
    
    try {
        form.classList.add('loading');
        resultsContainer.innerHTML = '<div class="text-center"><div class="spinner-border"></div><p class="mt-2">Generando gráfico...</p></div>';
        
        // Recopilar datos
        const objectiveType = document.getElementById('objectiveType').value;
        const objectiveCoeff1 = parseFloat(document.getElementById('objCoeff1').value);
        const objectiveCoeff2 = parseFloat(document.getElementById('objCoeff2').value);
        
        // Restricciones
        const constraints = [];
        const constraintElements = document.querySelectorAll('.constraint');
        
        constraintElements.forEach((constraint) => {
            const coeff1 = parseFloat(constraint.querySelector('.coeff1').value);
            const coeff2 = parseFloat(constraint.querySelector('.coeff2').value);
            const operator = constraint.querySelector('.operator').value;
            const rhs = parseFloat(constraint.querySelector('.rhs').value);
            
            constraints.push({
                coefficients: [coeff1, coeff2],
                type: operator,
                rhs: rhs
            });
        });
        
        // Enviar solicitud
        const response = await fetch('/api/solve_graphical', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                objective: {
                    type: objectiveType,
                    coefficients: [objectiveCoeff1, objectiveCoeff2]
                },
                constraints: constraints
            })
        });
        
        const data = await response.json();
        
        if (data.error) {
            throw new Error(data.error);
        }
        
        // Mostrar resultados con gráfico
        displayGraphicalResults(data);
        
    } catch (error) {
        resultsContainer.innerHTML = `
            <div class="alert alert-danger">
                <strong>Error:</strong> ${error.message}
            </div>
        `;
    } finally {
        form.classList.remove('loading');
    }
}

function displayGraphicalResults(data) {
    const resultsContainer = document.getElementById('resultsContainer');
    
    let html = `
        <div class="alert alert-success">
            <h5>Problema Resuelto Exitosamente</h5>
            <p><strong>Estado:</strong> ${data.status}</p>
    `;
    
    if (data.status === 'Optimal') {
        html += `
            <p><strong>Valor Óptimo:</strong> ${data.objective_value.toFixed(2)}</p>
            <p><strong>Solución Óptima:</strong> x₁ = ${data.variables.x1.toFixed(2)}, x₂ = ${data.variables.x2.toFixed(2)}</p>
        `;
    }
    
    html += `</div>`;
    
    if (data.plot && data.plot !== "base64_placeholder") {
        html += `
            <div class="result-item">
                <h6>Visualización Gráfica:</h6>
                <div class="text-center">
                    <img src="${data.plot}" alt="Gráfico de Programación Lineal" class="img-fluid" style="max-width: 100%; height: auto;">
                </div>
            </div>
        `;
    } else {
        html += `
            <div class="alert alert-warning">
                No se pudo generar el gráfico. Los datos pueden ser inválidos.
            </div>
        `;
    }
    
    resultsContainer.innerHTML = html;
}

function displaySimplexResults(data) {
    const resultsContainer = document.getElementById('resultsContainer');
    
    let html = `
        <div class="alert alert-success">
            <h5>Problema Resuelto Exitosamente</h5>
            <p><strong>Estado:</strong> ${data.status}</p>
            <p><strong>Valor Óptimo:</strong> ${data.objective_value.toFixed(2)}</p>
        </div>
        
        <div class="result-item optimal-solution">
            <h6>Variables de Decisión Óptimas:</h6>
            <ul class="list-unstyled">
    `;
    
    for (const [varName, value] of Object.entries(data.variables)) {
        html += `<li><strong>${varName}:</strong> ${value.toFixed(4)}</li>`;
    }
    
    html += `
            </ul>
        </div>
        
        <div class="result-item">
            <h6>Análisis de Restricciones:</h6>
            <table class="table table-sm">
                <thead>
                    <tr>
                        <th>Restricción</th>
                        <th>Holgura</th>
                        <th>Precio Sombra</th>
                    </tr>
                </thead>
                <tbody>
    `;
    
    for (const [constrName, constrData] of Object.entries(data.constraints)) {
        html += `
            <tr>
                <td>${constrName}</td>
                <td>${constrData.slack.toFixed(4)}</td>
                <td>${constrData.shadow_price.toFixed(4)}</td>
            </tr>
        `;
    }
    
    html += `
                </tbody>
            </table>
        </div>
    `;
    
    resultsContainer.innerHTML = html;
}