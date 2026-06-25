# Plan Update: Worker Reload Limitation

Este arquivo descreve a alteração necessária no plano original para documentar o comportamento atual do worker em relação à ativação de versões.

## O que precisa ser alterado

1. No passo 10 de verificação e testes:
   - adicionar que o worker atualmente carrega a versão ativa apenas na inicialização ou quando detecta mudanças nos arquivos de modelo.
   - deixar claro que uma mudança de ativação no DB não produz atualização imediata no worker em execução.

2. Em `Further Considerations`:
   - adicionar uma observação sobre a limitação atual:
     - "O worker só carrega o modelo ativo na inicialização ou quando detecta mudanças nos arquivos de modelo; a ativação no DB não provoca atualização imediata."
   - sugerir como melhoria futura:
     - "Implementar polling ou refresh ativo para detectar alterações de ativação em tempo real e aplicar a nova versão sem reiniciar o worker."

## Texto sugerido para o plano

### Passo 10
`10. Verificação e testes: garantir que os endpoints retornam a lista correta, que a ativação altera model_versions e pipelines_config, que o worker carrega a versão ativa (atualmente somente na inicialização ou quando os arquivos de modelo mudam, não imediatamente quando a ativação muda no DB) e que o frontend reflete o estado.`

### Further Considerations
`- Limitação atual: o worker só carrega o modelo ativo na inicialização ou quando detecta mudanças nos arquivos de modelo; a ativação no DB não provoca atualização imediata. Implementar polling ou refresh ativo para detectar alterações de ativação em tempo real.`
