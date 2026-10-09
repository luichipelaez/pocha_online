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

class Sala:
    def __init__(self, sala_id: str, modo: str = "bots"):
        self.sala_id = sala_id
        self.modo = modo
        self.connections: dict[int, WebSocket] = {}
        nombres_defecto = ["Jugador 1", "Guille (Bot)", "Pepe (Bot)", "Amador (Bot)"]
        self.partida = PartidaPocha(nombres_defecto, carta_inicio=1, manos_pico=4)
        
        # Si es modo individual contra bots, inicia de inmediato.
        # En multijugador se queda en espera hasta pulsar 'Comenzar'.
        self.iniciada = (modo == "bots")
        if not self.iniciada:
            self.partida.estado = "ESPERANDO"
            self.partida.mensaje = "Esperando jugadores. Pulsa 'Comenzar Partida' para iniciar."

        self.lock = asyncio.Lock()
        self.task = asyncio.create_task(self.bucle_juego_bots())

    async def conectar(self, websocket: WebSocket, nombre: str) -> int:
        await websocket.accept()
        async with self.lock:
            asiento_libre = None
            if self.modo == "bots":
                asiento_libre = 0
            else:
                for i in range(4):
                    if i not in self.connections:
                        asiento_libre = i
                        break

            if asiento_libre is None:
                await websocket.close(code=4000, reason="Sala llena")
                return -1

            self.connections[asiento_libre] = websocket
            self.partida.jugadores[asiento_libre].humano = True
            if nombre:
                self.partida.jugadores[asiento_libre].nombre = nombre

            if self.modo == "multi" and not self.iniciada:
                self.partida.mensaje = f"{nombre} se ha unido. ({len(self.connections)}/4 conectados)."

        await self.broadcast()
        return asiento_libre

    def desconectar(self, asiento_id: int):
        if asiento_id in self.connections:
            del self.connections[asiento_id]
            if self.modo == "multi":
                self.partida.jugadores[asiento_id].humano = False

    async def broadcast(self):
        for p_id in range(4):
            estado = self.partida.obtener_estado_cliente(p_id)
            estado["tu_id"] = p_id
            estado["esperando_inicio"] = not self.iniciada
            estado["num_conectados"] = len(self.connections)
            if p_id in self.connections:
                try:
                    await self.connections[p_id].send_json(estado)
                except Exception:
                    pass

    async def bucle_juego_bots(self):
        try:
            while True:
                await asyncio.sleep(0.8)
                async with self.lock:
                    # Si la partida no ha sido iniciada en multijugador, espera
                    if not self.iniciada:
                        continue

                    if self.partida.estado in ["REPARTIR", "ESPERANDO"]:
                        self.partida.estado = "REPARTIR"
                        self.partida.repartir()
                        await self.broadcast()
                        await asyncio.sleep(1.2)

                    elif self.partida.estado == "APUESTAS":
                        turno = self.partida.turno_idx
                        jugador_actual = self.partida.jugadores[turno]
                        
                        if not jugador_actual.humano:
                            await asyncio.sleep(1.0)
                            apuesta = self.partida.calcular_apuesta_bot(jugador_actual)
                            exito = self.partida.procesar_apuesta(turno, apuesta)
                            if exito:
                                await self.broadcast()

                    elif self.partida.estado == "JUGANDO":
                        if len(self.partida.mesa) == 4:
                            await asyncio.sleep(1.8)
                            self.partida.resolver_baza()
                            await self.broadcast()
                        else:
                            turno = self.partida.turno_idx
                            jugador_actual = self.partida.jugadores[turno]
                            if not jugador_actual.humano:
                                await asyncio.sleep(1.0)
                                carta = self.partida.jugar_carta_bot(jugador_actual)
                                exito = self.partida.procesar_jugada(turno, carta.key)
                                if exito:
                                    await self.broadcast()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"Error en bucle de sala {self.sala_id}: {e}")

class RoomManager:
    def __init__(self):
        self.salas: dict[str, Sala] = {}

    def obtener_o_crear_sala(self, sala_id: str, modo: str) -> Sala:
        if sala_id not in self.salas:
            self.salas[sala_id] = Sala(sala_id, modo)
        return self.salas[sala_id]

room_manager = RoomManager()

# Endpoint HTTP para obtener la lista de salas activas y su ocupación
@app.get("/api/salas")
async def listar_salas():
    resultado = []
    for sala_id, sala in room_manager.salas.items():
        if sala.modo == "multi":
            resultado.append({
                "id": sala_id,
                "humanos": len(sala.connections),
                "iniciada": sala.iniciada
            })
    return resultado

# WebSocket Endpoint adaptado
@app.websocket("/ws/{sala_id}")
async def websocket_endpoint(websocket: WebSocket, sala_id: str):
    nombre = websocket.query_params.get("nombre", "Jugador")
    modo = websocket.query_params.get("modo", "bots")

    sala = room_manager.obtener_o_crear_sala(sala_id, modo)
    asiento_id = await sala.conectar(websocket, nombre)

    if asiento_id == -1:
        return

    try:
        while True:
            data = await websocket.receive_json()
            action = data.get("action")

            async with sala.lock:
                if action == "iniciar_partida":
                    sala.iniciada = True
                    # Reemplazar con Bots los huecos donde no haya entrado ningún jugador humano
                    for i in range(4):
                        if i not in sala.connections:
                            sala.partida.jugadores[i].humano = False
                            if "Bot" not in sala.partida.jugadores[i].nombre:
                                sala.partida.jugadores[i].nombre = f"Bot {i+1}"
                    await sala.broadcast()

                elif action == "reiniciar_partida":
                    nombres = data.get("nombres", [])
                    carta_inicio = data.get("carta_inicio", 1)
                    manos_pico = data.get("manos_pico", 4)
                    sala.partida.reiniciar(nombres, carta_inicio, manos_pico)
                    sala.iniciada = True
                    for i in range(4):
                        sala.partida.jugadores[i].humano = (i in sala.connections)
                    await sala.broadcast()

                elif action == "apostar" and sala.partida.estado == "APUESTAS" and sala.partida.turno_idx == asiento_id:
                    exito = sala.partida.procesar_apuesta(asiento_id, data["cantidad"])
                    if exito:
                        await sala.broadcast()

                elif action == "jugar" and sala.partida.estado == "JUGANDO" and sala.partida.turno_idx == asiento_id:
                    exito = sala.partida.procesar_jugada(asiento_id, data["carta"])
                    if exito:
                        await sala.broadcast()

    except WebSocketDisconnect:
        sala.desconectar(asiento_id)
        async with sala.lock:
            await sala.broadcast()

# Montar carpeta Frontend
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
FRONTEND_DIR = os.path.join(ROOT_DIR, "Frontend")
if not os.path.exists(FRONTEND_DIR):
    FRONTEND_DIR = os.path.join(ROOT_DIR, "frontend")

if os.path.exists(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
