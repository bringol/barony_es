# Barony Spanish Localization

## 1. OBJETIVO

Este repositorio contiene la localización de **Barony** del inglés al español neutro.

Al trabajar sobre archivos de localización, el objetivo es producir traducciones:

- Fieles al significado original.
- Naturales en español neutro latinoamericano.
- Concisas y apropiadas para una interfaz de videojuego.
- Consistentes con el resto de la traducción.
- Compatibles con la estructura y funcionamiento interno de Barony.

Evita regionalismos cuando exista una alternativa ampliamente comprensible.

No utilices `vosotros`, `vuestro` ni conjugaciones asociadas.

No modifiques código, IDs, recursos internos ni estructuras del juego salvo que el usuario lo solicite explícitamente.

---

# 2. PRIORIDAD DE REGLAS

Si dos requisitos entran en conflicto, aplica este orden:

1. Preservar el funcionamiento del juego y producir JSON válido.
2. Preservar IDs, claves internas, recursos, variables y estructura.
3. Preservar placeholders, símbolos y secuencias especiales.
4. Aplicar la terminología establecida en el glosario.
5. Preservar correctamente el significado del original.
6. Mantener consistencia con traducciones españolas existentes.
7. Utilizar español neutro, natural y gramaticalmente correcto.
8. Respetar las restricciones visuales de la interfaz.
9. Mantener casing y estilo compatibles con el original.

Nunca sacrifiques la integridad técnica del archivo para mejorar el estilo de una traducción.

---

# 3. FUENTES DE CONTEXTO

Cuando el usuario solicite traducir o revisar un archivo dentro de `v5.0.2/`, reúne primero el contexto necesario.

## 3.1. Original inglés

Ubicación:

`1-ENG-VERSION/`

Normalmente contiene el mismo archivo con el sufijo `_en`.

Ejemplo:

Destino:

`v5.0.2/items/item_tooltips.json`

Original:

`1-ENG-VERSION/items/item_tooltips_en.json`

El archivo inglés es la fuente principal para determinar el significado del texto.

---

## 3.2. Referencia polaca

Ubicación:

`2-POLISH/`

Normalmente contiene el mismo archivo con el sufijo `_pl`.

Ejemplo:

`2-POLISH/items/item_tooltips_pl.json`

La versión polaca funciona como referencia estructural adicional para distinguir:

- Texto visible.
- IDs internos.
- Recursos.
- Etiquetas técnicas.
- Elementos que los archivos de localización no deben modificar.

NO utilices la traducción polaca como fuente terminológica para el español.

---

## 3.3. Glosario

Ubicación:

`tools/glosario_completo.txt`

Consulta siempre este archivo antes de crear traducciones.

El glosario es la principal fuente terminológica del proyecto.

---

## 3.4. Traducciones españolas existentes

Cuando un término o construcción no esté resuelto por el glosario, busca cómo aparece en otros archivos de `v5.0.2/`.

Las traducciones existentes pueden aportar contexto sobre:

- Nombres de objetos.
- Habilidades.
- Monstruos.
- Clases.
- Estados.
- Mecánicas.
- Terminología de interfaz.

No introduzcas variantes innecesarias para un término que ya tenga una traducción establecida.

---

# 4. INVESTIGACIÓN DE CONTEXTO

No traduzcas entradas ambiguas de forma aislada.

Cuando el significado de un string no sea evidente, investiga de forma autónoma antes de decidir.

Puedes consultar:

1. El nodo equivalente inglés.
2. El nodo equivalente polaco.
3. Las entradas inmediatamente anteriores y posteriores.
4. Otras apariciones del mismo ID.
5. Otras apariciones del texto inglés.
6. Traducciones españolas existentes.
7. El glosario.
8. Archivos JSON relacionados.
9. Código fuente o referencias del repositorio que utilicen ese ID, cuando sea necesario para comprender su función.

Utiliza búsquedas en el repositorio para determinar qué representa una entrada antes de realizar una traducción dudosa.

No preguntes al usuario por contexto que pueda deducirse razonablemente investigando el repositorio.

---

# 5. DISTINGUIR TEXTO DE CÓDIGO

Barony contiene numerosos valores que parecen palabras normales pero funcionan como:

- IDs.
- Nombres de recursos.
- Texturas.
- Rutas.
- Nombres de archivos.
- Etiquetas técnicas.
- Variables.
- Claves internas.

No determines que algo es traducible únicamente porque está escrito en inglés.

---

## 5.1. Comparación inglés-polaco

La comparación con el archivo polaco es una señal útil, no una regla absoluta.

### Si inglés y polaco son diferentes

Es evidencia fuerte de que probablemente se trata de texto visible.

Tradúcelo salvo que la estructura o el uso en el código demuestre que es un identificador.

### Si inglés y polaco son idénticos

