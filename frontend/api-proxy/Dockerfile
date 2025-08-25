FROM node:18

# Install Python and pip
RUN apt-get update && apt-get install -y python3 python3-pip python3-venv

WORKDIR /app

# Copy and install Node.js dependencies
COPY package*.json ./
RUN npm install

# Copy React app source
COPY . .

# Build React app
RUN npm run build

# Install serve globally
RUN npm install -g serve

# Create Python virtual environment and install FastAPI dependencies
RUN python3 -m venv /app/venv
ENV PATH="/app/venv/bin:$PATH"

# Copy Python requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy FastAPI proxy server
COPY proxy_server.py .

EXPOSE 7860

# Copy the startup script
COPY start.sh .
RUN chmod +x start.sh

CMD ["./start.sh"]