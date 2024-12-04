from flask import Flask, jsonify
import sqlite3
import os

app = Flask(__name__)

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, "publishers.db")

@app.route("/api/publishers", methods=["GET"])
def get_publishers():
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM publishers")
        publishers = cursor.fetchall()
        conn.close()
        return jsonify({"publishers": publishers})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
