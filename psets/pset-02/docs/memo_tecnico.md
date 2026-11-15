# PSet 2 - Detección de fallas presentes y priorización de revisión

Autor: Ron. Fecha de revisión: 12 de noviembre de 2026.

## 1. Problema, selección y arquitectura

El objetivo es detectar el estado de falla de la observación actual (target MACHINE_FAILURE) y priorizar revisión humana. El horizonte es t=0: AI4I no permite estimar vida útil ni falla en el siguiente ciclo. El objetivo futuro de atención en 30 minutos es un SLA operativo propuesto, no un horizonte predictivo ni una capacidad demostrada por el pipeline semanal. El técnico valida antes de actuar; no se automatizan paradas.

| Idea | Acción y valor | Selección con los datos disponibles |
| --- | --- | --- |
| Vida útil restante | Programar recambio | Sin trayectorias por activo ni tiempos hasta falla, AI4I no valida RUL. |
| Demanda | Ajustar inventario | Se requiere otra fuente con fecha, SKU, ventas y costos; no fue aportada. |
| Falla presente | Priorizar inspección | Target observable y acción delimitada; seleccionada como demostrador condicionado a datos reales. |

La selección depende de correspondencia target-acción-evidencia; el tamaño del archivo solo facilita el cómputo. Los datos sintéticos pueden favorecer reglas de su generador y no acreditan utilidad industrial ni ahorros. Para anticipación se necesitarían activos persistentes, timestamps de señales, fallas e intervenciones y nuevas etiquetas temporales.

Kestra descarga y orquesta la carga; dbt construye Bronze/Silver/Gold; Spark genera la OBT en Snowflake. PostgreSQL guarda metadatos de Kestra. Compose define Kestra, PostgreSQL y runners Spark/pipeline. Python 3.11, Java 17, Spark 3.5.5, dbt Snowflake 1.9.4 y conector 3.14.0 están fijados. La clave privada no se versiona; el rol operativo PSET2_INGEST no es administrador.

## 2. Ingesta, backfill y entregables

La fuente es AI4I 2020 de UCI, id 601: 10.000 observaciones y 14 columnas. El grano es una lectura UDI en una versión del CSV. No hay timestamps de medición; UDI, desgaste, fecha de carga y orden de filas no se convierten en tiempo hasta falla.

El trigger revisa la fuente estática los viernes a las 08:00 de America/Guayaquil. RAW.AI4I_OBSERVATIONS conserva las columnas como texto y añade SHA256, URL, lote y timestamp de carga. Se verifica el contrato, cantidad de filas y UDI único. write_pandas carga staging temporal y MERGE inserta solo claves (source_sha256, udi) nuevas. Una versión distinta se conserva separada; repetir la misma es idempotente. No se reemplaza la antigua RAW.AI4I.

Descarga y pipeline tienen retry constante de 30 segundos y maxAttempts=3. Los errores hacen fallar el flow; no se ocultan cargas en afterExecution. La concurrencia es 1. El backfill ordena UDI y selecciona por batch_id/batch_size: -1 carga todo; con tamaño 1000, lotes 0..9 cubren la fuente. Índices/tamaños inválidos fallan. Una interrupción puede dejar capas parciales; reejecutar reconcilia los resultados. La OBT previa se conserva hasta validar su reemplazo.

| Etapa | Entregable específico | Criterio de salida |
| --- | --- | --- |
| Formulación corregida | Target presente, regla y contrato económico | Supuestos y horizonte reconocidos por el patrocinador. |
| PSet 2 / datos | ELT, tests, star schema, OBT, baseline y sensibilidad | Kestra exitoso, conteos reconciliados y memo de 6 páginas. |
| Exploración / features | Diccionario, auditoría de fugas y plan de splits | Snapshot y particiones congelados. |
| Modelado | Regla, logística y candidato calibrado | PR-AUC, recall, precisión, costo y umbral evaluados sin ajustar el test. |
| Demo / monitoreo | Servicio para lectura actual y tablero de calidad/carga/drift | Revisión humana y reporte go/no-go; sin conexión a sensores reales. |

## 3. Calidad y preparación de datos

El CSV auditado y la consulta Snowflake contienen 10.000 filas; 0 celdas nulas en la fuente, 0 UDI duplicados, 339 fallas (3,39%) y 27 discrepancias entre target y subtipos. Los tipos observados son L=6000, M=2997, H=1003. Esta prevalencia no es una tasa de fallas de una planta.

