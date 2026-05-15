# ==========================================
# ETAPA 1: Construção (Build)
# ==========================================
FROM node:20-alpine as builder

WORKDIR /app

# Copia os arquivos de dependência primeiro (otimiza o cache do Docker)
COPY package.json package-lock.json* ./
RUN npm install

# Copia o resto do código e faz o build (transforma TS/React em HTML/JS)
COPY . .
RUN npm run build

# ==========================================
# ETAPA 2: Servidor Web (Produção)
# ==========================================
FROM nginx:alpine

# Remove a página padrão do Nginx
RUN rm -rf /usr/share/nginx/html/*

# Copia os arquivos gerados na Etapa 1 para a pasta do Nginx
COPY --from=builder /app/dist /usr/share/nginx/html

# Copia a configuração que redireciona as rotas do React
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]