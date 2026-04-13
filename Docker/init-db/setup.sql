-- ==========================================
-- 1. CRIAÇÃO DAS TABELAS (SCHEMA DA LOJA)
-- ==========================================

-- Tabela de Departamentos da empresa
CREATE TABLE departamentos (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(50) NOT NULL
);

-- Tabela de Funcionários (Alvo para análise de fraudes internas)
CREATE TABLE funcionarios (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    cargo VARCHAR(50) NOT NULL,
    departamento_id INT REFERENCES departamentos(id),
    data_contratacao DATE DEFAULT CURRENT_DATE
);

-- Tabela de Fornecedores (Para cruzar com despesas suspeitas)
CREATE TABLE fornecedores (
    id SERIAL PRIMARY KEY,
    cnpj VARCHAR(20) UNIQUE NOT NULL,
    nome_fantasia VARCHAR(100) NOT NULL,
    data_cadastro DATE DEFAULT CURRENT_DATE,
    score_confiabilidade INT DEFAULT 100 -- De 0 a 100
);

-- Tabela de Despesas Corporativas (O Foco Principal do nosso Debezium/IA)
CREATE TABLE despesas (
    id SERIAL PRIMARY KEY,
    funcionario_id INT REFERENCES funcionarios(id),
    fornecedor_id INT REFERENCES fornecedores(id),
    valor DECIMAL(12,2) NOT NULL,
    categoria VARCHAR(50) NOT NULL,
    descricao TEXT,
    data_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status_aprovacao VARCHAR(20) DEFAULT 'PENDENTE'
);

-- Tabela de Clientes
CREATE TABLE clientes (
    id SERIAL PRIMARY KEY,
    cpf VARCHAR(14) UNIQUE NOT NULL,
    nome VARCHAR(100) NOT NULL,
    data_cadastro DATE DEFAULT CURRENT_DATE
);

