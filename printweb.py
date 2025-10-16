import os
import subprocess

from flask import Flask, render_template_string, request
from werkzeug.utils import secure_filename
from logger_config import get_logger

# Inicializar logger
logger = get_logger(__name__)

UPLOAD_FOLDER = "/tmp/impresiones"
ALLOWED_EXTENSIONS = {"pdf"}
MAX_FILES = 10  # Límite máximo de archivos

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def get_printers():
    result = subprocess.run(["lpstat", "-v"], capture_output=True, text=True)
    printers = []
    logger.info("--- DEBUG: salida de lpstat -v ---")
    logger.info(f"result.stdout)
    for line in result.stdout.splitlines():
        if "para" in line or "device for" in line:
            parts = line.split()
            if len(parts) >= 3:
                printer_name = parts[2].rstrip(":")
                printers.append(printer_name)
    logger.info("--- DEBUG: impresoras detectadas ---")
    logger.info(f"{{printers}}")
    return printers

@app.route("/" methods=["GET", "POST"]")
def upload_file():
    printers = get_printers()
    if not printers:
        return "No se han detectado impresoras configuradas en CUPS. Salida debug:<br><pre>" + subprocess.run(["lpstat", "-v"], capture_output=True, text=True).stdout + "</pre>"

    if request.method == "POST":
        files = request.files.getlist("file")
        if len(files) > MAX_FILES:
            return f"Demasiados archivos seleccionados. El máximo permitido es {MAX_FILES}."
        selected_printer = request.form.get("printer")
        duplex_option = request.form.get("duplex_option")
        color_option = request.form.get("color_option")
        messages = []
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                file.save(filepath)
                cmd = ["lp", "-d", selected_printer]
                if duplex_option == "long":
                    cmd += ["-o", "sides=two-sided-long-edge"]
                elif duplex_option == "short":
                    cmd += ["-o", "sides=two-sided-short-edge"]
                if color_option == "bw":
                    cmd += ["-o", "ColorModel=Gray"]
                elif color_option == "color":
                    cmd += ["-o", "ColorModel=Color"]
                cmd.append(filepath)
                subprocess.run(cmd)
                messages.append(f"'{filename}' enviado a imprimir.")
        return "<br>".join(messages)

    return render_template_string('''
    <!doctype html>
    <title>Impresión PDF</title>
    <h1>Sube uno o más PDFs para imprimir (máx. {{ max_files }})</h1>
    <form method=post enctype=multipart/form-data id="upload-form">
      <label for="printer">Selecciona impresora:</label>
      <select name="printer">
        {% for printer in printers %}
          <option value="{{ printer }}">{{ printer }}</option>
        {% endfor %}
      </select><br><br>

      <label>Tipo de doble cara:</label><br>
      <input type="radio" name="duplex_option" value="long"> Doble cara (borde largo)<br>
      <input type="radio" name="duplex_option" value="short"> Doble cara (borde corto)<br>
      <input type="radio" name="duplex_option" value="none" checked> Simple cara<br><br>

      <label>Color:</label><br>
      <input type="radio" name="color_option" value="bw" checked> Blanco y negro<br>
      <input type="radio" name="color_option" value="color"> Color<br><br>

      <div id="drop-area" style="border: 2px dashed #ccc; padding: 20px; text-align: center;">
        Arrastra aquí tus archivos PDF o haz clic para seleccionar
        <input type="file" name="file" id="file-input" multiple accept="application/pdf" style="display: none;">
      </div>
      <ul id="file-list"></ul>
      <p id="warning-message" style="color: red;"></p>
      <br>
      <input type=submit value=Imprimir id="submit-button">
    </form>

    <script>
    const dropArea = document.getElementById('drop-area');
    const fileInput = document.getElementById('file-input');
    const fileList = document.getElementById('file-list');
    const warningMessage = document.getElementById('warning-message');
    const submitButton = document.getElementById('submit-button');
    const MAX_FILES = {{ max_files }};

    dropArea.addEventListener('click', () => fileInput.click());

    dropArea.addEventListener('dragover', e => {
      e.preventDefault();
      dropArea.style.backgroundColor = '#f0f0f0';
    });

    dropArea.addEventListener('dragleave', () => {
      dropArea.style.backgroundColor = '';
    });

    dropArea.addEventListener('drop', e => {
      e.preventDefault();
      dropArea.style.backgroundColor = '';

      const dt = new DataTransfer();
      let rejectedFiles = [];
      let validFiles = [];

      for (let i = 0; i < fileInput.files.length; i++) {
        validFiles.push(fileInput.files[i]);
      }
      for (let i = 0; i < e.dataTransfer.files.length; i++) {
        const file = e.dataTransfer.files[i];
        if (file.type === "application/pdf") {
          validFiles.push(file);
        } else {
          rejectedFiles.push(file.name);
        }
      }

      if (validFiles.length > MAX_FILES) {
        warningMessage.textContent = `Has seleccionado ${validFiles.length} archivos. El máximo permitido es ${MAX_FILES}.`;
        submitButton.disabled = true;
        return;
      }

      validFiles.forEach(f => dt.items.add(f));
      fileInput.files = dt.files;
      updateFileList();

      if (rejectedFiles.length > 0) {
        warningMessage.textContent = "Archivos ignorados (no son PDF): " + rejectedFiles.join(", ");
        submitButton.disabled = true;
      } else {
        warningMessage.textContent = "";
        submitButton.disabled = false;
      }
    });

    fileInput.addEventListener('change', () => {
      updateFileList();
      warningMessage.textContent = "";
      if (fileInput.files.length > MAX_FILES) {
        warningMessage.textContent = `Has seleccionado ${fileInput.files.length} archivos. El máximo permitido es ${MAX_FILES}.`;
        submitButton.disabled = true;
      } else {
        submitButton.disabled = false;
      }
    });

    function updateFileList() {
      fileList.innerHTML = '';
      for (let i = 0; i < fileInput.files.length; i++) {
        const li = document.createElement('li');
        li.textContent = fileInput.files[i].name;
        fileList.appendChild(li);
      }
    }
    </script>
    ''', printers=printers, max_files=MAX_FILES)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
