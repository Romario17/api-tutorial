from fastapi import FastAPI, WebSocketDisconnect
from fastapi.websockets import WebSocket

app = FastAPI()

class GerenciadorDeConexoes:
    def __init__(self):
        self.ativas: list[WebSocket] = []

    async def conectar(self, ws: WebSocket):
        await ws.accept()
        self.ativas.append(ws)

    def desconectar(self, ws: WebSocket):
        self.ativas.remove(ws)

    async def broadcast(self, mensagem: str):
        for ws in self.ativas:
            await ws.send_text(mensagem)


gerenciador = GerenciadorDeConexoes()


@app.websocket("/ws/sala")
async def sala(websocket: WebSocket):
    await gerenciador.conectar(websocket)
    try:
        while True:
            msg = await websocket.receive_text()
            await gerenciador.broadcast(f"Usuário disse: {msg}")
    except WebSocketDisconnect:
        gerenciador.desconectar(websocket)
        await gerenciador.broadcast("Um usuário saiu da sala.")
