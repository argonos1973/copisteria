import os
import re

FRONTEND_DIR = '/var/www/html/frontend'
MODALES_CSS = '<link rel="stylesheet" href="/static/css/modales.css?v=1763897790" />'
NOTIFICACIONES_CSS = '<link rel="stylesheet" href="/static/css/notificaciones.css?v=1763897790" />'

def patch_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Solo parchear si usa scripts_utils.js (indicador de que es una app SPA-like que usa overlay)
    # O si es una página de GESTION/CONSULTA que probablemente lo necesite.
    needs_patch = 'scripts_utils.js' in content or 'GESTION_' in filepath or 'CONSULTA_' in filepath
    
    if not needs_patch:
        print(f"Skipping {os.path.basename(filepath)} (no scripts_utils.js dependency)")
        return

    modified = False
    
    # Check modales.css
    if 'modales.css' not in content:
        print(f"Patching modales.css in {os.path.basename(filepath)}")
        # Insertar después de styles.css si existe
        if 'styles.css' in content:
            content = re.sub(r'(<link.*styles\.css.*?>)', r'\1\n  ' + MODALES_CSS, content)
        elif '</head>' in content:
            content = content.replace('</head>', '  ' + MODALES_CSS + '\n</head>')
        modified = True
    
    # Check notificaciones.css
    if 'notificaciones.css' not in content:
        print(f"Patching notificaciones.css in {os.path.basename(filepath)}")
        if 'modales.css' in content: # Si ya estaba o lo acabamos de poner
             # Insertar antes de modales si es posible, o después de styles
             # Simplemente insertamos después de styles si existe
             if 'styles.css' in content:
                 content = re.sub(r'(<link.*styles\.css.*?>)', r'\1\n  ' + NOTIFICACIONES_CSS, content)
             else:
                 content = content.replace('</head>', '  ' + NOTIFICACIONES_CSS + '\n</head>')
        elif 'styles.css' in content:
            content = re.sub(r'(<link.*styles\.css.*?>)', r'\1\n  ' + NOTIFICACIONES_CSS, content)
        elif '</head>' in content:
             content = content.replace('</head>', '  ' + NOTIFICACIONES_CSS + '\n</head>')
        modified = True

    if modified:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

for filename in os.listdir(FRONTEND_DIR):
    if filename.endswith('.html'):
        patch_file(os.path.join(FRONTEND_DIR, filename))