NO asumas automáticamente que es código.

Puede tratarse de:

- Un ID.
- Un recurso interno.
- Un nombre propio.
- Una palabra internacional.
- Texto que el equipo polaco decidió no traducir.
- Texto todavía sin localizar.

Analiza el contexto antes de decidir.

---

## 5.2. Valores con apariencia técnica

Si inglés y polaco son idénticos Y el contenido tiene claramente apariencia de:

- ID interno.
- Ruta.
- Archivo.
- Textura.
- Recurso.
- Etiqueta RGB.
- Nombre técnico.
- Variable.
- Código.

conserva el valor exactamente.

---

## 5.3. Ambigüedad persistente

Si después de investigar el repositorio no es posible determinar con seguridad si una entrada debe traducirse:

- Conserva el valor original.
- No inventes.
- Indica al usuario cuál fue la entrada ambigua al finalizar.

---

# 6. REGLAS SEGÚN EL TIPO DE ARCHIVO

La función de una llave o valor depende del tipo de archivo.

No asumas que todas las estructuras JSON siguen el mismo modelo.

---

## 6.1. `contents_*.json`

Ejemplo:

`contents_items.json`

En estos archivos, normalmente:

- La LLAVE contiene texto visible.
- El VALOR contiene el ID interno.

Por lo tanto, traduce la llave y conserva el valor.

Ejemplo:

```json
{
    "LEATHER ARMOR": "leather armor"
}
```

debe convertirse en:

```json
{
    "ARMADURA DE CUERO": "leather armor"
}
```

---

## 6.2. `status_effects.json`, `item_tooltips.json`, `lang_codex.json`

Normalmente:

- La LLAVE es un ID interno.
- El VALOR contiene texto visible.
- El valor puede ser un string o un array de strings.

Conserva las llaves internas.

Traduce solamente el contenido visible.

---

## 6.3. Estructuras desconocidas

Si aparece un archivo cuya estructura no está documentada aquí:

1. Inspecciona el archivo inglés.
2. Compáralo con el polaco.
3. Examina las entradas españolas existentes.
4. Busca referencias de las claves en el repositorio si es necesario.
5. Determina qué partes son localizables antes de modificarlo.

La estructura real tiene prioridad sobre las suposiciones de este documento.

---

# 7. GLOSARIO

`tools/glosario_completo.txt` tiene prioridad terminológica.

Si un término inglés figura en el glosario, utiliza la traducción española establecida.

No la sustituyas por:

- Sinónimos.
- Traducciones más literales.
- Traducciones provenientes de otros videojuegos.
- Preferencias personales.
- Variantes regionales.

Adapta únicamente el casing cuando el contexto lo requiera.

Ejemplo:

Glosario:

`Armor Class = Clase de Armadura`

Original:

`ARMOR CLASS`

Resultado:

`CLASE DE ARMADURA`

Si una entrada del glosario parece incorrecta para un contexto concreto, no la reemplaces silenciosamente.

Utilízala salvo que hacerlo produzca un error evidente y señala el conflicto al usuario.

---

# 8. CONSISTENCIA TERMINOLÓGICA

Antes de crear una traducción nueva para un término recurrente:

1. Consulta el glosario.
2. Busca el término inglés en `v5.0.2/`.
3. Busca traducciones relacionadas.
4. Determina si ya existe una convención establecida.

La consistencia tiene prioridad sobre la variedad estilística.

No utilices varios términos españoles diferentes para una misma mecánica únicamente para evitar repeticiones.

---

# 9. ARRAYS

Los arrays de strings pueden corresponder directamente a líneas individuales de la interfaz.

Su estructura es intocable.

Nunca:

- Fusiones elementos.
- Dividas elementos.
- Agregues elementos.
- Elimines elementos.
- Reordenes elementos.
- Elimines elementos vacíos `""`.

Cada elemento debe conservar exactamente el mismo índice que en el original.

Ejemplo:

```json
[
    "Observe the enemy",
    "attack pace through",
    "the door on your right.",
    "",
    "Proceed through the",
    "door on your left",
    "when ready."
]
```

La traducción debe continuar teniendo exactamente **7 elementos**.

Puedes redistribuir gramaticalmente una oración entre esos elementos si es necesario, pero no alterar la cantidad de líneas.

Evalúa el texto completo del array como una sola unidad lingüística antes de traducir cada línea.

---

# 10. PLACEHOLDERS Y SÍMBOLOS DEL MOTOR

Conserva exactamente todos los placeholders y secuencias especiales.

Entre ellos:

`%s`

`%d`

`%+d%%`

`\n`

`$`

`^`

`*1`

`*2`

`*3`

y cualquier secuencia equivalente encontrada en los archivos.

Nunca:

- Traduzcas estos elementos.
- Los elimines.
- Los dupliques.
- Modifiques sus caracteres.
- Introduzcas espacios dentro de ellos.

