let ws = null;
let miJugadorId = 0; // Asiento asignado por el servidor
let miApuestaSeleccionada = 0;
let maxCartasRonda = 1;
let prohibidoActual = -1;

// Elementos DOM
const modalLobby = document.getElementById("modal-lobby");
const inputMiNombre = document.getElementById("input-mi-nombre");
const selectModo = document.getElementById("select-modo");
const grupoSalasActivas = document.getElementById("grupo-salas-activas");
const selectSalasActivas = document.getElementById("select-salas-activas");
const grupoCodigoSala = document.getElementById("grupo-codigo-sala");
const inputCodigoSala = document.getElementById("input-codigo-sala");
const btnEntrarJuego = document.getElementById("btn-entrar-juego");

const bannerMensaje = document.getElementById("mensaje-texto");
const textoTriunfo = document.getElementById("texto-triunfo");
const textoBazasTop = document.getElementById("texto-bazas-top");
const listaPuntos = document.getElementById("lista-puntuaciones");
const manoCartasContainer = document.getElementById("mano-cartas");

const panelEspera = document.getElementById("panel-espera");
const textoEstadoEspera = document.getElementById("texto-estado-espera");
const btnComenzarPartida = document.getElementById("btn-comenzar-partida");

const panelApuestas = document.getElementById("panel-apuestas");
const cantApuestaSpan = document.getElementById("cant-apuesta");
const textoProhibido = document.getElementById("texto-prohibido");
const btnConfirmarApuesta = document.getElementById("btn-confirmar-apuesta");

const modalConfig = document.getElementById("modal-config");
const btnAbrirConfig = document.getElementById("btn-abrir-config");
const btnCancelarConfig = document.getElementById("btn-cancelar-config");
const btnIniciarNuevaPartida = document.getElementById("btn-iniciar-nueva-partida");
const selectCartaInicio = document.getElementById("select-carta-inicio");
const selectManosPico = document.getElementById("select-manos-pico");
const resumenSecuencia = document.getElementById("resumen-secuencia");

// Cargar lista de salas activas desde la API HTTP
async function cargarSalasActivas() {
    try {
        const response = await fetch('/api/salas');
        if (response.ok) {
            const salas = await response.json();
            selectSalasActivas.innerHTML = '';
            
            if (salas.length > 0) {
                salas.forEach(s => {
                    const opt = document.createElement('option');
                    opt.value = s.id;
                    const estadoTxt = s.iniciada ? 'En juego' : 'Esperando';
                    opt.innerText = `${s.id} (${s.humanos}/4 jug. - ${estadoTxt})`;
                    selectSalasActivas.appendChild(opt);
                });
            }
            
            const optNueva = document.createElement('option');
            optNueva.value = 'nueva';
            optNueva.innerText = '+ Crear nueva sala...';
            selectSalasActivas.appendChild(optNueva);

            actualizarVisibilidadSeleccionSala();
        }
    } catch (e) {
        console.error("Error al cargar salas activas:", e);
    }
}

function actualizarVisibilidadLobby() {
    if (selectModo.value === "bots") {
        grupoSalasActivas.classList.add("oculto");
        grupoCodigoSala.classList.add("oculto");
    } else {
        grupoSalasActivas.classList.remove("oculto");
        cargarSalasActivas();
    }
}

function actualizarVisibilidadSeleccionSala() {
    if (selectSalasActivas.value === "nueva") {
        grupoCodigoSala.classList.remove("oculto");
    } else {
        grupoCodigoSala.classList.add("oculto");
    }
}

selectModo.onchange = actualizarVisibilidadLobby;
selectSalasActivas.onchange = actualizarVisibilidadSeleccionSala;
actualizarVisibilidadLobby();

// Entrar a la partida
btnEntrarJuego.onclick = () => {
    const nombre = inputMiNombre.value.trim() || "Luis";
    const modo = selectModo.value;
    
    let sala = "";
    if (modo === "bots") {
        sala = "solo_" + Math.random().toString(36).substring(2, 7);
    } else {
        if (selectSalasActivas.value === "nueva" || !selectSalasActivas.value) {
            sala = inputCodigoSala.value.trim() || "sala1";
        } else {
            sala = selectSalasActivas.value;
        }
    }

    modalLobby.classList.add("oculto");
    conectarASala(sala, nombre, modo);
};