-- Tabela de Vendas (Para testar fraudes de clientes)
CREATE TABLE vendas (
    id SERIAL PRIMARY KEY,
    cliente_id INT REFERENCES clientes(id),
    vendedor_id INT REFERENCES funcionarios(id),
    valor_total DECIMAL(12,2) NOT NULL,
    metodo_pagamento VARCHAR(50),
    data_venda TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ==========================================
-- 2. CONFIGURAÇÃO PARA O DEBEZIUM (CDC)
-- ==========================================
-- O REPLICA IDENTITY FULL garante que o Debezium capture o "antes" e o "depois" 
-- de cada UPDATE ou DELETE, e não apenas do INSERT.

ALTER TABLE despesas REPLICA IDENTITY FULL;
ALTER TABLE vendas REPLICA IDENTITY FULL;
ALTER TABLE fornecedores REPLICA IDENTITY FULL;

-- ==========================================
-- 3. PERMISSÕES DE SEGURANÇA (USUÁRIO DEBEZIUM)
-- ==========================================

-- Cria o usuário exclusivo para o Debezium ler os logs de replicação
CREATE USER debezium_user WITH PASSWORD 'dbz_123' REPLICATION LOGIN;

-- Dá permissão de uso no schema public
GRANT USAGE ON SCHEMA public TO debezium_user;

-- O Debezium precisa de permissão de SELECT em todas as tabelas para fazer 
-- o "snapshot" inicial (tirar uma foto do banco antes de começar a ler os logs)
GRANT SELECT ON ALL TABLES IN SCHEMA public TO debezium_user;

-- ==========================================
-- 4. INSERÇÃO DE DADOS INICIAIS (SEED)
-- ==========================================
-- =========================================================================
-- 1. LIMPANDO O BANCO (Para poder rodar o script várias vezes se precisar)
-- =========================================================================
TRUNCATE TABLE despesas, vendas, clientes, fornecedores, funcionarios, departamentos RESTART IDENTITY CASCADE;

-- =========================================================================
-- 2. DADOS CADASTRAIS BASE
-- =========================================================================

-- Departamentos
INSERT INTO departamentos (nome) VALUES 
('Vendas'), ('TI'), ('Recursos Humanos'), ('Diretoria'), ('Marketing'), ('Financeiro');

-- Funcionários (Vendedores, Devs, RH, etc)
INSERT INTO funcionarios (nome, cargo, departamento_id) VALUES 
('Carlos Silva', 'Vendedor Sênior', 1),
('Ana Souza', 'Gerente de Vendas', 1),
('Bruno Costa', 'Vendedor Junior', 1),
('Marcos TI', 'Engenheiro de Software', 2),
('Felipe DevOps', 'Analista de Infra', 2),
('Julia RH', 'Analista de RH', 3),
('Camila Admin', 'Coordenadora Administrativa', 3),
('Roberto Diretor', 'CEO', 4),
('Laura Marketing', 'Designer', 5),
('Fernanda Financeiro', 'Analista Contábil', 6);

-- Fornecedores (Com perfis de pontuação e tempo de mercado variados)
INSERT INTO fornecedores (cnpj, nome_fantasia, data_cadastro, score_confiabilidade) VALUES 
('11.111.111/0001-11', 'Kalunga Materiais', '2018-01-15', 98),     -- Fornecedor 1 (Escritório)
('22.222.222/0001-22', 'Dell Computadores', '2019-05-20', 99),     -- Fornecedor 2 (TI)
('33.333.333/0001-33', 'Amazon Web Services', '2020-10-10', 99),   -- Fornecedor 3 (Nuvem/TI)
('44.444.444/0001-44', 'Gol Linhas Aéreas', '2015-03-12', 95),     -- Fornecedor 4 (Viagens)
('55.555.555/0001-55', 'Localiza Aluguel', '2016-08-30', 94),      -- Fornecedor 5 (Viagens)
('66.666.666/0001-66', 'Agência de Publicidade X', '2022-01-10', 85); -- Fornecedor 6 (Marketing)

-- Clientes (Massa de clientes normais para vendas)
INSERT INTO clientes (cpf, nome) VALUES 
('111.111.111-11', 'João Cliente Normal'), ('222.222.222-22', 'Maria Cliente VIP'),
('333.333.333-33', 'Empresa X LTDA'), ('444.444.444-44', 'Roberto Silva'),
('555.555.555-55', 'Padaria do Zé'), ('666.666.666-66', 'Clinica Médica Saúde'),
('777.777.777-77', 'Ana Pereira'), ('888.888.888-88', 'Lucas Fernandes'),
('999.999.999-99', 'Juliana Castro'), ('000.000.000-00', 'Carlos Edu');

-- =========================================================================
-- 3. TREINAMENTO: COMPORTAMENTO NORMAL DE VENDAS
-- =========================================================================
INSERT INTO vendas (cliente_id, vendedor_id, valor_total, metodo_pagamento) VALUES 
-- Vendas no Cartão de Crédito (Valores menores, varejo)
(1, 1, 150.00, 'CARTAO_CREDITO'), (2, 2, 340.50, 'CARTAO_CREDITO'),
(4, 3, 89.90, 'CARTAO_CREDITO'), (7, 1, 450.00, 'CARTAO_CREDITO'),
(8, 2, 199.99, 'CARTAO_CREDITO'), (9, 3, 299.00, 'CARTAO_CREDITO'),
(10, 1, 55.00, 'CARTAO_CREDITO'), (1, 2, 850.00, 'CARTAO_CREDITO'),
(2, 3, 120.00, 'CARTAO_CREDITO'), (4, 1, 400.00, 'CARTAO_CREDITO'),

-- Vendas no PIX (Valores médios)
(5, 1, 850.00, 'PIX'), (6, 2, 1200.00, 'PIX'),
(7, 3, 900.00, 'PIX'), (8, 1, 450.00, 'PIX'),
(9, 2, 1500.00, 'PIX'), (10, 3, 750.00, 'PIX'),
(1, 1, 2200.00, 'PIX'), (2, 2, 600.00, 'PIX'),

-- Vendas no Boleto (B2B, Empresas, Valores muito altos)
(3, 2, 15000.00, 'BOLETO'), (5, 1, 8500.00, 'BOLETO'),
(6, 2, 12400.00, 'BOLETO'), (3, 3, 22000.00, 'BOLETO'),
(5, 1, 9300.00, 'BOLETO'), (6, 2, 18500.00, 'BOLETO');

-- =========================================================================
-- 4. TREINAMENTO: COMPORTAMENTO NORMAL DE DESPESAS (O FOCO DA IA)
-- =========================================================================
INSERT INTO despesas (funcionario_id, fornecedor_id, valor, categoria, descricao) VALUES 
-- Padrão 1: RH/Admin comprando material de escritório (Valores Baixos)
(6, 1, 150.00, 'Material de Escritório', 'Canetas e Post-it'),
(7, 1, 220.00, 'Material de Escritório', 'Papel sulfite A4'),
(6, 1, 310.00, 'Material de Escritório', 'Grampeadores e furadores'),
(7, 1, 180.00, 'Material de Escritório', 'Pastas organizadoras'),
(6, 1, 400.00, 'Material de Escritório', 'Cadeiras pequenas e lixeiras'),
(7, 1, 120.00, 'Material de Escritório', 'Clipes e borrachas'),
(6, 1, 250.00, 'Material de Escritório', 'Cadernos corporativos'),
(7, 1, 580.00, 'Material de Escritório', 'Quadro branco para sala'),
(6, 1, 85.00, 'Material de Escritório', 'Pilhas e fita durex'),
(7, 1, 490.00, 'Material de Escritório', 'Tonner para impressora'),

-- Padrão 2: TI comprando Equipamentos/Servidores (Valores Altos)
(4, 2, 7500.00, 'Equipamentos TI', 'Notebook Dell i5 para dev novo'),
(5, 2, 8200.00, 'Equipamentos TI', 'Notebook Dell i7 para engenharia'),
(4, 2, 6000.00, 'Equipamentos TI', 'Lote de Monitores Ultrawide'),
(5, 3, 4500.00, 'Serviços em Nuvem', 'Fatura Mensal AWS Servidores'),
(4, 2, 7800.00, 'Equipamentos TI', 'Notebook Dell i7 substituição'),
(5, 3, 4800.00, 'Serviços em Nuvem', 'Fatura Mensal AWS Banco de Dados'),
(4, 2, 3500.00, 'Equipamentos TI', 'Nobreak para CPD'),
(5, 3, 5100.00, 'Serviços em Nuvem', 'Hospedagem de e-commerce'),

-- Padrão 3: Vendas/Diretoria com Viagens Corporativas (Valores Médios)
(1, 4, 1200.00, 'Viagens', 'Passagem ida e volta SP-RJ'),
(2, 4, 2500.00, 'Viagens', 'Passagem ida e volta SP-Manaus'),
(8, 4, 3500.00, 'Viagens', 'Passagem Executiva CEO'),
(1, 5, 450.00, 'Viagens', 'Aluguel de carro 2 dias RJ'),
(2, 5, 800.00, 'Viagens', 'Aluguel de SUV 3 dias'),
(8, 5, 1200.00, 'Viagens', 'Aluguel Carro Premium CEO'),

-- Padrão 4: Marketing pagando agência
(9, 6, 8500.00, 'Marketing', 'Campanha Google Ads Janeiro'),
(9, 6, 9200.00, 'Marketing', 'Gestão de Redes Sociais Fevereiro'),
(9, 6, 7800.00, 'Marketing', 'Campanha Meta Ads Março');

-- ==========================================
-- FIM DO SCRIPT
-- ==========================================