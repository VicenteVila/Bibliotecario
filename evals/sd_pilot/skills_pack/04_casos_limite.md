Antes de dar por buena una solución, piensa en los bordes: cantidades negativas
y cero, valores en el borde (.005, >= vs >), entradas vacías, duplicados,
malformados/EOF, ciclos y orden de salida. Implementa el caso general Y los
bordes; si un borde no está en los tests públicos, sigue siendo parte del
contrato.
