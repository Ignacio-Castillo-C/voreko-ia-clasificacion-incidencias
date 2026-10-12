# Cómo crear y publicar el repositorio en GitHub

> El repositorio **todavía no está publicado**. Estos pasos lo crean; después de hacerlo, verifica que la URL abre correctamente antes de citarla en la entrega.

## Opción A — Desde el navegador (como en el Tema 10)

1. Entra a <https://github.com> → **New repository**.
2. *Repository name:* `voreko-ia-clasificacion-incidencias`. Elige **Public** o **Private** (si es privado, agrega como colaborador a tu profesor).
3. **No** marques *Add a README*, *.gitignore* ni *license*: ya vienen en la carpeta.
4. **Create repository** → **uploading an existing file**.
5. Arrastra **el contenido** de la carpeta `voreko-ia-clasificacion-incidencias/` (no la carpeta misma), incluyendo `.gitignore`.
   *Nota:* en macOS y Linux los archivos que empiezan con punto están ocultos; usa `Cmd + Shift + .` en Finder para verlos.
6. Mensaje: `Versión 1.4: prototipo, dataset, pruebas y documentación` → **Commit changes**.
7. Revisa que se vean las carpetas `notebooks/`, `data/`, `src/`, `results/`, `docs/`, `tests/` y que el README se muestre con formato.

## Opción B — Con Git en terminal

```bash
cd voreko-ia-clasificacion-incidencias
git init -b main
git add .
git status                      # confirma que no aparece ningún token, .env ni archivo de pesos
git commit -m "Versión 1.4: prototipo, dataset, pruebas y documentación"
git remote add origin https://github.com/<tu-usuario>/voreko-ia-clasificacion-incidencias.git
git push -u origin main
```

Con GitHub CLI: `gh repo create voreko-ia-clasificacion-incidencias --private --source=. --push`

## Después de ejecutar el notebook en Colab

1. Descomprime `resultados_voreko_ia.zip` dentro de `results/`.
2. Sustituye `notebooks/VOREKO_IA_comparacion_modelos.ipynb` por la versión descargada **con salidas**.
3. Completa la sección *Resultados y conclusiones* del README y las tablas marcadas como *Pendiente* del documento Word con los valores de `results/`.
4. Registra la ejecución en `BITACORA_CAMBIOS.md` (versión 1.5: fecha, GPU, errores y correcciones).
5. `git add . && git commit -m "Resultados de la ejecución en Colab (GPU T4)" && git push`

> Si actualizas el notebook con salidas, la prueba `test_sin_salidas_inventadas` fallará a propósito; en ese momento cámbiala por una que verifique que las salidas existen y que `results/revision_tecnica.csv` tiene 18 comprobaciones "OK".

## Comprobación de seguridad antes de publicar

```bash
grep -rniE "hf_[a-z0-9]{20,}" . --exclude-dir=.git || echo "Sin tokens de Hugging Face"
```
