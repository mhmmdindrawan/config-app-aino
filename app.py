import socket
import threading
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware # type: ignore
import uvicorn # type: ignore
from sockets import SocketIOApp
from fastapi import Form
import asyncio
from aino import Aino, DebitTransactionException
from pcless import Pcless
from sti import Sti
from sti import sti_init_key

app = FastAPI()
sio = SocketIOApp()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/socket.io", sio.sio_app)

pcless = Pcless()
aino = Aino()
sti = Sti()


@app.get("/")
async def index():
    return {"message": "biswami tawwa"}

#  Aino
@app.get("/connectaino")
def connectaino():
    aino.start_serial()
    return JSONResponse(content="Berhasil", status_code=200)


@app.post("/debittransaction")
def debit_transaction(
        amount: int = Form(),
        transaction_code: str = Form()):

    try:
        status, data = aino.debit_transaction(amount, transaction_code)
        # type: ignore
        return JSONResponse(content=f"Berhasil Tansaksi, status = {status}, data = {data}", status_code=200)
    except DebitTransactionException as e:
        status = str(e.status)
        data = {
            "amount": e.amount,
            "response_as_hex": e.response_as_hex
        }
        print(e)

        return JSONResponse(content="Waktu Transaksi Habis", status_code=200)


@app.post("/submit")
async def submit_data():
    return {"message": "biswami tawwa"}


@app.get("/connect")
def connect():
    socket_thread = threading.Thread(target=pcless.connect, daemon=True)
    socket_thread.start()
    return JSONResponse(content="Berhasil", status_code=200)


@app.get("/connectsti")
def connectsti():
    sti.set_config("COM5")
    sti.start_serial()
    sti.reader_init(init_key=sti_init_key)
    return JSONResponse(content={"message": "Berhasil kokek sti"}, status_code=200)

@app.get("/disconnectsti")
def disconnect():
    sti.disconnectsti() 
    return JSONResponse(content="Diskonek", status_code=200)

@app.get("/checkbalance")
def check_balance():
    try:
        response = sti.check_balance()
        return JSONResponse(content=response, status_code=200)
    except AttributeError as e:
        return JSONResponse(500, "Error", "Method missing: prepare_data", str(e))
    except Exception as e:
        return JSONResponse(500, "Error", "Terjadi kesalahan saat mengecek saldo", str(e))
    
@app.get("/uid-check")
def uid_check():
    try:
        response = sti.uid_check()  # Pastikan objek 'sti' telah dibuat sebelumnya
        return {"message": "Success", "data": response}
    except Exception as e:
        return {"error": str(e)}
    
@app.post("/deduct")
def deduct(amount: int = Form()):
    try:
        response = sti.deduct(amount=amount)  
        return JSONResponse(content={"status": "success", "data": response}, status_code=200)
    except Exception as e:
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)


@app.get("/diskonek")
def disconnect():
    result = pcless.close_connection()
    return JSONResponse(content="Diskonek", status_code=200)


@app.get("/status")
def status():
    result = pcless.statusconnect()
    return JSONResponse(content="Connect Berhasil", status_code=200)


@app.get("/listen")
def listen():
    def run_listener():
        pcless.listen()  # This will run in a separate thread

    listener_thread = threading.Thread(target=run_listener, daemon=True)
    listener_thread.start()

    return JSONResponse(content={"status": "Listening started"}, status_code=200)


@app.post("/send-command")
def send_command():
    result = pcless.send_command("¦TRIG1ON©")
    return JSONResponse(content="Data Terkirim", status_code=200)


@app.post("/send-sound")
def send_sound():
    result = pcless.send_command("¦MT00027©")
    return JSONResponse(content="Selamat Datang", status_code=200)


@app.post("/send-sound2")
def send_sound2():
    result = pcless.send_command("¦MT00002©")
    return JSONResponse(content="Cek Kartu", status_code=200)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)
