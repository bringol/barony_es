import json
from pathlib import Path

def count_translation_progress(es_data, en_data, pl_data=None, current_path=""):
    """
    Recorre los JSONs y cuenta cuántos strings son traducibles.
    Además, guarda la ruta de las llaves que aún no fueron traducidas.
    """
    translatable = 0
    translated = 0
    missing_nodes = []

    if isinstance(en_data, dict) and isinstance(es_data, dict):
        for key in en_data:
            if key in es_data:
                pl_val = pl_data.get(key) if isinstance(pl_data, dict) else None
                new_path = f"{current_path}.{key}" if current_path else key
                
                t, tr, missing = count_translation_progress(es_data[key], en_data[key], pl_val, new_path)
                translatable += t
                translated += tr
                missing_nodes.extend(missing)
                
    elif isinstance(en_data, list) and isinstance(es_data, list):
        for i in range(min(len(en_data), len(es_data))):
            pl_val = pl_data[i] if isinstance(pl_data, list) and i < len(pl_data) else None
            new_path = f"{current_path}[{i}]"
            
            t, tr, missing = count_translation_progress(es_data[i], en_data[i], pl_val, new_path)
            translatable += t
            translated += tr
            missing_nodes.extend(missing)
            
    elif isinstance(en_data, str) and isinstance(es_data, str):
        if en_data.strip():
            is_translatable = True
            
            if isinstance(pl_data, str) and en_data == pl_data:
                is_translatable = False
                
            if is_translatable:
                translatable += 1
                if es_data != en_data:
                    translated += 1
                else:
                    missing_nodes.append((current_path, en_data))
                
    return translatable, translated, missing_nodes

def main():
    # Detecta dinámicamente la carpeta donde está guardado este script
    script_dir = Path(__file__).parent
    
    # Navega hacia la raíz del proyecto para buscar las carpetas de datos
    # Como el script está en 'tools', el padre (.parent) es la raíz 'barony_es'
    project_root = script_dir.parent
    
    es_dir = project_root / "v5.0.2" 
    en_dir = project_root / "1-ENG-VERSION" 
    pl_dir = project_root / "2-POLISH"
    
    # El archivo log se guardará en la misma carpeta que el script (tools/)
    log_file_path = script_dir / "pendientes_traduccion.log"
    
    total_translatable = 0
    total_translated = 0
    files_processed = 0
    
    file_reports = []
    all_missing_logs = {}

    for es_file in es_dir.rglob("*.json"):
        rel_path = es_file.relative_to(es_dir)
        en_file = en_dir / rel_path.with_name(f"{rel_path.stem}_en.json")
        pl_file = pl_dir / rel_path.with_name(f"{rel_path.stem}_pl.json")

        if en_file.exists():
            try:
                with open(es_file, 'r', encoding='utf-8') as f_es, \
                     open(en_file, 'r', encoding='utf-8') as f_en:
                    es_data = json.load(f_es)
                    en_data = json.load(f_en)
                
                pl_data = None
                if pl_file.exists():
                    with open(pl_file, 'r', encoding='utf-8') as f_pl:
                        pl_data = json.load(f_pl)
                
                t, tr, missing = count_translation_progress(es_data, en_data, pl_data)
                
                total_translatable += t
                total_translated += tr
                files_processed += 1
                
                pct = (tr / t * 100) if t > 0 else 0.0
                file_reports.append({
                    'path': str(rel_path),
                    't': t,
                    'tr': tr,
                    'pct': pct
                })
                
                if missing:
                    all_missing_logs[str(rel_path)] = missing
                    
            except Exception as e:
                print(f"Error procesando {es_file.name}: {e}")

    if total_translatable > 0:
        file_reports.sort(key=lambda x: x['path'])
        
        print("\n" + "="*75)
        print("📂 REPORTE POR ARCHIVO 📂".center(75))
        print("="*75)
        
        for rep in file_reports:
            if rep['t'] > 0:
                print(f"{rep['path']:<50} | {rep['tr']:>5}/{rep['t']:<5} ({rep['pct']:>6.2f}%)")
            else:
                print(f"{rep['path']:<50} | Sin textos traducibles")

        percentage = (total_translated / total_translatable) * 100
        print("\n" + "="*75)
        print("📊 REPORTE DE TRADUCCIÓN GLOBAL 📊".center(75))
        print("="*75)
        print(f"Archivos escaneados : {files_processed}")
        print(f"Nodos traducibles   : {total_translatable}")
        print(f"Nodos traducidos    : {total_translated}")
        print(f"Progreso global     : {percentage:.2f}%")
        print("="*75 + "\n")
        
        try:
            with open(log_file_path, "w", encoding="utf-8") as f_log:
                f_log.write("===========================================================================\n")
                f_log.write("LOG DE NODOS PENDIENTES DE TRADUCCIÓN\n")
                f_log.write("===========================================================================\n\n")
                
                for path in sorted(all_missing_logs.keys()):
                    f_log.write(f"📂 ARCHIVO: {path}\n")
                    f_log.write("-" * 75 + "\n")
                    for node_path, en_text in all_missing_logs[path]:
                        display_text = en_text.replace('\n', '\\n')
                        f_log.write(f"[{node_path}] -> {display_text}\n")
                    f_log.write("\n")
                    
            print(f"✅ Se ha generado un log detallado en: {log_file_path.absolute()}")
        except Exception as e:
            print(f"No se pudo crear el archivo de log: {e}")

    else:
        print("No se encontraron textos traducibles o archivos equivalentes.")

if __name__ == "__main__":
    main()
