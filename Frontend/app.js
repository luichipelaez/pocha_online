// Detecta automáticamente si debe usar 'wss:' (para HTTPS en Render) o 'ws:' (para HTTP en local)
const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
const wsUrl = `${protocol}//${window.location.host}/ws/0`;

const socket = new WebSocket(wsUrl);
let miApuestaSeleccionada = 0;
let maxCartasRonda = 1;
let prohibidoActual = -1;

const bannerMensaje = document.getElementById("mensaje-texto");
const textoTriunfo = document.getElementById("texto-triunfo");
const textoBazasTop = document.getElementById("texto-bazas-top");
const listaPuntos = document.getElementById("lista-puntuaciones");
const manoCartasContainer = document.getElementById("mano-cartas");
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

ws.onopen = () => {
    console.log("Conectado al servidor de la Pocha.");
};

ws.onmessage = (event) => {
    const estado = JSON.parse(event.data);
    actualizarPantalla(estado);
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

    // Cálculo y formato del panel superior de apuestas
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

    // Marcador y Badges (REPARTE / MANO)
    listaPuntos.innerHTML = "";
    estado.jugadores.forEach((jug) => {
        const li = document.createElement("li");
        li.innerText = `${jug.nombre}: ${jug.puntos} pts`;
        listaPuntos.appendChild(li);

        const apTxt = jug.apuesta !== -1 ? jug.apuesta : "?";
        const elemBazas = document.getElementById(`bazas-${jug.id}`);
        const elemnom = document.getElementById(`nom-${jug.id}`);
        const elemRol = document.getElementById(`rol-${jug.id}`);
        const divPos = document.getElementById(`jugador-${jug.id}`) || document.getElementById("zona-humano");

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

    // Mesa
    const mesaSlot = document.getElementById("mesa-cartas");
    mesaSlot.innerHTML = "";
    estado.mesa.forEach((item) => {
        const img = document.createElement("img");
        img.src = `cartas_img/${item.carta.key}.png`;
        img.className = "carta-img";
        mesaSlot.appendChild(img);
    });

    // Mano del humano
    manoCartasContainer.innerHTML = "";
    const yo = estado.jugadores[0];
    if (yo && yo.mano) {
        yo.mano.forEach((carta) => {
            const img = document.createElement("img");
            img.src = `cartas_img/${carta.key}.png`;
            img.className = "carta-img";

            if (estado.estado === "JUGANDO" && estado.turno === 0) {
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

    // Panel Apuestas
    if (estado.estado === "APUESTAS" && estado.turno === 0 && yo.apuesta === -1) {
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

// Botones para pedir/apostar
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

// Generador de Vista Previa de la Secuencia en el Modal
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

// Abrir / Cerrar / Iniciar Partida desde Modal
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

    ws.send(JSON.stringify({
        action: "reiniciar_partida",
        nombres: [n0, n1, n2, n3],
        carta_inicio: cartaInicio,
        manos_pico: manosPico
    }));

    modalConfig.classList.add("oculto");
};
