"""Ejercicio 1: resumen, distribucion y atipicos de viajes_taxi.csv.

Corre el script antes de tocar nada:

    python3 ejercicio1_explorar.py

Corre sin errores y sin los TODO resueltos. Los graficos quedan en
figuras/: abrelos despues de cada corrida.
"""

import os

import matplotlib.pyplot as plt
import pandas as pd

os.makedirs("figuras", exist_ok=True)
viajes = pd.read_csv("viajes_taxi.csv")

print("Paso 1: resumen")
print("Filas y columnas:", viajes.shape)
print("5 Filas")
print(viajes.head())
print("Muestra aleatoria")
print(viajes.sample())


print("Valores faltantes por columna:")
print(viajes.isna().sum())
# TODO 1: imprime la estadistica descriptiva de las columnas numericas,
# redondeada a 2 decimales.
print(viajes.describe().round())

#viajes['metodo_pago'](isna = False)

print()
print("Paso 2: distribucion de la tarifa")
plt.figure()
# TODO 2: histograma de la tarifa, con 50 barras.
plt.hist(viajes['tarifa'], bins=50)
plt.title("Tarifa de cada viaje")
plt.xlabel("tarifa")
plt.ylabel("cantidad de viajes")
plt.savefig("figuras/hist_tarifa.png")
plt.close()

plt.figure()
plt.boxplot(viajes["tarifa"])
plt.title("Tarifa, diagrama de caja")
plt.savefig("figuras/caja_tarifa.png")
plt.close()
print("Figuras guardadas en figuras/")

print()

#IQR = RANGO INTERCUARTIL
#IQR = Q3 - Q1
#IQR = 75% - 25%
#LS = Q3 +1.5 * IQR
#LI = Q1 - 1.5 * IQR

print("Paso 3: atipicos con la regla del IQR")
# TODO 3: calcula Q1, Q3, el IQR y el limite superior (Q3 + 1.5 * IQR)
# de la tarifa.

# REGLA DE LOS 3 SIGMA -> 99.7% DE LOS DATOS
#columna.std() desviacion standar
# LS = MEDIA + 3 * STD
# LI = MEDIA - 3 * STD
Q3 = viajes["tarifa"].quantile(0.75)
Q1 = viajes["tarifa"].quantile(0.25)
IQR = Q3 - Q1

limite_superior = Q3 + 1.5 * IQR
limite_inferior = Q1 - 1.5 * IQR

atipicos = viajes.query(f'tarifa > {limite_superior} or tarifa < {limite_inferior}')

print(f"Limite superior: {limite_superior:.2f}")
print(f"Limite inferior: {limite_inferior:.2f}")

print(f"Viajes atipocos: {len(atipicos)}")
print(atipicos["tarifa"].value_counts().head(3))

print()
print("Paso 4: atipico no es lo mismo que error")
# TODO 4: de los atipicos, cuenta los que tienen la tarifa de error de
# captura (999.99) y los que tienen una tarifa exacta de 70.00.
errores_de_captura = None
tarifa_exacta_70 = None
print(f"Error de captura (999.99): {errores_de_captura}")
print(f"Tarifa exacta de 70.00: {tarifa_exacta_70}")
print(f"Duraciones negativas: {(viajes['duracion_min'] < 0).sum()}")
