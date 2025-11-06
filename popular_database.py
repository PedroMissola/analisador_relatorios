import sqlite3
import random
import pathlib
from faker import Faker
from datetime import datetime, timedelta

# --- Configurações ---
NUM_FUNCIONARIOS = 5000  # Ajustado para o número da sua solicitação
DB_FILE_PATH = pathlib.Path(__file__).parent / "data" / "empresa.db"

# Inicializa o Faker para dados em Português-BR
fake = Faker('pt_BR')

# Estrutura complexa de Divisões, Departamentos, Cargos, Salários Base e Gastos Típicos
ESTRUTURA_EMPRESA = {
    'Tecnologia e Produto': {
        'base_salario': 4500,
        'departamentos': {
            'Engenharia de Software': ['Engenheiro de Software Jr', 'Engenheiro de Software Pl',
                                       'Engenheiro de Software Sr', 'Arquiteto de Soluções'],
            'Infraestrutura (SRE)': ['Analista de Infraestrutura', 'Engenheiro SRE', 'Administrador de Redes'],
            'Segurança da Informação': ['Analista de Segurança', 'Especialista em Cibersegurança'],
            'Gestão de Produto': ['Product Manager', 'UX/UI Designer', 'Product Owner', 'Analista de QA']
        },
        'gastos': ['Licença Software', 'Curso/Treinamento', 'Equipamento (Hardware)', 'Café', 'Servidor Cloud']
    },
    'Comercial (Vendas e Mkt)': {
        'base_salario': 4000,
        'departamentos': {
            'Vendas (Executivo)': ['Executivo de Contas', 'Gerente de Vendas', 'Sales Development Rep (SDR)',
                                   'Analista de Pós-Venda'],
            'Marketing (Performance)': ['Analista de Marketing Digital', 'Especialista SEO/SEM', 'Analista de BI'],
            'Marketing (Marca)': ['Designer Gráfico', 'Assessor de Imprensa', 'Social Media', 'Produtor de Conteúdo']
        },
        'gastos': ['Almoço Cliente', 'Transporte App', 'Viagem (Hotel)', 'Conferência', 'Anúncios Online']
    },
    'Operações e Logística': {
        'base_salario': 2800,
        'departamentos': {
            'Cadeia de Suprimentos': ['Analista de Logística', 'Comprador', 'Gerente de Supply Chain'],
            'Produção (Fábrica)': ['Operador de Máquina', 'Supervisor de Produção', 'Técnico de Manutenção'],
            'Atendimento ao Cliente': ['Agente de Atendimento', 'Supervisor de Call Center', 'Analista de Suporte N1']
        },
        'gastos': ['Uniforme', 'Cantina', 'Material de Escritório', 'Transporte Fretado', 'Manutenção Equipamento']
    },
    'Administrativo e Financeiro': {
        'base_salario': 3800,
        'departamentos': {
            'Financeiro (Controladoria)': ['Analista Financeiro', 'Contador', 'Auditor Interno', 'Tesoureiro'],
            'Jurídico': ['Advogado Corporativo', 'Assistente Jurídico', 'Especialista em Compliance'],
            'Facilities (Adm)': ['Assistente Administrativo', 'Recepcionista', 'Técnico de Manutenção Predial',
                                 'Auxiliar de Limpeza']
        },
        'gastos': ['Papelaria', 'Serviço de Motoboy', 'Café', 'Material de Limpeza', 'Consultoria Externa']
    },
    'Recursos Humanos': {
        'base_salario': 3500,
        'departamentos': {
            'Aquisição de Talentos': ['Recrutador (Tech Recruiter)', 'Assistente de RH', 'Talent Sourcer'],
            'Business Partner': ['HR Business Partner', 'Analista de DHO', 'Especialista em L&D'],
            'Departamento Pessoal': ['Analista de Folha de Pagamento', 'Especialista em Benefícios']
        },
        'gastos': ['Brindes (Onboarding)', 'Plataforma de Vagas', 'Café', 'Evento Interno', 'Exame Admissional']
    }
}


