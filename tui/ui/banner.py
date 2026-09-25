from __future__ import annotations

_K = [
    "#   #",
    "#  # ",
    "###  ",
    "#  # ",
    "#   #",
]
_N = [
    "#   #",
    "##  #",
    "# # #",
    "#  ##",
    "#   #",
]
_L = [
    "#    ",
    "#    ",
    "#    ",
    "#    ",
    "#####",
]
_B = [
    "#### ",
    "#   #",
    "#### ",
    "#   #",
    "#### ",
]

_LETTERS = [_K, _N, _L, _B]
_GAP = "  "

KNLB_ASCII = "\n".join(_GAP.join(letter[row] for letter in _LETTERS) for row in range(5))