| Dimensión / problema | Evidencia | Acción y justificación |
| --- | --- | --- |
| Completitud e identidad | 0 nulos y 0 UDI duplicados | Validar en cada carga; no imputar sin necesidad. MERGE evita duplicados del mismo snapshot. |
| Validez | Aire 295,3-304,5 K; proceso 305,7-313,8 K; rpm 1168-2886; torque 3,8-76,6 Nm; desgaste 0-253 min | Casts explícitos, categorías conocidas y flags binarios; Kelvin/rpm positivos y torque/desgaste no negativos. Rangos observados no son límites universales. |
| Consistencia | 27 discrepancias target/subtipos | Marcar y conservar el target; no hay evidencia independiente para decidir cuál corregir. |
| Precisión | Dataset sintético, sin medición independiente | Verificar unidades y contrato; no afirmar exactitud física ni transferencia a otra planta. |

Bronze utiliza TRY_TO_NUMBER/TRY_TO_DOUBLE y normaliza texto. Silver calcula rejection_reason y failure_flag_mismatch. AI4I_CLEAN conserva válidos; AI4I_REJECTED conserva rechazados con motivo. QUALITY_REPORT presenta conteos, rangos y discrepancias por hash. Se exige RAW = válidos + rechazados y Silver = hechos Gold: no hay filtros con pérdidas silenciosas. En la ejecución validada hubo 10.000 válidos y 0 rechazados.

La OBT excluye TWF/HDF/PWF/OSF/RNF y la discrepancia porque revelan el target. IDs, hashes, procedencia, fecha de carga y las columnas de baseline son trazabilidad/referencias, no features. Se debe confirmar que las seis variables operativas estén disponibles al decidir. No se mezclan copias de una observación entre train y test: para modelar se fija un snapshot.

La etapa futura usará una partición estratificada exploratoria y sensibilidad por bloques UDI, sin llamarla validación temporal. La dependencia del generador puede volver optimistas los resultados. Un piloto real requerirá particiones y estimación de incertidumbre por activo/día.

## 4. Modelo dimensional y OBT con Spark

BRONZE contiene STG_AI4I; SILVER agrupa limpieza, rechazados y reporte de calidad. GOLD utiliza FACT_READING, DIM_PRODUCT y DIM_SOURCE. source() declara RAW y ref() expresa las dependencias. El macro generate_schema_name publica exactamente en los esquemas requeridos, sin prefijos adicionales.

El grano de hechos es (source_sha256, udi); reading_key es MD5 de esa combinación. product_key identifica product_id y product_type; source_key identifica la versión SHA256 y su procedencia. No se inventa una dimensión calendario ni se supone que distintos UDI sean una serie de una misma máquina.

Los tests verifican not_null, unique, accepted_values, relationships, dominios físicos básicos, Gold no vacío y reconciliación Raw/Silver/Gold. El star schema sirve para análisis por tipo de producto/fuente y centralización de atributos. La alta cardinalidad de producto no demuestra seguimiento longitudinal de activos.

Spark exige claves únicas/no nulas y ausencia de huérfanos; compara conteo y unicidad antes/después de los joins. Añade delta térmico y potencia mecánica, además de BASELINE_ALERT y su versión para comparación de políticas. MACHINE_FAILURE es la etiqueta, no una feature. La OBT facilita futuras matrices de entrenamiento y evita joins repetidos.

Se escribe una tabla de construcción, se validan conteo y claves en Snowflake y luego se publica OBT.AI4I_OBT con CREATE OR REPLACE ... CLONE. El transporte usa el conector Python; los joins/features se ejecutan en Spark local[2]. fetch_pandas_all/toPandas limita el volumen al driver: una escala mayor necesita conector distribuido y particionado.

## 5. Regla, costos y umbral de decisión

Baseline candidato: UCI_PHYSICS_WEAR200_v1, no aprobado aún por un experto de planta. Alerta si se cumple: delta térmico <8,6 K y rpm <1380; potencia <3500 o >9000 W; desgaste*torque >11000/12000/13000 para L/M/H; o desgaste >=200 min. Las tres primeras condiciones se inspiran en los mecanismos publicados por UCI; la última es una heurística conservadora propuesta, no una reproducción exacta de su desgaste aleatorio. No usa etiquetas ni flags de falla como entradas.

En el CSV completo: TP=330, FP=678, FN=9, TN=8983; precisión 32,74%, recall 97,35% y alertas 10,08%. Es una evaluación descriptiva de reglas del generador, no evidencia de generalización. También se calculan referencias nunca/siempre alertar; el calendario fijo no es reconstruible. Logística se añadirá en modelado.

Todos los importes son supuestos USD pendientes de validación. Planta de referencia: 20 equipos, 2 turnos de 8 h, 5 días/semana, una revisión por equipo-día y capacidad de 5 inspecciones/día. Margen perdido: USD 300/h. Planificado: 800 directo +2 h =1400. Emergencia: 2200 directo +8 h =4600. Inspección: 50. Demora incremental por omisión: 4 h*300 +800 de daño secundario =2000.

