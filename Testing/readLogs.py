archivo = "log_operacion.csv" 

try:
    with open(archivo, "r") as f:
        print(f"Contenido f2 de: {archivo}\n")
        
        for linea in f:
            if linea:
                columnas = [col for col in linea.split(',')]
                print(" | ".join(columnas))   # Separa las columnas con " | "
                
except OSError:
    print(f"Error: No se encontró el archivo '{archivo}'") 