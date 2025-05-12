import json
with open("contactform-2c612-firebase-adminsdk-i4ks3-6e8be73736.json", "r") as f:
    data = json.load(f)
    with open("firebase_env.txt", "w") as out:
        out.write(f'FIREBASE_CREDENTIALS="{json.dumps(data)}"')
