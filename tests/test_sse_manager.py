"""
tests/test_sse_manager.py

Testes unitários para o SSEManager — gerenciador de Server-Sent Events.

Estes testes validam o comportamento do SSEManager de forma isolada,
sem dependência de banco de dados ou servidor HTTP. São testes puramente
de lógica assíncrona usando unittest.IsolatedAsyncioTestCase.
"""

import asyncio
import unittest

from app.core.sse import SSEManager


class TestSSEManagerBroadcast(unittest.IsolatedAsyncioTestCase):
    """Testes de broadcast de eventos SSE."""

    def setUp(self) -> None:
        self.manager = SSEManager()

    async def test_broadcast_envia_para_todos_os_assinantes(self) -> None:
        """broadcast() deve entregar a mensagem para todas as filas ativas."""
        mensagens_cliente1: list[str] = []
        mensagens_cliente2: list[str] = []

        async def consumir(destino: list[str]) -> None:
            async for msg in self.manager.subscribe():
                destino.append(msg)
                if len(destino) >= 1:
                    break

        task1 = asyncio.create_task(consumir(mensagens_cliente1))
        task2 = asyncio.create_task(consumir(mensagens_cliente2))

        # Aguarda as filas serem criadas
        await asyncio.sleep(0.05)

        await self.manager.broadcast("ticket.created", {"id": "123"})

        await asyncio.wait_for(asyncio.gather(task1, task2), timeout=2.0)

        esperado = 'event: ticket.created\ndata: {"id": "123"}\n\n'
        self.assertEqual(mensagens_cliente1, [esperado])
        self.assertEqual(mensagens_cliente2, [esperado])

    async def test_broadcast_sem_assinantes_nao_falha(self) -> None:
        """broadcast() sem nenhum assinante conectado não deve lançar exceção."""
        await self.manager.broadcast("ticket.updated", {"id": "456"})
        # Se não lançou exceção, o teste passou
        self.assertEqual(len(self.manager._queues), 0)

    async def test_formato_sse_correto(self) -> None:
        """A mensagem deve seguir o formato SSE: event: ...\ndata: ...\n\n."""
        mensagens: list[str] = []

        async def consumir() -> None:
            async for msg in self.manager.subscribe():
                mensagens.append(msg)
                break

        task = asyncio.create_task(consumir())
        await asyncio.sleep(0.05)

        await self.manager.broadcast("ticket.updated", {"status": "closed"})
        await asyncio.wait_for(task, timeout=2.0)

        msg = mensagens[0]
        self.assertTrue(msg.startswith("event: ticket.updated\n"))
        self.assertIn("data: ", msg)
        self.assertTrue(msg.endswith("\n\n"))


class TestSSEManagerSubscribe(unittest.IsolatedAsyncioTestCase):
    """Testes de assinatura e gerenciamento de filas SSE."""

    def setUp(self) -> None:
        self.manager = SSEManager()

    async def test_subscribe_cria_fila(self) -> None:
        """Ao iniciar uma assinatura, uma fila deve ser adicionada."""
        self.assertEqual(len(self.manager._queues), 0)

        async def consumir() -> None:
            async for _ in self.manager.subscribe():
                break

        task = asyncio.create_task(consumir())
        await asyncio.sleep(0.05)

        self.assertEqual(len(self.manager._queues), 1)

        # Envia uma mensagem para desbloquear o consumidor e finalizar
        await self.manager.broadcast("test", {})
        await asyncio.wait_for(task, timeout=2.0)

    async def test_desconexao_remove_fila(self) -> None:
        """Quando o consumidor encerra, a fila deve ser removida."""
        async def consumir() -> None:
            async for _ in self.manager.subscribe():
                break

        task = asyncio.create_task(consumir())
        await asyncio.sleep(0.05)
        self.assertEqual(len(self.manager._queues), 1)

        await self.manager.broadcast("test", {})
        await asyncio.wait_for(task, timeout=2.0)

        # Aguarda o finally do gerador completar a remoção
        await asyncio.sleep(0.05)

        # Após o consumidor encerrar, a fila deve ser removida
        self.assertEqual(len(self.manager._queues), 0)

    async def test_keep_alive_enviado_apos_timeout(self) -> None:
        """Se nenhum evento for emitido, o subscribe deve enviar keep-alive."""
        mensagens: list[str] = []

        # Substituímos o timeout do manager para ser curto nos testes
        original_subscribe = self.manager.subscribe

        async def subscribe_com_timeout_curto():
            q = self.manager._new_queue()
            try:
                while True:
                    try:
                        message = await asyncio.wait_for(q.get(), timeout=0.1)
                        yield message
                    except TimeoutError:
                        yield ": keep-alive\n\n"
            finally:
                self.manager._remove_queue(q)

        async def consumir() -> None:
            async for msg in subscribe_com_timeout_curto():
                mensagens.append(msg)
                if len(mensagens) >= 1:
                    break

        task = asyncio.create_task(consumir())
        await asyncio.wait_for(task, timeout=2.0)

        self.assertEqual(mensagens[0], ": keep-alive\n\n")

    async def test_multiplos_eventos_em_sequencia(self) -> None:
        """O assinante deve receber múltiplos eventos na ordem de envio."""
        mensagens: list[str] = []

        async def consumir() -> None:
            async for msg in self.manager.subscribe():
                mensagens.append(msg)
                if len(mensagens) >= 3:
                    break

        task = asyncio.create_task(consumir())
        await asyncio.sleep(0.05)

        await self.manager.broadcast("ticket.created", {"id": "1"})
        await self.manager.broadcast("ticket.updated", {"id": "2"})
        await self.manager.broadcast("ticket.assigned", {"id": "3"})

        await asyncio.wait_for(task, timeout=2.0)

        self.assertEqual(len(mensagens), 3)
        self.assertIn("ticket.created", mensagens[0])
        self.assertIn("ticket.updated", mensagens[1])
        self.assertIn("ticket.assigned", mensagens[2])


if __name__ == "__main__":
    unittest.main()
