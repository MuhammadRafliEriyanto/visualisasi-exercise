import streamlit as st
import requests
from datetime import datetime
from pymongo import MongoClient
import os
from pymongo import MongoClient
from dotenv import load_dotenv

# Koneksi MongoDB (ubah sesuai konfigurasi kamu)

load_dotenv()

mongo_uri = os.getenv("MONGODB_URI")
print("DEBUG MONGODB_URI:", mongo_uri)

client = MongoClient(mongo_uri)  # ✅ Benar!
db = client["capstone"]
collection = db["exercises"]

# Fungsi sinkronisasi data dari API WGER
def sync_exercise_data():
    try:
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
        next_url = 'https://wger.de/api/v2/exerciseinfo/?limit=100&language=2'

        while next_url:
            response = requests.get(next_url)
            data = response.json()
            all_exercises.extend(data['results'])
            next_url = data['next']

        total_saved = 0
        now = datetime.utcnow()

        for exercise in all_exercises:
            exercise['category_name'] = category_dict.get(exercise.get('category', {}).get('id'), 'Unknown')
            exercise['equipment_names'] = [equipment_dict.get(eq.get('id'), 'Unknown') for eq in exercise.get('equipment', [])]
            exercise['muscle_names'] = [muscle_dict.get(m.get('id'), 'Unknown') for m in exercise.get('muscles', [])]
            exercise['muscle_secondary_names'] = [muscle_dict.get(m.get('id'), 'Unknown') for m in exercise.get('muscles_secondary', [])]
            exercise['last_synced'] = now

            if not exercise.get('name'):
                exercise['name'] = 'No Name'

            collection.replace_one({'id': exercise['id']}, exercise, upsert=True)
            total_saved += 1

        return total_saved

    except Exception as e:
        return f"❌ Error: {e}"

# Streamlit UI
st.title("💪 WGER Exercise Sync App")

if st.button("🔄 Sinkronisasi Data Latihan"):
    result = sync_exercise_data()
    if isinstance(result, int):
        st.success(f"✅ Sinkronisasi berhasil. Total data disimpan: {result}")
    else:
        st.error(result)

if st.button("📋 Tampilkan Semua Latihan"):
    data = list(collection.find().sort("name", 1))
    if data:
        for item in data:
            st.subheader(item['name'])
            st.write(f"Kategori: {item.get('category_name', 'Unknown')}")
            st.write(f"Peralatan: {', '.join(item.get('equipment_names', []))}")
            st.write(f"Otot Utama: {', '.join(item.get('muscle_names', []))}")
            st.write(f"Otot Sekunder: {', '.join(item.get('muscle_secondary_names', []))}")
            st.markdown("---")
    else:
        st.warning("Belum ada data latihan tersimpan.")

