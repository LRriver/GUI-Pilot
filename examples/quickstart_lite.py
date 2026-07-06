"""Minimal GUI-Pilot lite profile smoke example."""

import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gui_pilot import AgentInput, GuiPilotAgent


def main() -> None:
    agent = GuiPilotAgent(profile="lite")
    image = Image.new("RGB", (1080, 2400), "white")
    output = agent.act(AgentInput(instruction="打开爱奇艺", current_image=image, step_count=1))
    print(output.action, output.parameters)


if __name__ == "__main__":
    main()
