# Dev image: runs the Vite dev server (fast HMR, simplest for the test).
# A prod variant (vite build -> nginx) is noted in the README as an alternative.
FROM node:20-alpine

WORKDIR /app

# Install deps first for layer caching.
COPY package*.json ./
RUN npm install

# App source.
COPY . .

EXPOSE 5173

# --host 0.0.0.0 so the server is reachable from outside the container.
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
