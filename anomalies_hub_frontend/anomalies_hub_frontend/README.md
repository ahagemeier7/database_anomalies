# FraudOps Hub — frontend

Interface React, TypeScript e Vite para revisar alertas, consultar estatísticas, retreinar modelos e gerenciar versões.

## Executar com a arquitetura completa

Na raiz do repositório:

```bash
docker compose --profile seed up --build -d
```

Abra http://localhost:3000. O Nginx encaminha `/api` ao backend dentro da rede Docker. Os dados da demonstração e suas limitações estão no [README principal](../../readme.md).

## Desenvolvimento local

Use Node.js 22.12+ e mantenha o backend do Compose em execução. Nesta pasta:

```bash
npm ci
npm run dev
```

O Vite encaminha `/api` para `http://localhost:8000`. O valor padrão de `VITE_API_BASE_URL` é `/api`; o `.env.example` documenta essa configuração. Uma URL absoluta pode ser configurada em um `.env` local, desde que a API permita a origem no CORS.

## Verificar

```bash
npm run lint
npm run build
```

A tela de versões informa quando o Random Forest está indisponível e impede sua seleção. As estatísticas do Hub são calculadas sobre revisões humanas; o benchmark offline fica documentado na raiz do projeto.
