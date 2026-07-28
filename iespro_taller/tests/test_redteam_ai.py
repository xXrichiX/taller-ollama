"""Red team automatizado — batería adversarial de prompts IA."""

from __future__ import annotations

import unittest

from services.guardrails import validate_user_prompt
from services.redteam_cases import REDTEAM_PROMPTS


class RedTeamAITests(unittest.TestCase):
  def test_adversarial_battery(self) -> None:
    failures: list[str] = []
    for prompt, should_block in REDTEAM_PROMPTS:
      result = validate_user_prompt(prompt)
      if result.blocked != should_block:
        failures.append(
          f"prompt={prompt[:60]!r} expected_blocked={should_block} got={result.blocked} rule={result.rule_id}"
        )
    if failures:
      self.fail("Red team failures:\n" + "\n".join(failures))

  def test_no_false_positive_on_benign_workshop_flow(self) -> None:
    benign = [
      "¿Tienen disponibilidad para cambio de aceite mañana?",
      "Mi placa es ABC123, ¿cuándo fue la última visita?",
      "Necesito cotizar frenos delanteros",
    ]
    for prompt in benign:
      result = validate_user_prompt(prompt)
      self.assertFalse(result.blocked, msg=prompt)


if __name__ == "__main__":
  unittest.main()
