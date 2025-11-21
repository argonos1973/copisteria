#!/usr/bin/env python3
"""
Script para detectar y reportar posibles credenciales hardcodeadas
"""
import os
import re

def check_credentials(filepath):
    """Revisa un archivo en busca de credenciales hardcodeadas"""
    patterns = [
        (r'password\s*=\s*["\'](?!.*\.env|.*environ|.*getenv|.*config|.*\{\}|.*%s)([^"\']+)["\']', 'password'),
        (r'api_key\s*=\s*["\'](?!.*\.env|.*environ|.*getenv)([^"\']+)["\']', 'api_key'),
        (r'secret\s*=\s*["\'](?!.*\.env|.*environ|.*getenv)([^"\']+)["\']', 'secret'),
        (r'token\s*=\s*["\'](?!.*\.env|.*environ|.*getenv)([^"\']+)["\']', 'token'),
        (r'AWS_[A-Z_]+\s*=\s*["\']([^"\']+)["\']', 'aws_credential'),
        (r'SMTP_PASSWORD\s*=\s*["\']([^"\']+)["\']', 'smtp_password'),
    ]
    
    findings = []
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        for line_num, line in enumerate(lines, 1):
            # Ignorar comentarios y líneas de ejemplo
            if line.strip().startswith('#') or 'example' in line.lower():
                continue
            
            for pattern, cred_type in patterns:
                matches = re.finditer(pattern, line, re.IGNORECASE)
                for match in matches:
                    # Ignorar valores placeholder comunes
                    value = match.group(1) if match.lastindex else match.group(0)
                    placeholders = [
                        'your-', 'tu-', 'xxx', 'changeme', 'password',
                        'secret', 'key', 'token', 'placeholder', 'example',
                        'test', 'demo', '12345', 'admin', 'default'
                    ]
                    
                    if not any(p in value.lower() for p in placeholders):
                        findings.append({
                            'file': filepath,
                            'line': line_num,
                            'type': cred_type,
                            'value': value[:20] + '...' if len(value) > 20 else value,
                            'context': line.strip()[:80]
                        })
    
    except Exception as e:
        print(f"Error procesando {filepath}: {e}")
    
    return findings

def main():
    """Buscar credenciales en todos los archivos Python"""
    print("🔍 Buscando posibles credenciales hardcodeadas...\n")
    
    all_findings = []
    files_checked = 0
    
    # Buscar en archivos Python
    for root, dirs, files in os.walk('.'):
        dirs[:] = [d for d in dirs if d not in ['venv', '.venv', '.git', '__pycache__', 'node_modules']]
        
        for file in files:
            if file.endswith(('.py', '.js', '.env.example')):
                filepath = os.path.join(root, file)
                files_checked += 1
                findings = check_credentials(filepath)
                all_findings.extend(findings)
    
    # Agrupar por tipo
    by_type = {}
    for finding in all_findings:
        cred_type = finding['type']
        if cred_type not in by_type:
            by_type[cred_type] = []
        by_type[cred_type].append(finding)
    
    # Generar reporte
    print("📊 REPORTE DE CREDENCIALES POTENCIALES\n")
    print("=" * 70)
    
    if not all_findings:
        print("✅ ¡Excelente! No se encontraron credenciales hardcodeadas obvias")
    else:
        for cred_type, findings in by_type.items():
            print(f"\n🔐 {cred_type.upper()} ({len(findings)} encontrados)")
            print("-" * 50)
            for finding in findings[:5]:  # Mostrar máximo 5 por tipo
                print(f"  📄 {finding['file']}:{finding['line']}")
                print(f"     Valor: {finding['value']}")
                print(f"     Contexto: {finding['context']}")
                print()
            
            if len(findings) > 5:
                print(f"  ... y {len(findings) - 5} más\n")
    
    print("=" * 70)
    print(f"\n📈 RESUMEN:")
    print(f"   Archivos revisados: {files_checked}")
    print(f"   Posibles credenciales: {len(all_findings)}")
    
    # Clasificación de riesgo
    risk_level = "BAJO"
    if len(all_findings) > 50:
        risk_level = "ALTO"
    elif len(all_findings) > 20:
        risk_level = "MEDIO"
    
    print(f"   Nivel de riesgo: {risk_level}")
    
    # Guardar reporte
    with open('credentials_report.txt', 'w') as f:
        f.write("REPORTE DE CREDENCIALES HARDCODEADAS\n")
        f.write("=" * 50 + "\n\n")
        for finding in all_findings:
            f.write(f"{finding['file']}:{finding['line']} - {finding['type']}\n")
            f.write(f"  {finding['context']}\n\n")
    
    print(f"\n📄 Reporte detallado guardado en: credentials_report.txt")
    
    # Sugerencias de corrección
    if all_findings:
        print("\n💡 RECOMENDACIONES:")
        print("   1. Mover credenciales a archivo .env")
        print("   2. Usar os.environ.get() para acceder")
        print("   3. Nunca commitear archivos .env a Git")
        print("   4. Usar gestores de secretos en producción")

if __name__ == "__main__":
    main()
