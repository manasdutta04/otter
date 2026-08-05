FROM node:20-alpine
WORKDIR /workspace
COPY apps/web/package*.json ./
RUN npm install
COPY apps/web .
