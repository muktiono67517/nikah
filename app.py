from flask import Flask, render_template, session, request, redirect, url_for,jsonify
import mysql.connector
from datetime import datetime
from config import MYSQL_CONFIG
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)
app.secret_key = 'Ini-Rahasia-Dan-Wajib-Tidak-Dibocorkan'


# ==================== ADMIN PANEL ====================

ADMIN_TOKEN = "C9F2A7D0E4B16A83"

@app.route('/admin/<token>')
def admin_dashboard(token):
    # Validasi token
    if token != ADMIN_TOKEN:
        return "Token salah", 403

    conn = mysql.connector.connect(**MYSQL_CONFIG)
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM presensi ORDER BY created_at DESC")
    data = cursor.fetchall()

    cursor.execute("SELECT COUNT(*) AS total FROM presensi")
    total = cursor.fetchone()['total']

    cursor.execute("SELECT COUNT(DISTINCT ip_address) AS unik FROM presensi")
    unik_ip = cursor.fetchone()['unik']

    cursor.execute("SELECT MAX(created_at) AS terakhir FROM presensi")
    terakhir = cursor.fetchone()['terakhir']

    cursor.close()
    conn.close()

    return render_template(
        'admin_dashboard.html',
        data=data,
        total=total,
        unik_ip=unik_ip,
        terakhir=terakhir
    )



UPLOAD_FOLDER = 'static/gallery'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# otomatis membuat folder jika belum ada
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS



@app.route('/admin/<token>/uploadfoto', methods=['GET', 'POST'])
def admin_uploadfoto(token):
    # Validasi token admin
    if token != ADMIN_TOKEN:
        return "Token salah", 403

    message = ''

    if request.method == 'POST':
        if 'file' not in request.files:
            message = "Tidak ada file yang dipilih."
            return render_template('uploadfoto.html', message=message)

        file = request.files['file']

        if file.filename == '':
            message = "Nama file kosong."
            return render_template('uploadfoto.html', message=message)

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            message = f"Foto '{filename}' berhasil di-upload 🎉"
        else:
            message = "Format file tidak didukung. Gunakan JPG / PNG / WEBP."

    return render_template('uploadfoto.html', message=message,token=token)


# ==========================
#  FUNGSI BANTU: AMBIL FOTO
# ==========================
def ambil_foto(folder):
    hasil = []
    if not os.path.exists(folder):
        return hasil

    for file in os.listdir(folder):
        if file.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
            hasil.append(file)

    return hasil


# ==========================
#  API GABUNGAN FOTO
# ==========================
@app.route('/api/foto')
def api_foto():
    galeri = ambil_foto('static/gallery')
    undangan = ambil_foto('static/undangan')

    return jsonify({
        "galeri": galeri,
        "undangan": undangan
    })


# ==================== ADMIN PANEL CLOSE ====================


# ==================== HALAMAN LOGIN ====================

@app.route('/')
def index():
    return redirect(url_for('wedding_feed'))




# ==========================
# FUNGSI INI AKTIF
@app.route('/presensi', methods=['POST'])
def presensi():
    message = ''
    message_type = ''

    nama = request.form.get('nama', '').strip()
    asal = request.form.get('asal', '').strip()
    ucapan = request.form.get('ucapan', '').strip()
    ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)

    # Validasi backend (pengaman tambahan)
    if not nama:
        message = "Nama tamu belum diisi."
        message_type = 'error'
    elif not asal:
        message = "Alamat belum diisi."
        message_type = 'error'
    else:
        try:
            conn = mysql.connector.connect(**MYSQL_CONFIG)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO presensi (nama, asal, ucapan, ip_address, created_at)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                nama,
                asal,
                ucapan if ucapan else None,
                ip_address,
                datetime.now()
            ))

            conn.commit()
            cursor.close()
            conn.close()

            message = "Presensi berhasil. Terima kasih sudah mengisi 🙏"
            message_type = 'success'

        except Exception as e:
            message = f"Kesalahan sistem: {e}"
            message_type = 'error'

    return render_template(
        'presensi.html',
        message=message,
        message_type=message_type
    )
# ==========================
# FUNGSI INI AKTIF





# ==========================
#  HALAMAN UTAMA FOTO (UNDANGAN + GALERI)
# ==========================
@app.route('/undangan')
def home():
    # tidak perlu kirim foto_list,
    # karena semua di-load via fetch() dari JS
    return render_template('home.html')





@app.route('/kirim-ucapan', methods=['POST'])
def kirim_ucapan():
    if 'username' not in session:
        return render_template('ucapan_partial.html',
                               message="Anda belum login.",
                               message_type="error")

    username = session['username']
    ucapan = request.form.get('ucapan', '').strip()

    if len(ucapan) < 3:
        return render_template('ucapan_partial.html',
                               message="Ucapan terlalu singkat.",
                               message_type="warning")

    conn = mysql.connector.connect(**MYSQL_CONFIG)
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM ucapan WHERE username=%s", (username,))
    sudah = cursor.fetchone()

    if sudah:
        return render_template('ucapan_partial.html',
                               message="Anda sudah mengirim ucapan sebelumnya.",
                               message_type="warning")

    cursor.execute("INSERT INTO ucapan (username, isi) VALUES (%s, %s)", (username, ucapan))
    conn.commit()

    cursor.close()
    conn.close()

    return render_template('ucapan_partial.html',
                           message="Ucapan Anda berhasil dikirim.",
                           message_type="success")





# ==================== WEDDING FEED ====================

@app.route('/wedding-feed')
def wedding_feed():
    return render_template('base.html')

# Lokasi
@app.route('/lokasi')
def lokasi():
    map_url = "https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3952.122657234385!2d110.128!3d-7.8405!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x2e7b9c3c59f8f2e3%3A0xfac1d0376a201c83!2sGunung%20Pentul%2C%20Sidoharjo%2C%20Samigaluh%2C%20Kabupaten%20Kulon%20Progo%2C%20Daerah%20Istimewa%20Yogyakarta!5e0!3m2!1sid!2sid!4v1700000000000"
    external_map = "https://maps.app.goo.gl/d8Rqek7zsiqxUvCKA"
    return render_template('lokasi.html', map_url=map_url, external_map=external_map)




# ==================== LOGOUT ====================

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# ==================== RUN APP ====================

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

