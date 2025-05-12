from flask import  jsonify, Flask, request
import firebase_admin
from firebase_admin import credentials, firestore
import uuid
import base64
import os
import json
#from dotenv import load_dotenv

with open("firebase_credentials.json") as f:
    firebase_cred_json = json.load(f)

cred = credentials.Certificate(firebase_cred_json)

firebase_admin.initialize_app(cred)
db = firestore.client()

app = Flask(__name__)

@app.route('/register', methods=['POST'])
def register_user():
    try:
        user_address = request.json.get("address")

        if not user_address:
            return jsonify({"error": "Address is required"}), 400

        user_ref = db.collection("Users").document(user_address)
        user_doc = user_ref.get()

        if not user_doc.exists:
            user_ref.set({
                "address": user_address,
                "status": 1  
            })

    
            friends_ref = db.collection(user_address).document("Info")
            friends_ref.set({"info": "User friends list"})

        user_ref.set({"status": 1})

        friends_ref = db.collection(user_address)
        friends_docs = friends_ref.stream()
        friends_list = []

        for doc in friends_docs:
            friend_address = doc.id  
            if friend_address == "Info":
                continue  

            friend_data = doc.to_dict()
            friend_status = friend_data.get("status")

            # Check if the friend is online
            friend_doc = db.collection("Users").document(friend_address).get()
            friend_online_status = 1 if friend_doc.exists and friend_doc.to_dict().get("status") == 1 else 0

            friends_list.append({
                "address": friend_address,
                "status": friend_status,
                "On": friend_online_status
            })

        files_list = []
        for friend in friends_list:
            friend_address = friend["address"]
            friend_files_ref = db.collection(user_address).document(friend_address).collection("files")
            friend_files_docs = friend_files_ref.stream()

            for file_doc in friend_files_docs:
                file_data = file_doc.to_dict()
                files_list.append({
                    "File_Id":file_data.get("file_huff_id"),
                    "original_file": file_data.get("original_file"),
                    "uploaded_at": file_data.get("uploaded_at")
                })

        return jsonify({
            "message": "User registered" if not user_doc.exists else "User already exists",
            "address": user_address,
            "friends": friends_list,
            "files": files_list  
        }), 201

    except Exception as e:
        print(f"Error occurred: {e}")
        return jsonify({"error": "Internal server error", "message": str(e)}), 500
    
@app.route('/request_Sent',methods=['POST'])
def SendReq():
    try:
        data=request.json
        sender_address=data.get('user')
        receiver_address=data.get('Friend')
        if (not sender_address) or (not receiver_address) is None:
            return jsonify({"error": "Data is required"}), 400
        user_ref = db.collection("Users").document(receiver_address)
        user_doc = user_ref.get()

        if not user_doc.exists:
            return jsonify({"error": "User do not exists"}), 404
        else:
            db.collection(sender_address).document(receiver_address).set({
                "status": -1,
                "On": 0
            })
            db.collection(receiver_address).document(sender_address).set({
                "status": 0,
                "On": 0
            })
            return jsonify({"accept":"Success"}),200
    except Exception as e:
        print(f"Error occurred: {e}")
        return jsonify({"error": "Internal server error", "message": str(e)}), 500
    

@app.route('/Request_Accept_Deny', methods=['POST'])
def RequestAcceptDeny():
    try:
        data = request.json
        
        user_address = data.get("user")
        friend_address = data.get("Friend")
        status = data.get("status")


        if not user_address or not friend_address or status is None:
            return jsonify({"error": "Data is required"}), 400

        if status == "1":
            db.collection(user_address).document(friend_address).set({
                "status": 1,
                "On": 0
            })
            db.collection(friend_address).document(user_address).set({
                "status": 1,
                "On": 0
            })
        else:
            db.collection(user_address).document(friend_address).delete()
            db.collection(friend_address).document(user_address).delete()

        return jsonify({"Result": "Success"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/send_file', methods=['POST'])
def send_file():
    try:
        sender_address = request.form.get("sender")  
        receiver_address = request.form.get("receiver")
        file_huff = request.files.get("huff_file")
        file_tree = request.files.get("tree_file")

        filename = file_huff.filename.replace(".huff", "")
        if not sender_address or not receiver_address or not file_huff or not file_tree:
            return jsonify({"error": "Sender, receiver, and both files (.huff and .tree) are required"}), 400


        file_huff_data = file_huff.read()
        file_huff_base64 = base64.b64encode(file_huff_data).decode('utf-8')
        file_tree_data = file_tree.read()
        file_tree_base64 = base64.b64encode(file_tree_data).decode('utf-8')
        
        file_huff_id = str(uuid.uuid4()) 
        file_tree_id = str(uuid.uuid4())  


        receiver_ref = db.collection(receiver_address).document(sender_address)
        
        
        file_entry = {
    "original_file": filename,  
    "file_huff_id": file_huff_id,
    "file_huff_name": file_huff.filename,
    "file_huff_data": file_huff_base64,
    "file_tree_id": file_tree_id,
    "file_tree_name": file_tree.filename,
    "file_tree_data": file_tree_base64,
    "uploaded_at": firestore.SERVER_TIMESTAMP
}

        receiver_ref.collection("files").document(file_huff_id).set(file_entry)
       # receiver_ref.collection("files").document(file_huff_id).set(file_huff_entry)
       # receiver_ref.collection("files").document(file_tree_id).set(file_tree_entry)
       

        return jsonify({
            "message": "Files sent successfully",
            "files": [
                {"file_id": file_huff_id, "file_name": file_huff.filename},
                {"file_id": file_tree_id, "file_name": file_tree.filename}
            ]
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/get_files', methods=['POST'])
def get_files():
    try:
        receiver_address = request.json.get("receiver")
        sender_address = request.json.get("sender")
        file_id = request.json.get("file_id")

        if not receiver_address or not sender_address or not file_id:
            return jsonify({"error": "Receiver, sender, and file_id are required"}), 400

        # Reference to the stored file
        file_ref = db.collection(receiver_address).document(sender_address).collection("files").document(file_id)
        file_data = file_ref.get()

        if not file_data.exists:
            return jsonify({"error": "File not found"}), 404

        file_info = file_data.to_dict()
        response_Data={
            "message": "File retrieved successfully",
            "original_file": file_info["original_file"],
            "file_huff_data": file_info["file_huff_data"],  
            "file_tree_data": file_info["file_tree_data"], 
            "Time_Stamp":file_info["uploaded_at"]
        }

        file_ref.delete()

        return jsonify(response_Data), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500



if __name__ == '__main__':
    app.run()

