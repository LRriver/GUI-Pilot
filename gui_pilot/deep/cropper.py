"""Screenshot crop proposal utilities for high-budget reasoning."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class CropRegion:
    """A normalized crop proposal."""

    name: str
    box: Tuple[int, int, int, int]


class VisualCropper:
    """Generate stable UI crop regions without heavy CV dependencies."""

    def propose_regions(self, image) -> List[CropRegion]:
        width, height = image.size
        return [
            CropRegion("top_bar", (0, 0, width, int(height * 0.18))),
            CropRegion("center_content", (0, int(height * 0.15), width, int(height * 0.82))),
            CropRegion("bottom_bar", (0, int(height * 0.78), width, height)),
            CropRegion("right_actions", (int(width * 0.72), 0, width, height)),
        ]

    def crop(self, image, region: CropRegion):
        """Return the PIL crop for a proposed region."""
        return image.crop(region.box)
