import asyncio
import os
import sys
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# 1. Asegurar que Python encuentre los módulos internos
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from game_logic import PartidaPocha

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[int, WebSocket] = {}

    async def connect(self, player_id: int, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[player_id] = websocket

    def disconnect(self, player_id: int):
        if player_id in self.active_connections:
            del self.active_connections[player_id]

    async def send_personal_message(self, message: dict, player_id: int):
        if player_id in self.active_connections:
            try:
                await self.active_connections[player_id].send_json(message)
            except Exception:
                pass

    async def broadcast(self, partida: PartidaPocha):
        for player_id in range(4):
            estado = partida.obtener_estado_cliente(player_id)
            await self.send_personal_message(estado, player_id)

manager = ConnectionManager()

NOMBRES = ["Luis", "Guille (Bot)", "Pepe (Bot)", "Amador (Bot)"]
partida = PartidaPocha(NOMBRES, carta_inicio=1, manos_pico=4)

async def bucle_juego_bots():
    while True:
        await asyncio.sleep(1)
        
        if partida.estado == "REPARTIR":
            partida.repartir()
            await manager.broadcast(partida)
            await asyncio.sleep(1.5)

        elif partida.estado == "APUESTAS":
            turno = partida.turno_idx
            jugador_actual = partida.jugadores[turno]
            
            if not jugador_actual.humano:
                await asyncio.sleep(1.2)
                apuesta = partida.calcular_apuesta_bot(jugador_actual)
                exito = partida.procesar_apuesta(turno, apuesta)
                if exito:
                    await manager.broadcast(partida)

        elif partida.estado == "JUGANDO":
            if len(partida.mesa) == 4:
                await asyncio.sleep(2.0)
                partida.resolver_baza()
                await manager.broadcast(partida)
            else:
                turno = partida.turno_idx
                jugador_actual = partida.jugadores[turno]
                if not jugador_actual.humano:
                    await asyncio.sleep(1.2)
                    carta = partida.jugar_carta_bot(jugador_actual)
                    exito = partida.procesar_jugada(turno, carta.key)
                    if exito:
                        await manager.broadcast(partida)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(bucle_juego_bots())

# 2. Endpoint del WebSocket
@app.websocket("/ws/{player_id}")
async def websocket_endpoint(websocket: WebSocket, player_id: int):
    await manager.connect(player_id, websocket)
    await websocket.send_json(partida.obtener_estado_cliente(player_id))
    
    try:
        while True:
            data = await websocket.receive_json()
            
            if data.get("action") == "reiniciar_partida":
                nombres = data.get("nombres", [])
                carta_inicio = data.get("carta_inicio", 1)
                manos_pico = data.get("manos_pico", 4)
                partida.reiniciar(nombres, carta_inicio, manos_pico)
                await manager.broadcast(partida)

            elif data.get("action") == "configurar_nombres":
                nombres = data.get("nombres", [])
                if len(nombres) == 4:
                    partida.configurar_nombres(nombres)
                    await manager.broadcast(partida)

            elif data.get("action") == "apostar" and partida.estado == "APUESTAS" and partida.turno_idx == player_id:
                exito = partida.procesar_apuesta(player_id, data["cantidad"])
                if exito:
                    await manager.broadcast(partida)
                
            elif data.get("action") == "jugar" and partida.estado == "JUGANDO" and partida.turno_idx == player_id:
                exito = partida.procesar_jugada(player_id, data["carta"])
                if exito:
                    await manager.broadcast(partida)

    except WebSocketDisconnect:
        manager.disconnect(player_id)

# 3. Montar la carpeta Frontend en la raíz '/' para servir HTML, CSS, JS e imágenes
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
FRONTEND_DIR = os.path.join(ROOT_DIR, "Frontend")
if not os.path.exists(FRONTEND_DIR):
    FRONTEND_DIR = os.path.join(ROOT_DIR, "frontend")

if os.path.exists(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
