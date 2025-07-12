#!/bin/bash

echo "🔄 Reiniciando servidores NooxID..."

# Matar procesos en puertos específicos
echo "🛑 Deteniendo procesos existentes..."
npx kill-port 5000 2>/dev/null || true
npx kill-port 5173 2>/dev/null || true

sleep 2

echo "🚀 Iniciando Backend (Flask)..."
cd "noox-id-back"
python main.py &
BACKEND_PID=$!

sleep 5

echo "🌐 Iniciando Frontend (React)..."
cd "../noox-id"
npm run dev &
FRONTEND_PID=$!

echo ""
echo "✅ Servidores iniciados:"
echo "   Backend:  http://localhost:5000 (PID: $BACKEND_PID)"
echo "   Frontend: http://localhost:5173 (PID: $FRONTEND_PID)"
echo ""
echo "Para detener ambos servidores, presiona Ctrl+C"

# Esperar a que terminen los procesos
wait