def criar_banco():
    """
    Cria a estrutura de pastas e o banco de dados com as tabelas.
    """
    print(f"Iniciando criação do banco de dados em '{DB_FILE_PATH}'...")

    # 1. Garante que o diretório "data/" exista
    DB_FILE_PATH.parent.mkdir(exist_ok=True)

    # 2. Limpa o banco (se já existir) para começar do zero
    if DB_FILE_PATH.exists():
        DB_FILE_PATH.unlink()

    con = sqlite3.connect(str(DB_FILE_PATH))
    cur = con.cursor()

    # 3. Criar tabelas
    # Tabela de funcionários mais detalhada
    cur.execute("""
                CREATE TABLE funcionarios
                (
                    id                  INTEGER PRIMARY KEY,
                    nome                TEXT NOT NULL,
                    email               TEXT NOT NULL UNIQUE,
                    divisao             TEXT NOT NULL,
                    departamento        TEXT NOT NULL,
                    cargo               TEXT NOT NULL,
                    salario_base_mensal REAL NOT NULL,
                    data_contratacao    TEXT NOT NULL,
                    status              TEXT NOT NULL CHECK (status IN ('Ativo', 'Inativo')),
                    id_gerente          INTEGER,
                    FOREIGN KEY (id_gerente) REFERENCES funcionarios (id)
                )""")

    cur.execute("""
                CREATE TABLE pagamentos
                (
                    id             INTEGER PRIMARY KEY,
                    id_funcionario INTEGER NOT NULL,
                    mes_referencia TEXT    NOT NULL,
                    valor_pago     REAL    NOT NULL,
                    data_pagamento TEXT    NOT NULL,
                    status         TEXT    NOT NULL CHECK (status IN ('Pago', 'Pendente')),
                    FOREIGN KEY (id_funcionario) REFERENCES funcionarios (id)
                )""")

    # Tabela de gastos mais detalhada
    cur.execute("""
                CREATE TABLE gastos_internos
                (
                    id               INTEGER PRIMARY KEY,
                    id_funcionario   INTEGER NOT NULL,
                    descricao        TEXT    NOT NULL,
                    valor            REAL    NOT NULL,
                    data_gasto       TEXT    NOT NULL,
                    status_aprovacao TEXT    NOT NULL CHECK (status_aprovacao IN ('Aprovado', 'Pendente', 'Rejeitado')),
                    FOREIGN KEY (id_funcionario) REFERENCES funcionarios (id)
                )""")

    con.commit()
    con.close()
    print("Tabelas 'funcionarios', 'pagamentos', e 'gastos_internos' criadas com sucesso.")


