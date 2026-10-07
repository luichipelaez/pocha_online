import random

PALOS = ['oros', 'copas', 'espadas', 'bastos']
PALOS_ORDEN = {'oros': 0, 'copas': 1, 'espadas': 2, 'bastos': 3}
VALORES_NUM = {'1': 10, '3': 9, '12': 8, '11': 7, '10': 6, '7': 5, '6': 4, '5': 3, '4': 2, '2': 1}

FRASES_GANAR = [
    "En dos palabras, IN PRESIONANTE", "¿Dónde vas Peláez?", "Arrodillaos ante el rey", 
    "Así gana el Madrid", "Efectiviwonder", "Tal y como lo había planeado", "¡Para la saca!", 
    "¡Esa era mía!", "¡Soy el mejor!", "Ahora vas y lo cascas"
]

FRASES_QUEJA = [
    "¡Que mal he jugado!", "¿Pero cómo coño pedís?", "Soy el pupas", 
    "Esta no la vi llegar", "¡Esta me la pagáis!", "¡Nooo, esa no!", 
    "¡Me habéis pillado!", "¿En serio me la como con papas?"
]

def generar_secuencia(carta_inicio=1, max_cartas=10, manos_pico=4):
    carta_inicio = max(1, min(10, int(carta_inicio)))
    manos_pico = max(1, min(10, int(manos_pico)))
    subida = list(range(carta_inicio, max_cartas))
    pico = [max_cartas] * manos_pico
    bajada = list(range(max_cartas - 1, carta_inicio - 1, -1))
    return subida + pico + bajada

class Carta:
    def __init__(self, palo, valor_str):
        self.palo = palo
        self.valor_str = valor_str
        self.peso = VALORES_NUM[valor_str]
        self.key = f"{valor_str}_{palo}"

    def to_dict(self):
        return {"palo": self.palo, "valor": self.valor_str, "key": self.key, "peso": self.peso}

class Jugador:
    def __init__(self, nombre, humano=False, id_orig=0):
        self.nombre = nombre
        self.humano = humano
        self.id_orig = id_orig
        self.mano = []
        self.puntos = 0
        self.apuesta = -1
        self.bazas_ganadas = 0

    def ordenar_mano(self):
        self.mano.sort(key=lambda c: (PALOS_ORDEN.get(c.palo, 99), -c.peso))

    def obtener_legales(self, palo_salida, triunfo, mesa):
        if not palo_salida or not mesa:
            return self.mano[:]
        
        idx_g, mejor_c = mesa[0]
        for _, c in mesa[1:]:
            if (c.palo == triunfo and mejor_c.palo != triunfo) or (c.palo == mejor_c.palo and c.peso > mejor_c.peso):
                mejor_c = c
        
        asistir = [c for c in self.mano if c.palo == palo_salida]
        if asistir:
            if mejor_c.palo == palo_salida:
                superan = [c for c in asistir if c.peso > mejor_c.peso]
                if superan: 
                    return superan
            return asistir
        
        triunf = [c for c in self.mano if c.palo == triunfo]
        if triunf:
            if mejor_c.palo == triunfo:
                sup_t = [c for c in triunf if c.peso > mejor_c.peso]
                if sup_t: 
                    return sup_t
                else:
                    return self.mano[:]
            else: 
                return triunf
        return self.mano[:]

    def to_dict(self, revelar_mano=False, cartas_legales=None):
        mano_dict = []
        for c in self.mano:
            cd = c.to_dict()
            if cartas_legales is not None:
                cd["legal"] = any(leg.key == c.key for leg in cartas_legales)
            else:
                cd["legal"] = True
            mano_dict.append(cd)

        return {
            "id": self.id_orig,
            "nombre": self.nombre,
            "humano": self.humano,
            "puntos": self.puntos,
            "apuesta": self.apuesta,
            "bazas_ganadas": self.bazas_ganadas,
            "num_cartas": len(self.mano),
            "mano": mano_dict if (revelar_mano or self.humano) else []
        }