Para RUL, sobreestimar vida podría elevar 1400 planificados a 4600 de emergencia (exceso 3200); subestimarla podría adelantar un mantenimiento innecesario de 1400. Una pieza de 500 con 25% de vida restante desperdicia 125, incluidos en ese costo, sin volver a sumarlos. Son ejemplos de la idea descartada: AI4I no demuestra prevención de emergencias.

En detección actual se usa C_TN=0, C_FP=C_TP=50 y C_FN=2000. El costo es 50*(TP+FP)+2000*FN: no se suma toda la reparación común ni el costo de emergencia otra vez. Una futura probabilidad calibrada p alerta si p>=t=50/2000=0,025 (2,5%). Ese valor sustituye 60-70%, no es una probabilidad que ya produzca PSet 2. La atención sigue sujeta a revisión humana y capacidad.

La sensibilidad varía inspección 25/50/100 y demora 1000/2000/4000: t varía 0,625%-10%. Por 1000 observaciones, la regla cuesta 6840 en el caso base, 10980 con costos 100/1000 y 6120 con 25/4000. Nunca alertar cuesta 67800 en base. Son valoraciones retrospectivas sintéticas, no ahorro anual ni causal. Los nueve casos y parámetros están versionados en negocio.json y business_assumptions.json.

Con margen/hora de 150/300/600, la demora pasa a 1400/2000/3200 y t a 3,57%/2,5%/1,56%. Suponiendo únicamente para dimensionar la mezcla sintética, 20 oportunidades/día darían 2,016 alertas; 60 darían 6,048, sobre la capacidad de 5. No son tasas reales ni se asume que cada turno cree eventos independientes.

## 6. Evidencia, aceptación y patrocinador

El pipeline original validó 8 modelos y 24 tests dbt; RAW, Gold y OBT tuvieron 10.000 filas únicas. Reejecución y backfills no duplicaron RAW. Las ejecuciones de la mejora, tests y reportes de baseline/costos están en docs/validacion.md y docs/evidencia. PSet 2 prepara datos y referencias: no hay todavía un modelo calibrado, ROI real ni autorización de implementación.

Para sustituir supuestos, solicitar 12 meses de CMMS/ERP: activo/familia, timestamps de falla/detección/reparación/reinicio, planificado/emergencia, horas/tarifas, repuestos, urgencias, scrap y margen/hora. Comparar trabajos de severidad/familia similar (objetivo 30 de cada tipo; si hay menos, declararlo), calcular mediana y P25/P75 y separar demora evitable de reparación común. Sin historial: cotizaciones fechadas y escenarios firmados por mantenimiento/finanzas. La guía DOE/FEMP orienta el procedimiento; no aporta los precios de esta planta.

Propuesta de aceptación del futuro modelo: reducción de costo variable >=10% frente a la mejor referencia factible, límite inferior IC95% de ahorro pareado >0, recall >=80%, precisión >=30% y <=5 revisiones/día. Umbral/calibración se eligen en validación, no en test. Además se exige beneficio neto positivo con volumen real, descontando presupuesto ilustrativo de 200/mes +1200 de puesta en marcha (3600 el primer año). No calcular ROI anual con filas de AI4I. Aprobar en sintético solo permite solicitar piloto; implementar exige piloto real y aceptación firmada.

Solicitud al patrocinador: autorizar 4 semanas en modo sombra para 20 equipos, sin paradas automáticas; entregar en 10 días hábiles el extracto anonimizado CMMS/ERP y costos; designar responsables de mantenimiento/finanzas para dos sesiones de 60 min que validen regla, costos, capacidad y presupuesto. Se solicita acceso y validación, no compra inmediata del modelo.

Batch es suficiente para la fuente estática y el alcance académico; el cron semanal no cubre un SLA de planta. Streaming solo sería justificable con telemetría continua, decisiones urgentes y event time/deduplicación/watermarking. No se implementa. Persisten límites de datos sintéticos, falta de timestamps, desbalance y 27 discrepancias conservadas. El documento ampliado negocio_y_decision.md traza cada comentario del PSet 1; las metas propuestas no se presentan como logros del modelo.

Fuentes: PSet1_pitch_Ron.pdf y CD_PSet_2 (1).pdf aportados; UCI AI4I, doi:10.24432/C5HS5C; DOE/FEMP, O&M Best Practices Guide 3.0. Enlaces y procedimiento completo en negocio_y_decision.md. El nombre final de entrega requiere los apellidos reales.
