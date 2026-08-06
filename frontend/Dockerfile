# ==========================================================================
# NeuroOmics-AD frontend
#   target `dev`  -> Vite dev server (hot reload)
#   target `prod` -> static build served by nginx
# ==========================================================================

FROM node:20-alpine AS base
WORKDIR /app
COPY package.json package-lock.json* ./

FROM base AS deps
RUN npm install

FROM deps AS dev
COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

FROM deps AS build
COPY . .
ARG VITE_API_BASE=/api/v1
ENV VITE_API_BASE=${VITE_API_BASE}
RUN npm run build

FROM nginx:1.27-alpine AS prod
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
