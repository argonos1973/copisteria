import os
import tempfile
import logging
import subprocess

print(f"User: {os.getuid()}")
print(f"Group: {os.getgid()}")

# Test escritura /tmp
try:
    fd, path = tempfile.mkstemp()
    print(f"Escritura en /tmp OK: {path}")
    os.close(fd)
    os.remove(path)
except Exception as e:
    print(f"ERROR escribiendo en /tmp: {e}")

# Test escritura /var/www/html/certs
try:
    path = "/var/www/html/certs/test_write.txt"
    with open(path, "w") as f:
        f.write("test")
    print(f"Escritura en certs OK: {path}")
    os.remove(path)
except Exception as e:
    print(f"ERROR escribiendo en certs: {e}")
    
# Test escritura /var/www/html/certs/empresas
try:
    path = "/var/www/html/certs/empresas/test_write.txt"
    with open(path, "w") as f:
        f.write("test")
    print(f"Escritura en certs/empresas OK: {path}")
    os.remove(path)
except Exception as e:
    print(f"ERROR escribiendo en certs/empresas: {e}")

# Test openssl
try:
    res = subprocess.run(['openssl', 'version'], capture_output=True)
    print(f"OpenSSL OK: {res.stdout.decode()}")
except Exception as e:
    print(f"ERROR OpenSSL: {e}")
