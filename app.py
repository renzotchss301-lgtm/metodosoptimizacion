from flask import Flask, render_template, request, jsonify
import pulp
import json

app = Flask(__name__, static_folder='static', template_folder='templates')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/custom')
def custom():
    return render_template('custom.html')

@app.route('/simplex')
def simplex():
    return render_template('simplex.html')

@app.route('/transport')
def transport():
    return render_template('transport.html')

@app.route('/assignment')
def assignment():
    return render_template('assignment.html')

@app.route('/graphical')
def graphical():
    return render_template('graphical.html')

# API existente para problemas personalizados
@app.route('/api/solve_custom', methods=['POST'])
def solve_custom():
    try:
        data = request.json
        
        # Crear problema
        if data['objective_type'] == 'maximize':
            problem = pulp.LpProblem("Problema_Personalizado", pulp.LpMaximize)
        else:
            problem = pulp.LpProblem("Problema_Personalizado", pulp.LpMinimize)
        
        # Crear variables
        var_count = int(data['var_count'])
        variables = []
        for i in range(var_count):
            var_name = f"x{i+1}"
            variables.append(pulp.LpVariable(var_name, lowBound=0))
        
        # Función objetivo
        obj_expr = 0
        for i, coef in enumerate(data['objective_coeffs']):
            obj_expr += coef * variables[i]
        problem += obj_expr
        
        # Restricciones
        for constraint in data['constraints']:
            constr_expr = 0
            for i, coef in enumerate(constraint['coefficients']):
                constr_expr += coef * variables[i]
            
            if constraint['type'] == '<=':
                problem += constr_expr <= constraint['rhs']
            elif constraint['type'] == '>=':
                problem += constr_expr >= constraint['rhs']
            else:
                problem += constr_expr == constraint['rhs']
        
        # Resolver
        problem.solve()
        
        # Preparar resultados
        results = {
            'status': pulp.LpStatus[problem.status],
            'objective_value': pulp.value(problem.objective),
            'variables': {},
            'constraints': {},
            'constraint_usage': {}
        }
        
        # Valores de variables
        for var in variables:
            results['variables'][var.name] = var.varValue
        
        # Información de restricciones
        constraint_names = [f"Restricción_{i+1}" for i in range(len(data['constraints']))]
        
        for i, (name, constraint) in enumerate(zip(constraint_names, problem.constraints.values())):
            # Calcular uso del recurso
            used = 0
            for j, coef in enumerate(data['constraints'][i]['coefficients']):
                used += coef * variables[j].varValue
            
            results['constraints'][name] = {
                'slack': constraint.slack,
                'shadow_price': constraint.pi
            }
            
            results['constraint_usage'][name] = {
                'used': used,
                'available': data['constraints'][i]['rhs']
            }
        
        return jsonify(results)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400

# AGREGA ESTA RUTA DESPUÉS DE solve_custom Y ANTES DE solve_transport
@app.route('/api/solve_simplex', methods=['POST'])
def solve_simplex():
    try:
        data = request.get_json()
        
        # Crear problema
        if data['objective']['type'] == 'maximize':
            problem = pulp.LpProblem("Problema_Simplex", pulp.LpMaximize)
        else:
            problem = pulp.LpProblem("Problema_Simplex", pulp.LpMinimize)
        
        # Crear variables
        var_count = data['var_count']
        variables = []
        for i in range(var_count):
            var_name = f"x{i+1}"
            variables.append(pulp.LpVariable(var_name, lowBound=0))
        
        # Función objetivo
        obj_expr = 0
        for i, coef in enumerate(data['objective']['coefficients']):
            obj_expr += coef * variables[i]
        problem += obj_expr
        
        # Restricciones
        for i, constraint in enumerate(data['constraints']):
            constr_expr = 0
            for j, coef in enumerate(constraint['coefficients']):
                constr_expr += coef * variables[j]
            
            if constraint['type'] == '<=':
                problem += constr_expr <= constraint['rhs'], f"Restriccion_{i}"
            elif constraint['type'] == '>=':
                problem += constr_expr >= constraint['rhs'], f"Restriccion_{i}"
            else:
                problem += constr_expr == constraint['rhs'], f"Restriccion_{i}"
        
        # Resolver
        problem.solve()
        
        # Preparar resultados
        results = {
            'status': pulp.LpStatus[problem.status],
            'objective_value': pulp.value(problem.objective),
            'variables': {},
            'constraints': {}
        }
        
        # Valores de variables
        for var in variables:
            results['variables'][var.name] = var.varValue
        
        # Información de restricciones (holgura y precios sombra)
        for i, constraint in enumerate(problem.constraints.values()):
            constraint_name = f"Restriccion_{i+1}"
            results['constraints'][constraint_name] = {
                'slack': constraint.slack,
                'shadow_price': constraint.pi
            }
        
        return jsonify(results)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/solve_transport', methods=['POST'])
