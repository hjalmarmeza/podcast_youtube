#!/bin/bash
cd "$(dirname "$0")"

echo "================================================"
echo "   Sincronizador de Podcast MusiChris Studio"
echo "================================================"
echo "Sincronizando tus nuevos audios con la nube..."
echo ""

# Descargar cualquier cambio remoto (por si editaste el archivo yml en la web, etc)
git pull origin main

# Agregar todos los cambios y nuevos archivos
git add .

# Hacer commit con fecha
git commit -m "Nuevos audios agregados el $(date +'%Y-%m-%d %H:%M:%S')"

# Subir a GitHub
git push origin main

echo ""
echo "================================================"
echo "¡Sincronización Completada!"
echo "Tus nuevos audios ya están en la nube listos para el robot."
echo "Puedes cerrar esta ventana."
echo "================================================"
