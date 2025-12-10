from . import app
import os
import json
import pymongo
from flask import jsonify, request, make_response, abort, url_for  # noqa; F401
from pymongo import MongoClient
from bson import json_util
from pymongo.errors import OperationFailure
from pymongo.results import InsertOneResult
from bson.objectid import ObjectId
import sys
from bson.json_util import dumps

SITE_ROOT = os.path.realpath(os.path.dirname(__file__))
json_url = os.path.join(SITE_ROOT, "data", "songs.json")
songs_list: list = json.load(open(json_url))

# client = MongoClient(
#     f"mongodb://{app.config['MONGO_USERNAME']}:{app.config['MONGO_PASSWORD']}@localhost")
mongodb_service = os.environ.get('MONGODB_SERVICE')
mongodb_username = os.environ.get('MONGODB_USERNAME')
mongodb_password = os.environ.get('MONGODB_PASSWORD')
mongodb_port = os.environ.get('MONGODB_PORT')

print(f'The value of MONGODB_SERVICE is: {mongodb_service}')

if mongodb_service == None:
    app.logger.error('Missing MongoDB server in the MONGODB_SERVICE variable')
    # abort(500, 'Missing MongoDB server in the MONGODB_SERVICE variable')
    sys.exit(1)

if mongodb_username and mongodb_password:
    url = f"mongodb://{mongodb_username}:{mongodb_password}@{mongodb_service}"
else:
    url = f"mongodb://{mongodb_service}"


print(f"connecting to url: {url}")

try:
    client = MongoClient(url)
except OperationFailure as e:
    app.logger.error(f"Authentication error: {str(e)}")

db = client.songs
db.songs.drop()
db.songs.insert_many(songs_list)

def parse_json(data):
    return json.loads(json_util.dumps(data))

######################################################################
# INSERT CODE HERE
######################################################################

@app.route("/health", methods = ['GET'])
def health():
    return jsonify({"status": "OK"}), 200

@app.route("/count", methods = ['GET'])
def count():
    try:
        songs_count = db.songs.count_documents({})
        return jsonify({"count": songs_count}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/song", methods = ['GET'])
def song():
    try:
        cursor = db.songs.find({})
        song_list = list(cursor)
        return jsonify({"songs": parse_json(song_list)}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/song/<id>", methods=['GET'])
def get_song_by_id(id):
    try:
        song_id = int(id)
    except ValueError:
        return jsonify({"message": "song with id not found"}), 404

    song = db.songs.find_one({"id": song_id})

    if not song:
        return jsonify({"message": "song with id not found"}), 404

    return jsonify(parse_json(song)), 200

@app.route("/song", methods = ['POST'])
def create_song():
    song = request.get_json()

    if "id" not in song:
        return jsonify({"message": "missing id field"}), 400

    try:
        song_id = int(song["id"])
    except ValueError:
        return jsonify({"Message": "id must be an integer"}), 400

    existing = db.songs.find_one({"id": song_id})
    if existing:
        return jsonify({"Message": f"song with id {song_id} already present"}), 302

    result = db.songs.insert_one(song)

    return jsonify({"inserted id": parse_json(result.inserted_id)}), 201

@app.route("/song/<int:id>", methods=['PUT'])
def update_song(id):
    # Datos enviados por el cliente
    song_data = request.get_json()

    # 1. Comprobar si la canción existe
    existing_song = db.songs.find_one({"id": id})
    if not existing_song:
        return jsonify({"message": "song not found"}), 404

    # 2. Intentar actualizarla con $set
    result = db.songs.update_one({"id": id}, {"$set": song_data})

    # 3. Si no se modificó nada
    if result.modified_count == 0:
        return jsonify({"message": "song found, but nothing updated"}), 200

    # 4. Volver a leer la canción actualizada y devolverla
    updated_song = db.songs.find_one({"id": id})
    return jsonify(parse_json(updated_song)), 201

@app.route("/song/<int:id>", methods=['DELETE'])
def delete_song(id):
    result = db.songs.delete_one({"id": id})

    if result.deleted_count == 0:
        return jsonify({"message": "song not found"}), 404

    return "", 204