def solve_transport():
    try:
        data = request.json
        supply = data['supply']
        demand = data['demand']
        costs = data['costs']
        
        # Crear problema de transporte
        problem = pulp.LpProblem("Problema_Transporte", pulp.LpMinimize)
        
        # Crear variables
        routes = []
        for i in range(len(supply)):
            for j in range(len(demand)):
                routes.append((i, j))
        
        x = pulp.LpVariable.dicts("Ruta", routes, lowBound=0)
        
        # Función objetivo
        problem += pulp.lpSum([costs[i][j] * x[(i, j)] for i in range(len(supply)) for j in range(len(demand))])
        
        # Restricciones de oferta
        for i in range(len(supply)):
            problem += pulp.lpSum([x[(i, j)] for j in range(len(demand))]) <= supply[i], f"Oferta_{i}"
        
        # Restricciones de demanda
        for j in range(len(demand)):
            problem += pulp.lpSum([x[(i, j)] for i in range(len(supply))]) >= demand[j], f"Demanda_{j}"
        
        # Resolver
        problem.solve()
        
        # Preparar resultados
        results = {
            'status': pulp.LpStatus[problem.status],
            'total_cost': pulp.value(problem.objective),
            'allocations': [],
            'supply_usage': [],
            'demand_satisfaction': []
        }
        
        # Asignaciones
        for i, j in routes:
            quantity = x[(i, j)].varValue
            if quantity > 0:
                results['allocations'].append({
                    'from': f"Origen {i+1}",
                    'to': f"Destino {j+1}",
                    'quantity': quantity,
                    'cost': costs[i][j] * quantity
                })
        
        # Uso de oferta
        for i in range(len(supply)):
            used = sum(x[(i, j)].varValue for j in range(len(demand)))
            results['supply_usage'].append({
                'supplier': f"Origen {i+1}",
                'used': used,
                'available': supply[i],
                'percentage': (used / supply[i]) * 100 if supply[i] > 0 else 0
            })
        
        # Satisfacción de demanda
        for j in range(len(demand)):
            received = sum(x[(i, j)].varValue for i in range(len(supply)))
            results['demand_satisfaction'].append({
                'customer': f"Destino {j+1}",
                'received': received,
                'demanded': demand[j],
                'percentage': (received / demand[j]) * 100 if demand[j] > 0 else 0
            })
        
        return jsonify(results)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/solve_assignment', methods=['POST'])
def solve_assignment():
    try:
        data = request.json
        cost_matrix = data['cost_matrix']
        
        n = len(cost_matrix)
        
        # Crear problema de asignación
        problem = pulp.LpProblem("Problema_Asignacion", pulp.LpMinimize)
        
        # Variables binarias
        x = pulp.LpVariable.dicts("Asignar", 
                                 [(i, j) for i in range(n) for j in range(n)], 
                                 cat='Binary')
        
        # Función objetivo
        problem += pulp.lpSum([cost_matrix[i][j] * x[(i, j)] for i in range(n) for j in range(n)])
        
        # Restricciones: cada trabajador hace exactamente 1 tarea
        for i in range(n):
            problem += pulp.lpSum([x[(i, j)] for j in range(n)]) == 1, f"Trabajador_{i}"
        
        # Restricciones: cada tarea es hecha por exactamente 1 trabajador
        for j in range(n):
            problem += pulp.lpSum([x[(i, j)] for i in range(n)]) == 1, f"Tarea_{j}"
        
        # Resolver
        problem.solve()
        
        # Preparar resultados
        results = {
            'status': pulp.LpStatus[problem.status],
            'total_cost': pulp.value(problem.objective),
            'assignments': [],
            'efficiency_analysis': []
        }
        
        # Asignaciones
        for i in range(n):
            for j in range(n):
                if x[(i, j)].varValue == 1:
                    results['assignments'].append({
                        'worker': f"Trabajador {i+1}",
                        'task': f"Tarea {j+1}",
                        'cost': cost_matrix[i][j]
                    })
        
        # Análisis de eficiencia
        for i in range(n):
            worker_costs = [cost_matrix[i][j] for j in range(n)]
            assigned_cost = next(a['cost'] for a in results['assignments'] if a['worker'] == f"Trabajador {i+1}")
            min_cost = min(worker_costs)
            max_cost = max(worker_costs)
            efficiency = ((max_cost - assigned_cost) / (max_cost - min_cost)) * 100 if max_cost != min_cost else 100
            
            results['efficiency_analysis'].append({
                'worker': f"Trabajador {i+1}",
                'assigned_cost': assigned_cost,
                'min_possible': min_cost,
                'max_possible': max_cost,
                'efficiency': efficiency
            })
        
        return jsonify(results)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/solve_graphical', methods=['POST'])