function conectarASala(salaId, nombreJugador, modo) {
    if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
        ws.close();
    }

    const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' || window.location.protocol === 'file:';
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = isLocal ? 'localhost:8000' : window.location.host;

    const wsUrl = `${protocol}//${host}/ws/${salaId}?nombre=${encodeURIComponent(nombreJugador)}&modo=${modo}`;
    
    bannerMensaje.innerText = "Conectando al servidor...";
    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
        console.log(`Conectado a la sala: ${salaId}`);
        bannerMensaje.innerText = "¡Conectado a la sala!";
    };

    ws.onmessage = (event) => {
        const estado = JSON.parse(event.data);
        
        if (estado.tu_id !== undefined) {
            miJugadorId = estado.tu_id;
        }

        actualizarPantalla(estado);
    };

    ws.onerror = (err) => {
        console.error("Error en WebSocket:", err);
        bannerMensaje.innerText = "Error de conexión con el servidor.";
    };
}

// Botón para comenzar la partida en multijugador
btnComenzarPartida.onclick = () => {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ action: "iniciar_partida" }));
    }
};

function actualizarEstadoBotonApuesta() {
    cantApuestaSpan.innerText = miApuestaSeleccionada;
    if (prohibidoActual !== -1 && miApuestaSeleccionada === prohibidoActual) {
        btnConfirmarApuesta.disabled = true;
    } else {
        btnConfirmarApuesta.disabled = false;
    }
}

function actualizarPantalla(estado) {
    bannerMensaje.innerText = estado.mensaje;
    textoTriunfo.innerText = `TRIUNFO: ${estado.triunfo ? estado.triunfo.toUpperCase() : '-'}`;
    maxCartasRonda = estado.cant_cartas;
    prohibidoActual = (estado.prohibido !== undefined) ? estado.prohibido : -1;

    // Manejo del Panel de Espera Multijugador
    if (estado.esperando_inicio) {
        panelEspera.classList.remove("oculto");
        textoEstadoEspera.innerText = `Conectados: ${estado.num_conectados}/4 jugadores.\n${estado.mensaje}`;
    } else {
        panelEspera.classList.add("oculto");
    }

    // Marcador y superior
    const totalPedidas = estado.total_apuestas;
    const totalCartas = estado.cant_cartas;
    let estadoPedidaTexto = "";

    if (totalPedidas < totalCartas) {
        const dif = totalCartas - totalPedidas;
        estadoPedidaTexto = `(${dif} a la baja)`;
    } else if (totalPedidas > totalCartas) {
        const dif = totalPedidas - totalCartas;
        estadoPedidaTexto = `(${dif} al alza)`;
    } else {
        estadoPedidaTexto = `(Exactas)`;
    }
    textoBazasTop.innerText = `Pedidas: ${totalPedidas} / ${totalCartas} ${estadoPedidaTexto}`;

    // Posicionamiento dinámico relativo en mesa
    listaPuntos.innerHTML = "";
    estado.jugadores.forEach((jug) => {
        const li = document.createElement("li");
        li.innerText = `${jug.nombre}: ${jug.puntos} pts`;
        listaPuntos.appendChild(li);

        const relPos = (jug.id - miJugadorId + 4) % 4;

        const apTxt = jug.apuesta !== -1 ? jug.apuesta : "?";
        const elemBazas = document.getElementById(`bazas-${relPos}`);
        const elemnom = document.getElementById(`nom-${relPos}`);
        const elemRol = document.getElementById(`rol-${relPos}`);
        const divPos = document.getElementById(`jugador-${relPos}`) || document.getElementById("zona-humano");

        if (elemBazas) elemBazas.innerText = `Bazas: ${jug.bazas_ganadas}/${apTxt}`;
        if (elemnom) elemnom.innerText = jug.nombre;

        if (elemRol) {
            if (jug.id === estado.repartidor) {
                elemRol.innerText = "REPARTE";
                elemRol.className = "badge-rol badge-repartidor";
            } else if (jug.id === estado.mano_idx) {
                elemRol.innerText = "MANO";
                elemRol.className = "badge-rol badge-mano";
            } else {
                elemRol.innerText = "";
                elemRol.className = "badge-rol";
            }
        }

        if (divPos) {
            if (estado.turno === jug.id) {
                divPos.classList.add("turno-activo");
            } else {
                divPos.classList.remove("turno-activo");
            }
        }
    });

    // Cartas en Mesa
    const mesaSlot = document.getElementById("mesa-cartas");
    mesaSlot.innerHTML = "";
    estado.mesa.forEach((item) => {
        const img = document.createElement("img");
        img.src = `cartas_img/${item.carta.key}.png`;
        img.className = "carta-img";
        mesaSlot.appendChild(img);
    });

    // Mano Jugador Local
    manoCartasContainer.innerHTML = "";
    const yo = estado.jugadores[miJugadorId];
    if (yo && yo.mano) {
        yo.mano.forEach((carta) => {
            const img = document.createElement("img");
            img.src = `cartas_img/${carta.key}.png`;
            img.className = "carta-img";

            if (estado.estado === "JUGANDO" && estado.turno === miJugadorId) {
                if (carta.legal) {
                    img.classList.add("carta-jugable");
                    img.onclick = () => {
                        ws.send(JSON.stringify({ action: "jugar", carta: carta.key }));
                    };
                } else {
                    img.classList.add("carta-bloqueada");
                }
            }
            manoCartasContainer.appendChild(img);
        });
    }

    // Panel de Apuestas
    if (estado.estado === "APUESTAS" && estado.turno === miJugadorId && yo && yo.apuesta === -1) {
        if (panelApuestas.classList.contains("oculto")) {
            panelApuestas.classList.remove("oculto");
            miApuestaSeleccionada = 0;
        }

        if (prohibidoActual !== -1) {
            textoProhibido.innerText = `Prohibido pedir ${prohibidoActual}`;
        } else {
            textoProhibido.innerText = "";
        }
        actualizarEstadoBotonApuesta();
    } else {
        panelApuestas.classList.add("oculto");
    }
}