El número de ocurrencias debe permanecer intacto.

Ejemplo:

Si el original contiene dos `%s`, la traducción debe contener exactamente dos `%s`.

Puedes cambiar la posición de un placeholder únicamente cuando sea necesario para obtener una oración española correcta Y sea seguro hacerlo según el funcionamiento de esa entrada.

---

# 11. VARIABLES DINÁMICAS Y GÉNERO GRAMATICAL

No asumas el género gramatical del contenido insertado mediante variables como `%s`.

Evita estructuras donde artículos, adjetivos o participios deban concordar con una variable cuyo valor sea desconocido.

Ejemplo:

Evitar:

`Hay un %s aquí.`

si `%s` puede representar sustantivos de distinto género.

Preferir:

`Aquí hay %s.`

Busca reformulaciones naturales que eviten concordancias inseguras.

---

# 12. LENGUAJE NEUTRO RESPECTO DEL JUGADOR

El género del personaje jugador puede ser desconocido.

Evita construcciones que obliguen a utilizar masculino o femenino cuando se refieran a quien juega.

Evita, cuando sea posible:

- `listo/lista`
- `preparado/preparada`
- `cansado/cansada`
- `descansado/descansada`
- `bienvenido/bienvenida`

No utilices:

- `@`
- `x`
- `e`

como sustitutos artificiales de género.

Reformula naturalmente.

Ejemplo:

Original:

`You feel rested.`

Evitar:

`Te sientes descansado.`

Preferir:

`Sientes que has recuperado fuerzas.`

Utiliza verbos, sustantivos y construcciones impersonales cuando permitan conservar el significado sin marcar género.

---

# 13. ESPAÑOL NEUTRO

Utiliza español neutro latinoamericano comprensible internacionalmente.

Evita expresiones marcadamente regionales cuando exista una alternativa clara y natural.

No utilices:

- `vosotros`
- `vuestro`
- conjugaciones correspondientes a `vosotros`

Para instrucciones directas utiliza normalmente el imperativo de `tú`.

Ejemplos:

`Press` → `Presiona`

`Hold` → `Mantén`

`Look` → `Mira`

`Equip` → `Equipa`

No traduzcas literalmente una estructura inglesa si resulta antinatural en español.

Traduce su función y significado.

---

# 14. ECONOMÍA DEL LENGUAJE

La interfaz de Barony puede imponer restricciones visuales.

El español suele ocupar más espacio que el inglés.

Utiliza la longitud del original como referencia aproximada de espacio disponible, no como un límite matemático obligatorio.

Prioriza:

1. Que el texto quepa en la interfaz.
2. Que conserve el significado.
3. Que respete el glosario.
4. Que resulte natural.
5. Que sea breve.

Cuando sea necesario:

- Elimina pronombres redundantes.
- Evita perífrasis innecesarias.
- Utiliza verbos directos.
- Prefiere sinónimos más breves.
- Evita repetir información evidente por contexto.

Ejemplo:

Preferir:

`Mantén$ para bloquear.`

frente a:

`Mantén presionado$ para bloquear.`

cuando `$` ya representa visualmente un botón.

No acortes una frase hasta volverla ambigua o incorrecta.

---

# 15. CASING

Respeta el casing funcional del texto original.

Ejemplo:

`Armor Class`

→

`Clase de Armadura`

`ARMOR CLASS`

→

`CLASE DE ARMADURA`

`armor class`

→

`clase de armadura`

---

# 16. SIGNIFICADO ANTES QUE LITERALIDAD

Traduce conceptos, no palabras aisladas.

Ten en cuenta:

- La función del objeto.
- La mecánica asociada.
- El contexto de fantasía.
- El tono.
- La interfaz donde aparece.
- Otras apariciones del término.

Una misma palabra inglesa puede requerir traducciones diferentes dependiendo de su función.

Antes de traducir un término ambiguo, busca cómo se utiliza dentro del juego.

---

# 17. ERRORES DEL ORIGINAL

El texto inglés puede contener:

- Typos.
- Errores gramaticales.
- Frases incompletas.
- Terminología inconsistente.
- Texto obsoleto.
- Errores evidentes.

Si la intención correcta es inequívoca, traduce la intención y no el error.

No reproduzcas automáticamente errores accidentales del inglés.

Sin embargo, si existen varias interpretaciones razonables:

- No inventes.
- Investiga el contexto.
- Si sigue siendo ambiguo, utiliza la interpretación más conservadora y señálalo al usuario.

Nunca corrijas silenciosamente IDs, variables o código aunque parezcan contener errores.

---

# 18. PRESERVACIÓN DEL ARCHIVO

Evita cambios ajenos a la traducción solicitada.

No:

- Reformatees todo el JSON.
- Cambies la indentación global.
- Reordenes claves.
- Normalices innecesariamente archivos.
- Modifiques código relacionado.
- Renombres archivos.
- Modifiques strings fuera del alcance solicitado.

Mantén el diff lo más pequeño posible.

Una tarea de localización debe producir principalmente cambios en texto visible.

---

# 19. VALIDACIÓN OBLIGATORIA

Después de modificar un archivo, valida el resultado antes de finalizar.

Comprueba:

1. Que el JSON sea sintácticamente válido.
2. Que la estructura esperada no haya cambiado.
3. Que no falten claves.
4. Que no existan claves adicionales introducidas accidentalmente.
5. Que los arrays mantengan exactamente la misma cantidad de elementos (Ejemplo: si el json tenía 100 líneas de código, el archivo traducido resultante también tendrá 100 líneas de código).
6. Que el orden de los arrays permanezca intacto.
7. Que todos los placeholders originales continúen presentes.
8. Que no hayan aparecido placeholders nuevos accidentalmente.
9. Que `$`, `^`, `*1`, `*2`, `*3`, `\n` y secuencias equivalentes se hayan preservado.
10. Que IDs y recursos internos no hayan sido traducidos.
11. Que las traducciones respeten el glosario.
12. Que no queden textos visibles en inglés por accidente.
13. Que el archivo modificado contenga únicamente los cambios necesarios.

Utiliza herramientas automáticas siempre que sea razonable.

Por ejemplo, puedes utilizar:

- Un parser JSON.
- Scripts.
- `git diff`.
- Búsquedas en el repositorio.
- Comparaciones programáticas entre inglés y español.

Si existe en el repositorio un script específico de validación, utilízalo.

Por ejemplo, si en el futuro existe:

`tools/validate_translation.py`

ejecútalo según las instrucciones del propio script.

NO asumas que dicho script existe y NO lo crees salvo que el usuario lo solicite.

---

# 20. REVISIÓN DEL DIFF

Antes de terminar, inspecciona el diff producido.

Comprueba especialmente que:

- Solo se hayan modificado strings que debían traducirse.
- No hayan cambiado IDs.
- No haya reformateo masivo.
- No se hayan perdido caracteres especiales.
- No se hayan modificado accidentalmente líneas vecinas.
- No existan traducciones inconsistentes evidentes.

Si detectas un cambio accidental, corrígelo antes de finalizar.

---

# 21. FLUJO DE TRABAJO

Cuando el usuario solicite traducir un archivo:

1. Identifica el archivo destino.
2. Localiza el original inglés.
3. Localiza la referencia polaca.
4. Consulta el glosario.
5. Examina traducciones españolas relacionadas.
6. Analiza la estructura del archivo.
7. Identifica qué contenido es visible y qué contenido es interno.
8. Investiga cualquier término ambiguo.
9. Traduce el texto visible.
10. Conserva IDs, estructura, placeholders y secuencias especiales.
11. Guarda el archivo.
12. Valida el JSON.
13. Compara estructuralmente con el original cuando corresponda.
14. Revisa placeholders y símbolos.
15. Revisa terminología.
16. Inspecciona el `git diff`.
17. Corrige cualquier problema detectado.
18. Informa el resultado al usuario.

No solicites confirmación para decisiones que puedan resolverse razonablemente mediante el repositorio, el glosario y estas instrucciones.

---

# 22. GUARDADO

Por defecto, sobrescribe directamente el archivo `.json` de destino dentro de `v5.0.2/`.

No crees automáticamente:

- `_translated`
- `_new`
- `_draft`
- copias de respaldo
- archivos temporales permanentes

salvo que el usuario lo solicite.

Si el usuario pide explícitamente:

- un borrador;
- una comparación;
- una revisión;
- una vista previa;

no sobrescribas el archivo original hasta que la tarea lo requiera.

---

# 23. NO EXPANDIR EL ALCANCE

No aproveches una tarea de traducción para modificar otras partes del repositorio.

Si durante el trabajo descubres:

- Traducciones antiguas posiblemente incorrectas.
- Inconsistencias fuera del archivo solicitado.
- Errores de código.
- Entradas dudosas del glosario.

no las modifiques salvo que sean necesarias para completar correctamente la tarea actual.

Debes señalarlas al usuario al finalizar.

---

# 24. RESULTADO FINAL

Al terminar:

- Guarda el archivo solicitado.
- Ejecuta las validaciones necesarias.
- Inspecciona el diff.
- No muestres el archivo completo salvo que el usuario lo solicite.

Informa brevemente:

- Qué archivo fue modificado.
- Si las validaciones fueron satisfactorias.
- Cualquier entrada que requiera revisión humana.

Si no existen problemas, basta con una confirmación breve.

No presentes decisiones internas rutinarias ni enumeres cada cambio de traducción salvo que el usuario lo solicite.
