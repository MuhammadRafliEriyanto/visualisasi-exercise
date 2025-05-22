from flask import Flask
from flask_apscheduler import APScheduler
import requests
from pymongo import MongoClient, errors
from datetime import datetime, timedelta

app = Flask(__name__)

class Config:
    SCHEDULER_API_ENABLED = True

app.config.from_object(Config())
scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()

def sync_exercise_data():
    try:
        print("\n🔄 Mulai sinkronisasi data latihan...")
        print(f"⏰ Waktu: {datetime.now()}")

        # 🔧 Ubah koneksi database
        client = MongoClient("mongodb://localhost:27017/")
        db = client['capstone']  # Ganti dengan nama database baru
        collection = db['visualisasi2']  # Nama collection tanpa spasi

        # Buat index unik berdasarkan 'id'
        try:
            collection.create_index('id', unique=True)
        except errors.OperationFailure as e:
            print(f"⚠ Gagal membuat index (mungkin sudah ada): {e}")

        # Ambil kategori
        categories = requests.get('https://wger.de/api/v2/exercisecategory/').json()['results']
        category_dict = {cat['id']: cat['name'] for cat in categories}

        # Ambil peralatan
        equipments = requests.get('https://wger.de/api/v2/equipment/').json()['results']
        equipment_dict = {eq['id']: eq['name'] for eq in equipments}

        # Ambil otot
        muscles = requests.get('https://wger.de/api/v2/muscle/').json()['results']
        muscle_dict = {muscle['id']: muscle['name'] for muscle in muscles}

        # Ambil semua latihan
        all_exercises = []
        next_url = 'https://wger.de/api/v2/exercise/?limit=100'

        while next_url:
            response = requests.get(next_url)
            data = response.json()
            all_exercises.extend(data['results'])
            next_url = data['next']

        # Tambahkan info dan simpan
        total_saved = 0
        now = datetime.utcnow()
        for exercise in all_exercises:
            exercise['category_name'] = category_dict.get(exercise.get('category'), 'Unknown')
            exercise['equipment_names'] = [equipment_dict.get(eq_id, 'Unknown') for eq_id in exercise.get('equipment', [])]
            exercise['muscle_names'] = [muscle_dict.get(mid, 'Unknown') for mid in exercise.get('muscles', [])]
            exercise['muscle_secondary_names'] = [muscle_dict.get(mid, 'Unknown') for mid in exercise.get('muscles_secondary', [])]
            exercise['last_synced'] = now

            collection.replace_one({'id': exercise['id']}, exercise, upsert=True)
            total_saved += 1

        print(f"✅ Sinkronisasi selesai. Total data diproses: {total_saved} latihan.")

    except Exception as e:
        print(f"❌ Terjadi kesalahan saat sinkronisasi: {e}")

# Jadwalkan setiap 30 detik
scheduler.add_job(id='SyncDataJob', func=sync_exercise_data, trigger='interval', seconds=30)

@app.route('/')
def home():
    return 'Scheduler aktif. Sinkronisasi akan tampil di terminal.'

@app.route('/recent')
def get_recent_exercises():
    client = MongoClient("mongodb://localhost:27017/")
    db = client['capstone']  # Pastikan sama dengan yang di atas
    collection = db['visualisasi2']
    one_day_ago = datetime.utcnow() - timedelta(days=1)
    recent_exercises = list(collection.find({'last_synced': {'$gte': one_day_ago}}, {'_id': 0, 'name': 1, 'last_synced': 1}))
    return {'recent_exercises': recent_exercises}

if __name__ == '__main__':
    print("🚀 Flask server berjalan di http://localhost:5000")
    app.run(debug=True)