class PartidaPocha:
    def __init__(self, nombres, carta_inicio=1, manos_pico=4):
        self.jugadores = [Jugador(nomb, humano=(i == 0), id_orig=i) for i, nomb in enumerate(nombres)]
        self.reiniciar(nombres, carta_inicio, manos_pico)

    def reiniciar(self, nombres=None, carta_inicio=1, manos_pico=4):
        if nombres:
            for i, nomb in enumerate(nombres):
                if i < len(self.jugadores) and nomb.strip():
                    self.jugadores[i].nombre = nomb.strip()

        for j in self.jugadores:
            j.puntos = 0
            j.mano = []
            j.apuesta = -1
            j.bazas_ganadas = 0

        self.secuencia = generar_secuencia(carta_inicio, 10, manos_pico)
        self.repartidor_idx = random.randint(0, 3)
        self.turno_idx = (self.repartidor_idx + 1) % 4
        self.estado = "REPARTIR"
        self.mesa = []
        self.triunfo_palo = ""
        self.palo_salida = None
        self.cant_cartas = 0
        self.mensaje = "¡Nueva partida iniciada! Repartiendo..."

    def configurar_nombres(self, nombres):
        for i, nomb in enumerate(nombres):
            if i < len(self.jugadores) and nomb.strip():
                self.jugadores[i].nombre = nomb.strip()

    def repartir(self):
        if not self.secuencia:
            self.estado = "FIN"
            self.mensaje = "¡Fin de la partida! Revisa el marcador final."
            return
        self.cant_cartas = self.secuencia.pop(0)
        baraja = [Carta(p, v) for p in PALOS for v in VALORES_NUM.keys()]
        random.shuffle(baraja)
        
        for j in self.jugadores:
            j.mano = [baraja.pop() for _ in range(self.cant_cartas)]
            j.ordenar_mano()
            j.apuesta = -1
            j.bazas_ganadas = 0
            
        self.triunfo_palo = baraja.pop().palo if baraja else self.jugadores[self.repartidor_idx].mano[-1].palo
        self.turno_idx = (self.repartidor_idx + 1) % 4
        self.estado = "APUESTAS"
        self.mensaje = f"Ronda de {self.cant_cartas} carta(s). Triunfo: {self.triunfo_palo.upper()}"

    def calcular_apuesta_bot(self, jug):
        p_tri = sum(1.5 if c.valor_str in ['1','3'] else 1.0 for c in jug.mano if c.palo == self.triunfo_palo)
        p_alt = sum(0.6 if c.valor_str == '1' else 0.4 if c.valor_str == '3' else 0 for c in jug.mano if c.palo != self.triunfo_palo)
        ap = min(self.cant_cartas, round((p_tri + p_alt) * 0.65))
        
        s_a = sum(j.apuesta for j in self.jugadores if j.apuesta != -1)
        prohibido = (self.cant_cartas - s_a) if jug.id_orig == self.repartidor_idx else -1
        
        if ap == prohibido:
            if ap < self.cant_cartas:
                ap += 1
            elif ap > 0:
                ap -= 1
            else:
                ap = 1 if self.cant_cartas > 0 else 0
        return ap

    def procesar_apuesta(self, jugador_id, cantidad):
        if self.estado != "APUESTAS" or self.turno_idx != jugador_id:
            return False

        if jugador_id == self.repartidor_idx:
            s_a = sum(j.apuesta for j in self.jugadores if j.apuesta != -1 and j.id_orig != jugador_id)
            prohibido = self.cant_cartas - s_a
            if cantidad == prohibido:
                return False

        j = self.jugadores[jugador_id]
        j.apuesta = cantidad
        self.mensaje = f"{j.nombre} ha pedido {cantidad} baza(s)."
        self.turno_idx = (self.turno_idx + 1) % 4
        
        if all(jug.apuesta != -1 for jug in self.jugadores):
            self.estado = "JUGANDO"
            self.turno_idx = (self.repartidor_idx + 1) % 4
            self.mensaje = f"¡Empieza la ronda! Turno de {self.jugadores[self.turno_idx].nombre}"
        return True

    def jugar_carta_bot(self, jug):
        legales = jug.obtener_legales(self.palo_salida, self.triunfo_palo, self.mesa)
        if jug.bazas_ganadas < jug.apuesta:
            if self.mesa:
                _, mejor_m = self.mesa[0]
                for _, c_m in self.mesa[1:]:
                    if (c_m.palo == self.triunfo_palo and mejor_m.palo != self.triunfo_palo) or (c_m.palo == mejor_m.palo and c_m.peso > mejor_m.peso):
                        mejor_m = c_m
                ganadoras = [c for c in legales if (c.palo == self.triunfo_palo and mejor_m.palo != self.triunfo_palo) or (c.palo == mejor_m.palo and c.peso > mejor_m.peso)]
                carta = min(ganadoras, key=lambda c: c.peso) if ganadoras else min(legales, key=lambda c: c.peso)
            else:
                carta = max(legales, key=lambda c: (c.palo == self.triunfo_palo, c.peso))
        else:
            if self.mesa:
                _, mejor_m = self.mesa[0]
                for _, c_m in self.mesa[1:]:
                    if (c_m.palo == self.triunfo_palo and mejor_m.palo != self.triunfo_palo) or (c_m.palo == mejor_m.palo and c_m.peso > mejor_m.peso):
                        mejor_m = c_m
                perdedoras = [c for c in legales if not ((c.palo == self.triunfo_palo and mejor_m.palo != self.triunfo_palo) or (c.palo == mejor_m.palo and c.peso > mejor_m.peso))]
                carta = max(perdedoras, key=lambda c: c.peso) if perdedoras else max(legales, key=lambda c: c.peso)
            else:
                carta = min(legales, key=lambda c: (c.palo == self.triunfo_palo, c.peso))
        return carta

    def procesar_jugada(self, jugador_id, carta_key):
        j = self.jugadores[jugador_id]
        legales = j.obtener_legales(self.palo_salida, self.triunfo_palo, self.mesa)
        carta = next((c for c in j.mano if c.key == carta_key), None)
        
        if not carta or not any(leg.key == carta.key for leg in legales):
            return False
            
        j.mano.remove(carta)
        if not self.mesa:
            self.palo_salida = carta.palo
            
        self.mesa.append((jugador_id, carta))
        self.mensaje = f"{j.nombre} juega {carta.valor_str} de {carta.palo}"
        self.turno_idx = (self.turno_idx + 1) % 4
        return True

    def resolver_baza(self):
        idx_ganador, mejor = self.mesa[0]
        for idx, c in self.mesa[1:]:
            if (c.palo == self.triunfo_palo and mejor.palo != self.triunfo_palo) or (c.palo == mejor.palo and c.peso > mejor.peso):
                mejor, idx_ganador = c, idx
                
        j_gan = self.jugadores[idx_ganador]
        j_gan.bazas_ganadas += 1
        self.turno_idx = idx_ganador
        self.mesa = []
        self.palo_salida = None
        
        reaccion = random.choice(FRASES_QUEJA) if j_gan.bazas_ganadas > j_gan.apuesta else random.choice(FRASES_GANAR)
        self.mensaje = f"Baza para {j_gan.nombre}. {j_gan.nombre}: \"{reaccion}\""

        if all(len(j.mano) == 0 for j in self.jugadores):
            self.puntuacion_final_ronda()

    def puntuacion_final_ronda(self):
        for j in self.jugadores:
            if j.bazas_ganadas == j.apuesta:
                j.puntos += (5 + j.bazas_ganadas * 5)
            else:
                j.puntos -= 10
        self.repartidor_idx = (self.repartidor_idx + 1) % 4
        self.estado = "REPARTIR"

    def obtener_estado_cliente(self, jugador_id):
        j_solicitante = self.jugadores[jugador_id]
        legales = j_solicitante.obtener_legales(self.palo_salida, self.triunfo_palo, self.mesa) if (self.estado == "JUGANDO" and self.turno_idx == jugador_id) else None

        s_a = sum(j.apuesta for j in self.jugadores if j.apuesta != -1)
        prohibido = -1
        if self.estado == "APUESTAS" and self.turno_idx == self.repartidor_idx:
            p_val = self.cant_cartas - s_a
            if 0 <= p_val <= self.cant_cartas:
                prohibido = p_val

        return {
            "estado": self.estado,
            "turno": self.turno_idx,
            "repartidor": self.repartidor_idx,
            "mano_idx": (self.repartidor_idx + 1) % 4,
            "triunfo": self.triunfo_palo,
            "cant_cartas": self.cant_cartas,
            "total_apuestas": s_a,
            "prohibido": prohibido,
            "mensaje": self.mensaje,
            "mesa": [{"jugador": idx, "carta": c.to_dict()} for idx, c in self.mesa],
            "jugadores": [
                j.to_dict(
                    revelar_mano=(j.id_orig == jugador_id),
                    cartas_legales=(legales if j.id_orig == jugador_id else None)
                ) for j in self.jugadores
            ]
        }