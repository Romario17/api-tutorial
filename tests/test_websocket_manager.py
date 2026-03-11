"""
tests/test_websocket_manager.py

Testes unitários para o WebSocketManager — gerenciador de conexões WebSocket
agrupadas por ticket.

Utiliza mocks para simular objetos WebSocket do FastAPI, permitindo testar
a lógica de gerenciamento de conexões sem necessidade de servidor real.
"""

import json
import unittest
from unittest.mock import AsyncMock, MagicMock

from app.core.websocket_manager import WebSocketManager


class TestWebSocketManagerConnect(unittest.IsolatedAsyncioTestCase):
    """Testes de conexão WebSocket."""

    def setUp(self) -> None:
        self.manager = WebSocketManager()

    def _criar_ws_mock(self) -> MagicMock:
        """Cria um mock de WebSocket com métodos async."""
        ws = MagicMock()
        ws.accept = AsyncMock()
        ws.send_text = AsyncMock()
        return ws

    async def test_connect_aceita_e_registra_websocket(self) -> None:
        """connect() deve chamar accept() e registrar a conexão no ticket."""
        ws = self._criar_ws_mock()

        await self.manager.connect("ticket-1", ws)

        ws.accept.assert_awaited_once()
        self.assertIn(ws, self.manager._connections["ticket-1"])

    async def test_multiplas_conexoes_no_mesmo_ticket(self) -> None:
        """Múltiplos clientes podem se conectar ao mesmo ticket."""
        ws1 = self._criar_ws_mock()
        ws2 = self._criar_ws_mock()

        await self.manager.connect("ticket-1", ws1)
        await self.manager.connect("ticket-1", ws2)

        self.assertEqual(len(self.manager._connections["ticket-1"]), 2)
        self.assertIn(ws1, self.manager._connections["ticket-1"])
        self.assertIn(ws2, self.manager._connections["ticket-1"])

    async def test_conexoes_em_tickets_diferentes_sao_isoladas(self) -> None:
        """Conexões de tickets diferentes devem ser independentes."""
        ws1 = self._criar_ws_mock()
        ws2 = self._criar_ws_mock()

        await self.manager.connect("ticket-1", ws1)
        await self.manager.connect("ticket-2", ws2)

        self.assertEqual(len(self.manager._connections["ticket-1"]), 1)
        self.assertEqual(len(self.manager._connections["ticket-2"]), 1)


class TestWebSocketManagerDisconnect(unittest.IsolatedAsyncioTestCase):
    """Testes de desconexão WebSocket."""

    def setUp(self) -> None:
        self.manager = WebSocketManager()

    def _criar_ws_mock(self) -> MagicMock:
        ws = MagicMock()
        ws.accept = AsyncMock()
        ws.send_text = AsyncMock()
        return ws

    async def test_disconnect_remove_conexao(self) -> None:
        """disconnect() deve remover a conexão do ticket."""
        ws = self._criar_ws_mock()
        await self.manager.connect("ticket-1", ws)

        self.manager.disconnect("ticket-1", ws)

        self.assertNotIn(ws, self.manager._connections["ticket-1"])

    async def test_disconnect_conexao_inexistente_nao_falha(self) -> None:
        """disconnect() com conexão não registrada não deve lançar exceção."""
        ws = self._criar_ws_mock()
        # Não fez connect, mas disconnect não deve falhar
        self.manager.disconnect("ticket-inexistente", ws)

    async def test_disconnect_preserva_outras_conexoes(self) -> None:
        """Ao desconectar um cliente, os outros devem permanecer."""
        ws1 = self._criar_ws_mock()
        ws2 = self._criar_ws_mock()

        await self.manager.connect("ticket-1", ws1)
        await self.manager.connect("ticket-1", ws2)

        self.manager.disconnect("ticket-1", ws1)

        self.assertNotIn(ws1, self.manager._connections["ticket-1"])
        self.assertIn(ws2, self.manager._connections["ticket-1"])


class TestWebSocketManagerBroadcast(unittest.IsolatedAsyncioTestCase):
    """Testes de broadcast de mensagens WebSocket."""

    def setUp(self) -> None:
        self.manager = WebSocketManager()

    def _criar_ws_mock(self) -> MagicMock:
        ws = MagicMock()
        ws.accept = AsyncMock()
        ws.send_text = AsyncMock()
        return ws

    async def test_broadcast_envia_para_todos_do_ticket(self) -> None:
        """broadcast_to_ticket() deve enviar JSON para todos os participantes."""
        ws1 = self._criar_ws_mock()
        ws2 = self._criar_ws_mock()

        await self.manager.connect("ticket-1", ws1)
        await self.manager.connect("ticket-1", ws2)

        data = {"type": "message", "author": "alice", "message": "Olá!"}
        await self.manager.broadcast_to_ticket("ticket-1", data)

        esperado = json.dumps(data)
        ws1.send_text.assert_awaited_once_with(esperado)
        ws2.send_text.assert_awaited_once_with(esperado)

    async def test_broadcast_nao_envia_para_outros_tickets(self) -> None:
        """broadcast_to_ticket() deve enviar apenas para o ticket especificado."""
        ws_ticket1 = self._criar_ws_mock()
        ws_ticket2 = self._criar_ws_mock()

        await self.manager.connect("ticket-1", ws_ticket1)
        await self.manager.connect("ticket-2", ws_ticket2)

        await self.manager.broadcast_to_ticket(
            "ticket-1",
            {"type": "message", "message": "Somente ticket 1"},
        )

        ws_ticket1.send_text.assert_awaited_once()
        ws_ticket2.send_text.assert_not_awaited()

    async def test_broadcast_remove_conexoes_mortas(self) -> None:
        """Conexões que falham ao enviar devem ser removidas automaticamente."""
        ws_ativo = self._criar_ws_mock()
        ws_morto = self._criar_ws_mock()
        ws_morto.send_text = AsyncMock(side_effect=RuntimeError("Conexão perdida"))

        await self.manager.connect("ticket-1", ws_ativo)
        await self.manager.connect("ticket-1", ws_morto)

        await self.manager.broadcast_to_ticket(
            "ticket-1",
            {"type": "message", "message": "teste"},
        )

        # A conexão morta deve ter sido removida
        self.assertNotIn(ws_morto, self.manager._connections["ticket-1"])
        # A conexão ativa deve permanecer
        self.assertIn(ws_ativo, self.manager._connections["ticket-1"])

    async def test_broadcast_ticket_sem_conexoes_nao_falha(self) -> None:
        """broadcast_to_ticket() para um ticket sem conexões não deve falhar."""
        await self.manager.broadcast_to_ticket(
            "ticket-vazio",
            {"type": "message", "message": "ninguém vai receber"},
        )
        # Se não lançou exceção, o teste passou


if __name__ == "__main__":
    unittest.main()
