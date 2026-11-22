ORQUESTADOR DE ARRANQUE — Diagnóstico de liquidez global (Guiver Research) · P-040 paso 4
Este archivo sustituye a sistema/orquestador.md en el Project "REPORTES POR PARTES". El orquestador de verdad vive en el repo privado mane-spec/guiver-datos, en la marca «vigente» (solo avanza cuando pasan los tests de GitHub Actions). Las salidas de cada semana (semanas/, pruebas/) y el registro (registro/) siguen en el proyecto.

ARGUMENTOS: los mismos que te han pasado (MODO, MODO_PRUEBA). Pásalos sin cambios al orquestador del repo.

1. Crea T = <pwd>/trabajo/.
2. Añade el repo a la sesión con add_repo (owner "mane-spec", repo "guiver-datos", access "read") y clónalo UNA vez en la marca vigente, con tiempo de espera generoso (~10 min):
   git clone --depth 1 --branch vigente https://github.com/mane-spec/guiver-datos T/guiver-datos
3. Comprueba el sistema: cd T/guiver-datos && python3 sistema/comprobar.py → debe terminar en "comprobación OK".
4. Copia a T, con los nombres que usa el orquestador: sistema/manifiesto.json, contrato.md, investigadores.md, motor/motor.py, prompts/parte1-v2.md, parte2-v5.1.md, parte3-v6.3.md, final-v1.md, simulador/plantilla.html y simulador/build.py (todos planos en T, como hasta ahora: T/motor.py, T/plantilla.html…).
5. Lee íntegro T/guiver-datos/sistema/orquestador.md y síguelo, con estos cambios:
   - FASE 0 paso 2: los archivos de sistema/ NO se descargan del proyecto: ya están en T desde el repo y su verificación es la del paso 3 de este arranque (sustituye a la del manifiesto). Del proyecto solo se descargan registro/historial.json y registro/propuestas.md.
   - FASE 0 paso 5: el repo ya está clonado en T/guiver-datos; no lo clones otra vez. La regla «no ejecutes código del repo» no se aplica a sistema/ de la marca vigente (motor, build y comprobar.py), que es el código del sistema; sí se aplica al resto del repo (datos.py, sondas.py…), que no se ejecuta.
   - Todo lo demás (fases 1–3, subidas al proyecto después de cada paso, avisos) sin cambios.
6. VUELTA ATRÁS (P-040 paso 7).
   - Si el clon funcionó pero comprobar.py falla: no uses la marca vigente; sigue con el orquestador O7 tal cual (T/guiver-datos/copias-sistema/orquestador-O7-cabecera-18nov.md), que descarga los archivos de sistema/ del proyecto y los verifica con su manifiesto (siguen en el proyecto hasta que el usuario libere espacio). Anótalo en incidencias en cuanto exista estado.json: "arranque desde el repo fallido: <motivo>; se usa O7 con los archivos del proyecto".
   - Si add_repo no existe o el clon falla tras un reintento: no hay orquestador que seguir. Aviso al usuario (SendUserMessage y PushNotification si está disponible) con el motivo exacto y la solución: volver a poner en sistema/orquestador.md del proyecto la copia O7 (repo mane-spec/guiver-datos, copias-sistema/orquestador-O7-cabecera-18nov.md, idéntica a sistema/orquestador.md del repo). Fin.
