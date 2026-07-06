"""Minimal GUI-Pilot deep profile smoke example."""

import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gui_pilot import AgentInput, GuiPilotAgent, GuiPilotConfig


def main() -> None:
    agent = GuiPilotAgent(config=GuiPilotConfig(profile="deep", candidate_count=2))
    image = Image.new("RGB", (1080, 2400), "white")
    output = agent.act(AgentInput(instruction="打开爱奇艺", current_image=image, step_count=1))
    print(output.action, output.parameters)


if __name__ == "__main__":
    main()