def popular_banco():
    """
    Popula as tabelas com dados realistas usando Faker e a estrutura hierárquica.
    """
    con = sqlite3.connect(str(DB_FILE_PATH))
    cur = con.cursor()

    print(f"Populando {NUM_FUNCIONARIOS} funcionários...")

    funcionarios_data = []
    # Usamos dicionários para guardar dados que precisaremos depois
    funcionarios_lookup = {}
    gerentes_por_depto = {}  # Guarda IDs de gerentes por depto {depto_nome: [id1, id2]}

    today = datetime.now().date()

    for i in range(1, NUM_FUNCIONARIOS + 1):

        # 1. Escolher Divisão, Departamento e Cargo
        divisao = random.choice(list(ESTRUTURA_EMPRESA.keys()))
        config_divisao = ESTRUTURA_EMPRESA[divisao]

        departamento = random.choice(list(config_divisao['departamentos'].keys()))
        cargo = random.choice(config_divisao['departamentos'][departamento])

        # 2. Definir Salário
        # Salário = Base da Divisão * Multiplicador (simulando senioridade do cargo)
        salario_base = config_divisao['base_salario']
        multiplicador = random.uniform(1.0, 3.5)
        salario = round(salario_base * multiplicador, 2)

        # 3. Dados Pessoais
        nome = fake.name()
        email = f"{nome.lower().replace(' ', '.').replace('..', '.')}{i}@grandeempresa.com"
        data_contratacao = fake.date_between(start_date='-15y', end_date='-1mo')

        # Simular ~10% de funcionários inativos (desligados)
        status = 'Ativo' if random.random() > 0.1 else 'Inativo'

        # 4. Atribuir Gerente
        id_gerente = None
        if departamento in gerentes_por_depto and gerentes_por_depto[departamento]:
            # Atribui um gerente aleatório do mesmo departamento
            id_gerente = random.choice(gerentes_por_depto[departamento])

        # 5. Adicionar aos dados
        funcionarios_data.append((
            i, nome, email, divisao, departamento, cargo,
            salario, data_contratacao.isoformat(), status, id_gerente
        ))

        # 6. Guardar dados para lookup
        funcionarios_lookup[i] = {
            "salario": salario,
            "data_contratacao": data_contratacao,
            "divisao": divisao,
            "departamento": departamento,
            "status": status
        }

        # 7. Adicionar este funcionário como um potencial gerente se for sênior
        # (ex: contratado há mais de 3 anos)
        if (today - data_contratacao).days > (365 * 3):
            if departamento not in gerentes_por_depto:
                gerentes_por_depto[departamento] = []
            gerentes_por_depto[departamento].append(i)

    cur.executemany(
        """INSERT INTO funcionarios
           (id, nome, email, divisao, departamento, cargo, salario_base_mensal, data_contratacao, status, id_gerente)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        funcionarios_data
    )

    print("Funcionários populados. Gerando histórico de pagamentos e gastos...")

    pagamentos_data = []
    gastos_data = []

    for func_id, info in funcionarios_lookup.items():
        # Só gerar dados para funcionários 'Ativos'
        if info['status'] == 'Inativo':
            continue

        data_contratacao = info["data_contratacao"]
        salario = info["salario"]
        divisao = info["divisao"]

        # --- Gerar Pagamentos ---
        data_iter = data_contratacao
        while data_iter < today:
            data_iter = (data_iter.replace(day=1) + timedelta(days=32)).replace(day=1)
            if data_iter > today: break

            mes_referencia = data_iter.strftime("%Y-%m")

            # LÓGICA CONDICIONAL (IF): Vendas tem bônus/comissão maior
            if divisao == 'Comercial (Vendas e Mkt)':
                # Variação alta (0.9 a 2.5x do salário)
                multiplicador_pag = random.uniform(0.9, 2.5)
            else:
                # Variação normal (0.85 a 1.2x - bônus/desconto simples)
                multiplicador_pag = random.uniform(0.85, 1.2)

            valor_pago = round(salario * multiplicador_pag, 2)
            data_pagamento = data_iter + timedelta(days=random.randint(4, 6))  # 5º dia útil

            status_pag = 'Pago'
            if (today - data_iter).days < 35 and random.choice([True, False]):
                status_pag = 'Pendente'

            pagamentos_data.append((func_id, mes_referencia, valor_pago, data_pagamento.isoformat(), status_pag))

        # --- Gerar Gastos Internos ---
        # LÓGICA CONDICIONAL: Gastos específicos por divisão
        gastos_possiveis = ESTRUTURA_EMPRESA[divisao]['gastos']

        num_gastos = random.randint(5, 60)  # Pessoas de Vendas/Operações gastam mais
        for _ in range(num_gastos):
            descricao = random.choice(gastos_possiveis)

            # Valores de gastos também variam
            if descricao in ['Viagem (Hotel)', 'Licença Software', 'Conferência']:
                valor = round(random.uniform(150.00, 2500.00), 2)
            else:
                valor = round(random.uniform(15.00, 120.00), 2)

            data_gasto = fake.date_between(start_date=data_contratacao, end_date='today')

            # Simular status de aprovação
            status_aprov = random.choices(['Aprovado', 'Pendente', 'Rejeitado'], weights=[80, 15, 5], k=1)[0]

            gastos_data.append((func_id, descricao, valor, data_gasto.isoformat(), status_aprov))

    print(f"Inserindo {len(pagamentos_data)} registros de pagamento...")
    cur.executemany(
        "INSERT INTO pagamentos (id_funcionario, mes_referencia, valor_pago, data_pagamento, status) VALUES (?, ?, ?, ?, ?)",
        pagamentos_data
    )

    print(f"Inserindo {len(gastos_data)} registros de gastos internos...")
    cur.executemany(
        "INSERT INTO gastos_internos (id_funcionario, descricao, valor, data_gasto, status_aprovacao) VALUES (?, ?, ?, ?, ?)",
        gastos_data
    )

    con.commit()
    con.close()
    print("Banco de dados populado com sucesso!")


if __name__ == "__main__":
    criar_banco()
    popular_banco()