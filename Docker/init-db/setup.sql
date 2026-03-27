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

-- Inserindo Departamentos
INSERT INTO departamentos (nome) VALUES ('Vendas'), ('TI'), ('Recursos Humanos'), ('Diretoria');

-- Inserindo Funcionários
INSERT INTO funcionarios (nome, cargo, departamento_id) VALUES 
('Carlos Silva', 'Vendedor', 1),
('Ana Souza', 'Gerente de Vendas', 1),
('Marcos TI', 'Desenvolvedor', 2),
('Julia RH', 'Analista de RH', 3),
('Roberto Diretor', 'CEO', 4);

-- Inserindo Fornecedores Normais
INSERT INTO fornecedores (cnpj, nome_fantasia, data_cadastro, score_confiabilidade) VALUES 
('11.111.111/0001-11', 'Kalunga Materiais', '2020-01-15', 98),
('22.222.222/0001-22', 'Dell Computadores', '2019-05-20', 99);

-- Inserindo um Fornecedor "Suspeito" (Criado hoje, score baixo)
INSERT INTO fornecedores (cnpj, nome_fantasia, data_cadastro, score_confiabilidade) VALUES 
('99.999.999/0001-99', 'Consultoria Fantasma LTDA', CURRENT_DATE, 40);

-- Inserindo Clientes
INSERT INTO clientes (cpf, nome) VALUES 
('123.456.789-00', 'João Cliente Normal'),
('987.654.321-11', 'Maria Cliente VIP');

-- Inserindo Vendas (Comportamento Normal)
INSERT INTO vendas (cliente_id, vendedor_id, valor_total, metodo_pagamento) VALUES 
(1, 1, 150.00, 'CARTAO_CREDITO'),
(2, 1, 4500.00, 'PIX');

-- Inserindo Despesas (Comportamento Normal para treinar a IA)
INSERT INTO despesas (funcionario_id, fornecedor_id, valor, categoria, descricao) VALUES 
(3, 2, 8500.00, 'Equipamentos', 'Compra de Notebook para dev novo'),
(4, 1, 350.00, 'Material de Escritório', 'Papel e canetas para o mês');

-- ==========================================
-- FIM DO SCRIPT
-- ==========================================