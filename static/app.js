function $(id){return document.getElementById(id)}

// asignar botones (por ahora solo prints en consola)
$('btn_config').addEventListener('click', ()=>console.log('Configurar'));
$('btn_descargar').addEventListener('click', ()=>console.log('Descargar Historia'));
$('btn_manual').addEventListener('click', ()=>console.log('Control Manual Bomba'));
$('btn_borrar').addEventListener('click', ()=>console.log('Borrar Historia'));

async function actualizar(){
  try{
    const r = await fetch('/status',{cache:'no-store'});
    if(!r.ok) throw new Error('HTTP '+r.status);
    const j = await r.json();

    // Valores corrientes
    $('fecha').textContent = j.fecha || '--';
    $('hora').textContent  = j.hora  || '--';

    $('tdavb').textContent = (j.ctdavb && j.ctdavb.tiempoDiarioApertura!=null) ? j.ctdavb.tiempoDiarioApertura : '--';
    $('tavb').textContent  = (j.ctdavb && j.ctdavb.tiempoAperturaAcumulado!=null) ? j.ctdavb.tiempoAperturaAcumulado : '--';
    $('tavb_pct').textContent = (j.ctdavb && j.ctdavb.tiempoAperturaAcumuladoPorcentaje!=null) ? j.ctdavb.tiempoAperturaAcumuladoPorcentaje+' %' : '--';

    $('farmaco').textContent = (j.dosificar && j.dosificar.remedioAcumulado!=null) ? j.dosificar.remedioAcumulado : '--';
    $('farmaco_pct').textContent = (j.dosificar && j.dosificar.remedioAcumuladoPorcentaje!=null) ? j.dosificar.remedioAcumuladoPorcentaje+' %' : '--';

    // Parámetros (desde params.get_all())
    const p = j.parametros || {};
    // los nombres que devolviste: q_bomba, tiempo_encendido_bomba, tiempo_descanso_bomba, carga, dosis_diaria_farmaco, porcentaje_contraccion_tdavb
    $('param_carga').textContent = p.carga!=null ? p.carga : '--';
    $('param_dosis').textContent = p.dosis_diaria_farmaco!=null ? p.dosis_diaria_farmaco : '--';
    $('param_dosis_diaria').textContent = p.DosisDiaria!=null ? p.DosisDiaria : '--';
    $('param_qbomba').textContent = p.q_bomba!=null ? p.q_bomba : '--';
    $('param_pulso').textContent = p.tiempo_encendido_bomba!=null ? p.tiempo_encendido_bomba : '--';
    $('param_descanso').textContent = p.tiempo_descanso_bomba!=null ? p.tiempo_descanso_bomba : '--';
    $('param_contraccion').textContent = p.porcentaje_contraccion_tdavb!=null ? p.porcentaje_contraccion_tdavb+' %' : '--';

    // Capacidad
    $('cap_carga_max').textContent = j.capacidad ? (j.capacidad.cargaMaxima || '--') : '--';
    $('cap_dosis_max').textContent = j.capacidad ? (j.capacidad.dosisDiariaMaxima || '--') : '--';

    $('status').textContent = 'Última actualización: ' + new Date().toLocaleTimeString();
  }catch(e){
    $('status').textContent = 'Error al obtener estado';
    console.log('fetch error',e);
  }
}

// timer cada 1s
setInterval(actualizar,1000);
// refresco rápido al abrir
actualizar();