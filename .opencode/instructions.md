# Graphify — Grafo de dependencias del proyecto

Antes de análisis de arquitectura, refactorizaciones globales o búsquedas profundas:

1. **Verificar grafo actualizado**: `graphify-out/graph.json` existe. Si acaba de arrancar una sesión nueva y el grafo no está actualizado, ejecutar `graphify update` o `/graphify --update` desde la raíz del proyecto.

2. **Consultar antes de leer archivos**: Usar `graphify query "<pregunta>"` en vez de abrir archivos uno por uno. Ejemplos:
   - `graphify query "cómo se conecta historial_inscripcion con solicitudes"`
   - `graphify query "qué archivos importan a DetalleProgramaAlumno"`

3. **Leer el reporte**: `graphify-out/GRAPH_REPORT.md` contiene el resumen con god nodes, comunidades y preguntas sugeridas.

4. **Actualizar tras cambios significativos**: Después de agregar/quitar archivos o modificar imports, correr `graphify --update` para re-extraer solo los archivos cambiados.

5. **Full rebuild**: Si el grafo está corrupto o se quiere regenerar desde cero, borrar `graphify-out/` y correr `/graphify .`