// Botones Pedir / Apostar
document.getElementById("btn-mas").onclick = () => {
    if (miApuestaSeleccionada < maxCartasRonda) {
        miApuestaSeleccionada++;
        actualizarEstadoBotonApuesta();
    }
};

document.getElementById("btn-menos").onclick = () => {
    if (miApuestaSeleccionada > 0) {
        miApuestaSeleccionada--;
        actualizarEstadoBotonApuesta();
    }
};

btnConfirmarApuesta.onclick = () => {
    if (prohibidoActual !== -1 && miApuestaSeleccionada === prohibidoActual) {
        return;
    }
    ws.send(JSON.stringify({ action: "apostar", cantidad: miApuestaSeleccionada }));
    panelApuestas.classList.add("oculto");
    miApuestaSeleccionada = 0;
    cantApuestaSpan.innerText = 0;
};

// Secuencia de juego
function actualizarResumenSecuencia() {
    const inicio = parseInt(selectCartaInicio.value);
    const pico = parseInt(selectManosPico.value);
    
    let manos = [];
    for (let c = inicio; c < 10; c++) manos.push(c);
    for (let i = 0; i < pico; i++) manos.push(10);
    for (let c = 9; c >= inicio; c--) manos.push(c);

    resumenSecuencia.innerText = `Partida de ${manos.length} manos (${manos.slice(0, 4).join(', ')} ... ${manos.slice(-3).join(', ')})`;
}

selectCartaInicio.onchange = actualizarResumenSecuencia;
selectManosPico.onchange = actualizarResumenSecuencia;

btnAbrirConfig.onclick = () => {
    actualizarResumenSecuencia();
    modalConfig.classList.remove("oculto");
};

btnCancelarConfig.onclick = () => {
    modalConfig.classList.add("oculto");
};

btnIniciarNuevaPartida.onclick = () => {
    const n0 = document.getElementById("input-nom-0").value;
    const n1 = document.getElementById("input-nom-1").value;
    const n2 = document.getElementById("input-nom-2").value;
    const n3 = document.getElementById("input-nom-3").value;

    const cartaInicio = parseInt(selectCartaInicio.value);
    const manosPico = parseInt(selectManosPico.value);

    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
            action: "reiniciar_partida",
            nombres: [n0, n1, n2, n3],
            carta_inicio: cartaInicio,
            manos_pico: manosPico
        }));
    }

    modalConfig.classList.add("oculto");
};
