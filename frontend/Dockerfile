# Build stage
FROM node:20-alpine AS build

WORKDIR /app

COPY package.json package-lock.json ./
# Install dependencies with legacy-peer-deps
RUN npm install --legacy-peer-deps

COPY . ./

# Build production bundle
RUN npm run build

# Production serve stage with Nginx
FROM nginx:alpine

COPY --from=build /app/build /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
