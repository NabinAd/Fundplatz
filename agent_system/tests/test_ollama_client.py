"""Tests funktionieren ohne Ollama-Server und ohne Modell-Download."""
import json
import unittest
from unittest.mock import patch
from urllib.error import URLError

from agent_system.ollama_client import LLMConnectionError, OllamaClient


class OllamaClientTests(unittest.TestCase):
    @patch("agent_system.ollama_client.urlopen")
    def test_liefert_antworttext(self, mocked_open):
        mocked_open.return_value.__enter__.return_value.read.return_value = json.dumps(
            {"message": {"role": "assistant", "content": " 16 GB RAM. "}}
        ).encode("utf-8")
        client = OllamaClient(model="testmodell")
        answer = client.generate("Systemanweisung", "Kundenfrage")
        self.assertEqual(answer, "16 GB RAM.")
        request = mocked_open.call_args.args[0]
        payload = json.loads(request.data.decode("utf-8"))
        self.assertEqual(payload["model"], "testmodell")
        self.assertFalse(payload["stream"])
        self.assertEqual(payload["messages"][0]["role"], "system")
        self.assertEqual(payload["messages"][1]["role"], "user")

    @patch("agent_system.ollama_client.urlopen", side_effect=URLError("offline"))
    def test_ohne_server_verstaendlicher_fehler(self, _mocked_open):
        with self.assertRaisesRegex(LLMConnectionError, "nicht erreichbar"):
            OllamaClient().generate("System", "Frage")

    @patch("agent_system.ollama_client.urlopen")
    def test_leere_antwort_wird_abgelehnt(self, mocked_open):
        mocked_open.return_value.__enter__.return_value.read.return_value = b'{"message":{"content":""}}'
        with self.assertRaisesRegex(LLMConnectionError, "leeren Antworttext"):
            OllamaClient().generate("System", "Frage")

    @patch("agent_system.ollama_client.urlopen")
    def test_ungueltige_json_antwort_wird_abgelehnt(self, mocked_open):
        mocked_open.return_value.__enter__.return_value.read.return_value = b'not-json'
        with self.assertRaisesRegex(LLMConnectionError, "ungueltiges JSON|ungültiges JSON"):
            OllamaClient().generate("System", "Frage")


if __name__ == "__main__":
    unittest.main()
