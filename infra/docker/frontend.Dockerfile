# infra/docker/frontend.Dockerfile
FROM node:20-alpine

WORKDIR /workspace/apps/web

COPY apps/web/package.json apps/web/package-lock.json* ./
RUN npm ci

COPY apps/web ./

ARG NEXT_PUBLIC_API_BASE_URL
ENV NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL

RUN npm run build

EXPOSE 3100

CMD ["npm", "run", "start"]
