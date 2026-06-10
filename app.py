import os
from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "SHxNumber Zone Bot is Running 24/7 Successfully!"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
