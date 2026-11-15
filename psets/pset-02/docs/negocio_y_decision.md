# Formulación y contrato de decisión del proyecto

Autor: Ron. Revisión: 12/11/2026. Configuración ejecutable: `scripts/business_assumptions.json`.

## 1. Qué decisión puede sostener AI4I

El producto del semestre es un **prototipo de detección y priorización de revisión de fallas presentes**, con la etiqueta `MACHINE_FAILURE` de la misma observación. Unidad: una lectura UDI dentro de una versión del CSV. Horizonte de la etiqueta: **t = observación actual, sin adelanto temporal**. El técnico revisa la alerta durante la siguiente ronda operativa, con objetivo propuesto de atención en 30 minutos; ese SLA no cambia el horizonte de la etiqueta y no está medido en AI4I. La alerta no ordena detener ni sustituye protocolos de seguridad.

Se retiran las promesas del pitch de “probabilidad de falla en el siguiente ciclo”, entrega “antes de cada ciclo” y RUL. `LOADED_AT`, el cron semanal, el orden UDI y `TOOL_WEAR_MIN` no proporcionan un tiempo hasta falla ni una secuencia validada por máquina. El PSet 2 prepara los datos y calcula una referencia determinista; todavía no entrena ni sirve probabilidades de un modelo.

Para anticipar fallas harían falta IDs persistentes de activos, timestamps de medición/falla/intervención, disponibilidad de señales antes del evento y una ventana definida, por ejemplo falla en las próximas 24 horas. Esa formulación es futura y exige reconstruir etiquetas y validación temporal con datos reales.

## 2. Comparación de las tres ideas

| Idea | Valor y acción | Condición de viabilidad y decisión |
| --- | --- | --- |
| Vida útil restante (RUL) | Programar recambio según tiempo de vida remanente | Requiere trayectorias por activo y tiempos de falla/censura. AI4I no permite validar RUL. Se descarta con esta fuente, aunque el valor potencial sea alto. |
| Pronóstico de demanda | Ajustar inventario y evitar quiebres/exceso | Requiere ventas por fecha/SKU, inventario y costos de faltante/almacenamiento. No se aportó esa fuente; no se declara inviable en general ni se le asigna una puntuación ficticia. |
| Detección de falla presente | Priorizar revisión humana de un estado sospechoso | Etiqueta y variables observables, acceso abierto y recorrido ELT verificable. Se selecciona como demostrador técnico, condicionado a validar decisiones/costos en planta. |

La selección privilegia correspondencia entre target, acción y evidencia disponible. Las 10.000 filas reducen el esfuerzo computacional, pero no acreditan utilidad de negocio. Los datos sintéticos pueden reproducir las reglas del generador; un puntaje alto no prueba transferencia, ahorro ni anticipación. Las 339 fallas observadas no se convierten en una tasa de incidentes de una planta.

## 3. Línea base exacta y trazable

Nombre: `UCI_PHYSICS_WEAR200_v1`. Se alerta si se cumple al menos una condición:

1. Temperatura de proceso menos temperatura de aire **< 8,6 K** y velocidad **< 1380 rpm**.
2. Potencia `torque * rpm * 2*pi/60` **< 3500 W o > 9000 W**.
3. Desgaste por torque **> 11000 / 12000 / 13000 min·Nm** para tipo **L / M / H**, respectivamente.
4. Desgaste de herramienta **>= 200 minutos**.