def solve_graphical():
    try:
        data = request.get_json()
        objective = data['objective']
        constraints = data['constraints']
        
        import matplotlib.pyplot as plt
        import numpy as np
        from io import BytesIO
        import base64
        
        # Configurar el gráfico
        plt.figure(figsize=(10, 8))
        
        # Rango para x1
        x1 = np.linspace(0, 20, 400)
        
        # Graficar cada restricción
        colors = ['red', 'blue', 'green', 'orange', 'purple']
        feasible_region = None
        
        for i, constraint in enumerate(constraints):
            if len(constraint['coefficients']) >= 2:
                a, b = constraint['coefficients'][0], constraint['coefficients'][1]
                rhs = constraint['rhs']
                
                # Calcular x2 para la restricción
                if b != 0:
                    x2 = (rhs - a * x1) / b
                    
                    # Aplicar tipo de restricción
                    if constraint['type'] == '<=':
                        plt.fill_between(x1, x2, 0, alpha=0.1, color=colors[i % len(colors)])
                        label = f'{a}x₁ + {b}x₂ ≤ {rhs}'
                    else:  # '>='
                        plt.fill_between(x1, x2, 10, alpha=0.1, color=colors[i % len(colors)])
                        label = f'{a}x₁ + {b}x₂ ≥ {rhs}'
                    
                    plt.plot(x1, x2, label=label, color=colors[i % len(colors)], linewidth=2)
        
        # Resolver el problema para encontrar el punto óptimo
        if objective['type'] == 'maximize':
            problem = pulp.LpProblem("Problema_Grafico", pulp.LpMaximize)
        else:
            problem = pulp.LpProblem("Problema_Grafico", pulp.LpMinimize)
        
        x1_var = pulp.LpVariable("x1", lowBound=0)
        x2_var = pulp.LpVariable("x2", lowBound=0)
        
        # Función objetivo
        problem += objective['coefficients'][0] * x1_var + objective['coefficients'][1] * x2_var
        
        # Restricciones
        for i, constraint in enumerate(constraints):
            if len(constraint['coefficients']) >= 2:
                expr = constraint['coefficients'][0] * x1_var + constraint['coefficients'][1] * x2_var
                if constraint['type'] == '<=':
                    problem += expr <= constraint['rhs']
                else:
                    problem += expr >= constraint['rhs']
        
        # Resolver
        problem.solve()
        
        # Punto óptimo
        if pulp.LpStatus[problem.status] == 'Optimal':
            x1_opt = x1_var.varValue
            x2_opt = x2_var.varValue
            z_opt = pulp.value(problem.objective)
            
            # Marcar punto óptimo
            plt.plot(x1_opt, x2_opt, 'ro', markersize=10, label=f'Óptimo: ({x1_opt:.1f}, {x2_opt:.1f})')
            
            # Líneas de la función objetivo
            a_obj, b_obj = objective['coefficients']
            if b_obj != 0:
                x2_obj = (z_opt - a_obj * x1) / b_obj
                plt.plot(x1, x2_obj, 'k--', alpha=0.7, label=f'Z = {z_opt:.1f}')
        
        # Configuración del gráfico
        plt.xlim(0, 15)
        plt.ylim(0, 10)
        plt.xlabel('x₁', fontsize=12)
        plt.ylabel('x₂', fontsize=12)
        plt.title('Método Gráfico - Programación Lineal', fontsize=14)
        plt.grid(True, alpha=0.3)
        plt.legend()
        
        # Convertir a base64 para enviar al frontend
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        plt.close()
        
        # Resultados
        results = {
            'status': pulp.LpStatus[problem.status],
            'objective_value': pulp.value(problem.objective) if pulp.LpStatus[problem.status] == 'Optimal' else None,
            'variables': {
                'x1': x1_var.varValue if pulp.LpStatus[problem.status] == 'Optimal' else None,
                'x2': x2_var.varValue if pulp.LpStatus[problem.status] == 'Optimal' else None
            },
            'plot': f"data:image/png;base64,{image_base64}"
        }
        
        return jsonify(results)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    app.run(debug=True, port=5000)