Las tres primeras condiciones proceden de la descripción de los mecanismos sintéticos de [UCI AI4I](https://archive.ics.uci.edu/dataset/601/ai4i+2020+predictive+maintenance+dataset). La cuarta es una heurística conservadora propuesta para el proyecto, no la reconstrucción exacta de su mecanismo aleatorio de desgaste. No utiliza el target ni TWF/HDF/PWF/OSF/RNF como entradas. La implementación Python y la expresión Spark comparten los parámetros versionados y se contrastan en tests.

Esta es una **candidata a regla de expertos**, pendiente de revisión y firma del responsable de mantenimiento. No se atribuye su aprobación a un experto inexistente. Además de esta regla, se reportan “nunca alertar” y “siempre alertar” como referencias de control; el calendario fijo no puede reconstruirse sin historial de mantenimiento. La regresión logística será otra referencia en la etapa de modelado.

Evaluación descriptiva del CSV completo, sin entrenamiento ni selección de umbrales con esos resultados: TP=330, FP=678, FN=9, TN=8983; precisión=32,74%, recall=97,35%, alertas=10,08%. Estos valores **no son un resultado de generalización**; la regla conoce parte del mecanismo generador. El futuro modelo debe compararse en un conjunto reservado y la aprobación de planta requiere datos prospectivos reales.

`BASELINE_ALERT` y `BASELINE_RULE_VERSION` se guardan en la OBT para comparar políticas. Son referencias de decisión, no features de entrenamiento. Tampoco se usan los IDs, hashes, fecha de carga ni flags de subtipo como predictores.

## 4. Planta de referencia y costos propuestos

Todos los importes siguientes son **supuestos ilustrativos en USD, no cotizaciones ni costos observados**. Planta hipotética: 20 equipos, dos turnos de 8 horas, 5 días/semana, una oportunidad de revisión por equipo-día y capacidad de 5 inspecciones/día. El flujo académico sigue semanal porque la fuente es estática; no satisface ni demuestra un SLA de 30 minutos.

| Concepto | Supuesto | Cálculo |
| --- | --- | --- |
| Margen de contribución perdido por hora detenida | USD 300/h | Usar margen neto de costos variables evitables, no ventas brutas. |
| Mantenimiento planificado | Directo USD 800; 2 horas de paro | `C_P = 800 + 2*300 = USD 1400` |
| Mantenimiento de emergencia | Directo USD 2200; 8 horas de paro | `C_E = 2200 + 8*300 = USD 4600` |
| Inspección por alerta | USD 50 | Incluye tiempo técnico; no volver a sumarlo como mano de obra adicional. |
| Demora incremental de una falla presente omitida | 4 horas extra y USD 800 de daño secundario | `C_D = 4*300 + 800 = USD 2000` |

No se suman `C_E` y `C_D` para valorar cada FN: son escenarios distintos. `C_E - C_P = USD 3200` sería una diferencia planificado/emergencia solo si realmente se pudiera intervenir antes; AI4I no acredita esa capacidad. La decisión actual se analiza con costos incrementales de inspección/demora y omite reparaciones comunes a ambas políticas.

Para cuantificar errores de la alternativa RUL: sobreestimar la vida y posponer un recambio puede convertir el supuesto costo planificado de USD 1400 en USD 4600 de emergencia, un exceso de USD 3200. Subestimarla puede adelantar un mantenimiento innecesario de USD 1400; si una pieza de USD 500 conserva el 25% de su vida, USD 125 representan vida desperdiciada **dentro de ese costo**, no otro monto que sumar. Son ejemplos para comparar ideas, no pérdidas medidas ni predicciones de RUL del proyecto.

## 5. Matriz de costos y umbral específico

Para detectar una falla presente, se propone: `C_TN=0`, `C_FP=50`, `C_TP=50` y `C_FN=2000`. El TP también exige inspección; no se considera gratis. Los FN pueden prolongar la exposición al daño; los FP consumen capacidad técnica. Se requiere validación experta de que una detección más rápida pueda reducir realmente esa demora.

Para una futura probabilidad **calibrada del estado actual** `p`, alertar cuesta `C_I` y no alertar cuesta `p*C_D`. Se fija `t=C_I/C_D=50/2000=0,025`: alertar cuando `p >= 0,025`. El empate se resuelve a favor de revisar. Si `C_I/C_D>1`, ninguna probabilidad permite justificar la inspección con esta matriz. Este umbral reemplaza el rango arbitrario de 60-70%; no se aplica a la regla binaria como si esta fuera una probabilidad. Aún no existe modelo calibrado en PSet 2.

Capacidad futura: como máximo 5 revisiones diarias; cuando exceda la capacidad, priorizar por probabilidad y registrar lo que queda pendiente, con supervisión del planificador. La seguridad y los procedimientos de planta prevalecen. Evaluar esta política con capacidad, no asumir que el umbral económico irrestricto siempre se puede ejecutar.

## 6. Sensibilidad reproducible

`scripts/evaluar_negocio.py` evalúa las tres referencias por versión de fuente y nueve combinaciones de inspección USD 25/50/100 y pérdida por demora USD 1000/2000/4000. Las alertas de la regla permanecen fijas; solo cambia su valoración económica. El rango del umbral para un futuro modelo es 0,625%-10%.

| Escenario | Costos por 1000 observaciones: regla / nunca alertar | Interpretación |
| --- | --- | --- |
| Base: inspección 50, demora 2000 | USD 6840 / 67800; umbral 2,5% | Valoración retrospectiva con costos supuestos. |
| Menor inspección y demora: 25, 1000 | USD 3420 / 33900; umbral 2,5% | Cambiar ambos costos por el mismo factor conserva el umbral. |
| Inspección cara, demora menor: 100, 1000 | USD 10980 / 33900; umbral 10% | Las falsas alertas pesan más. |
| Inspección barata, demora mayor: 25, 4000 | USD 6120 / 135600; umbral 0,625% | La omisión pesa más y el umbral disminuye. |

En la cuadrícula probada la regla tiene menor costo que las referencias constantes. Eso no autoriza despliegue ni demuestra ahorros causales. No se presentan esos montos como ahorro anual o mensual, porque las filas sintéticas no son una serie de producción ni activos independientes. Los resultados completos quedan en `output/negocio.json` y en la evidencia de ejecución.

La sensibilidad también descompone el margen/hora: con USD 150/300/600, el planificado resulta USD 1100/1400/2000; la emergencia USD 3400/4600/7000; la demora incremental USD 1400/2000/3200 y el umbral 3,57%/2,5%/1,56%, manteniendo el resto constante. Son escenarios, no precios estimados del sector.

Para operación, **solo bajo el supuesto de que se repitiera la mezcla sintética**, 10/20/50 oportunidades diarias producirían 1,008/2,016/5,04 alertas medias de la regla; con 20 equipos y 3 oportunidades/día serían 6,048. Los dos últimos casos superarían la capacidad propuesta de 5 revisiones. Son cálculos de dimensionamiento hipotético, no pronósticos de carga real. Aumentar turnos no implica automáticamente nuevas observaciones: debe definirse la frecuencia de decisión para evitar alertas duplicadas del mismo evento.

## 7. Fuente y procedimiento para sustituir los supuestos

Solicitar 12 meses anonimizados de órdenes de trabajo del CMMS/ERP: ID persistente de activo y familia, timestamps de detección/falla/inicio/fin/reinicio, clasificación planificado/emergencia, horas técnicas y tarifa, repuestos/facturas, urgencias, scrap, producción recuperable y margen de contribución por hora. No inferir margen a partir de ventas brutas ni contar otra vez pérdidas recuperadas después.

Seleccionar al menos 30 intervenciones de cada tipo cuando existan; emparejar por familia de equipo, severidad y trabajo comparable. Calcular costo directo más paro no recuperable por margen/hora; resumir mediana y P25/P75 y documentar tamaño de muestra. Si no hay 30 casos, usar todos los disponibles y explicitar incertidumbre. Para el costo incremental de demora, contrastar fallas comparables con tiempos de respuesta distintos y estimar cuánto paro/daño es atribuible a la demora; no tratar toda la reparación como evitable. Sin identificación causal, mantener rangos y validar prospectivamente.

Si falta historial, realizar una sesión estructurada con mantenimiento y finanzas, obtener cotizaciones fechadas de proveedores y escenarios bajo/base/alto firmados. La [guía O&M de DOE/FEMP](https://www.energy.gov/sites/default/files/2020/04/f74/omguide_complete_w-eo-disclaimer.pdf) aporta contexto metodológico; no se trasladan sus promedios a esta planta ni se presentan como precios actuales. Los costos del proyecto se reemplazan con evidencia local y se versionan antes de abrir el test final.

## 8. Criterio para pasar a piloto y para implementar

En la etapa de modelado se elegirá el umbral en validación, se calibrarán probabilidades y se reservará un test. Las métricas de síntesis serán PR-AUC, recall, precisión, carga de alertas y costo de la política. Nunca usar accuracy como criterio principal ni convertir el orden UDI en un horizonte temporal. Una partición estratificada del snapshot es exploratoria; analizar también la sensibilidad a bloques de UDI por posible dependencia del generador. No mezclar copias/versiones de una observación entre train y test.

La propuesta exige simultáneamente: **reducción de costo variable de al menos 10% frente a la mejor referencia factible**, límite inferior del IC95% de la diferencia pareada de ahorro **>0**, recall **>=80%**, precisión **>=30%** y capacidad **<=5 revisiones/día**. La regresión logística se incorpora a la comparación cuando exista. En datos reales, la incertidumbre se estima por bloques de activo/día, no suponiendo independencia entre lecturas repetidas.

Ejemplo de ese margen bajo los costos base y únicamente las referencias actuales: frente a USD 6840 por 1000 casos de la regla, el futuro candidato debería costar como máximo USD 6156 por 1000 (mejora mínima USD 684), además de cumplir el intervalo de incertidumbre y las demás condiciones. Si una referencia posterior, como logística, mejora ese costo, el umbral de aceptación se recalcula frente a ella; este ejemplo no es un resultado de un modelo.

Además, beneficio neto anual con volumen real debe ser positivo después de infraestructura y puesta en marcha. Presupuesto ilustrativo: máximo USD 200/mes de operación y USD 1200 de implementación en el primer año (USD 3600/año); no es una oferta de proveedor. Fórmula: `N_real*(costo_baseline_por_caso - costo_modelo_por_caso) - 3600 > 0`. La inspección ya está en el costo por caso y no se duplica. Si no hay volumen real, no calcular ROI anual.

Superar estos criterios en datos sintéticos solo habilita solicitar un piloto: **no autoriza implementar**. Para implementación se requiere un piloto real prospectivo de 4 semanas, costos validados, revisión experta de las reglas, datos de señales disponibles al decidir y aceptación del patrocinador. Los valores son una propuesta de aceptación pendiente de firma, no metas alcanzadas por un modelo que aún no existe.

## 9. Entregables por etapa y petición al patrocinador

| Etapa | Entregable verificable | Criterio de salida |
| --- | --- | --- |
| Formulación / PSet 1 corregido | Target presente, comparación de ideas y contrato de decisión | Patrocinador reconoce límites de datos sintéticos y horizonte t=0. |
| Datos / PSet 2 | ELT reproducible, pruebas, star schema, OBT, baseline y sensibilidad versionadas | Kestra exitoso, conteos reconciliados, sin fuga del target y memo <=6 páginas. |
| Exploración / features | Diccionario, plan de partición, análisis de desbalance y fugas | Features justificadas y snapshot/splits congelados. |
| Modelado | Regla, logística y candidato; calibración, PR-AUC, matriz de confusión y costo en test | Evaluación sin ajustar el test y propuesta de umbral documentada. |
| Demo / despliegue académico | Servicio que clasifica una lectura presente y explica la alerta | Contrato de entrada/salida, validaciones y revisión humana; sin integración a sensores reales. |
| Monitoreo / cierre | Tablero de datos, alertas/capacidad y drift; informe go/no-go | Sin ROI real afirmado sin piloto; backlog de datos temporales para otra formulación. |

**Solicitud concreta:** autorizar un piloto en modo sombra de 4 semanas para 20 equipos de referencia, sin paradas automáticas; entregar en 10 días hábiles el extracto anonimizado CMMS/ERP de 12 meses y costos anteriores; designar un responsable de mantenimiento y otro de finanzas para dos sesiones de 60 minutos, validar regla, matriz de costos y capacidad de 5 revisiones/día, y aprobar o corregir el presupuesto propuesto. El primer resultado solicitado es acceso a datos y validación de supuestos, no compra ni despliegue del modelo.

## 10. Trazabilidad de los comentarios recibidos

| Comentario del PSet 1 | Cambio concreto | Evidencia |
| --- | --- | --- |
| Consecuencias de errores en tres ideas | RUL sobreestimada/subestimada con ejemplos y costos sin doble conteo | Secciones 2 y 4 |
| Selección y datos sintéticos | Selección por target/acción y límites de transferencia | Secciones 1 y 2 |
| Horizonte, umbral y expertos | t=0, umbral 2,5% condicionado a calibración y regla exacta provisional | Código de política y secciones 3/5 |
| Fuente de costos | CMMS/ERP, muestreo comparable y respaldo con cotizaciones/entrevistas | Sección 7 |
| Supuestos y sensibilidad | Planta explícita, matriz y nueve escenarios ejecutables | JSON versionado y reporte negocio |
| Margen para implementar | Mejora >=10%, IC95% >0, capacidad, beneficio neto y piloto real | Sección 8 |
| Entregable por etapa | Tabla de artefactos y criterios de salida | Sección 9 |
| Petición al patrocinador | Plazo, datos solicitados, responsables, sesiones y piloto | Sección 9 |
