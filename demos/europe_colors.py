#!/usr/bin/env python3
import enum
import itertools
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from pybelsberg import always


class Color(enum.IntEnum):
    RED = 0
    GREEN = 1
    YELLOW = 2
    BLUE = 3


class Country:
    def __init__(self, name, polygon):
        self.name = name
        self.polygon = polygon
        self.color = Color.RED
        self.neighbors = []

    def get_color(self):
        return self.color

    def set_color(self, value):
        self.color = value

    def is_neighbor_of(self, other):
        return other in self.neighbors


POLYGONS = {
    "Iceland": [(143, 156), (153, 172), (95, 191), (48, 186), (59, 180), (34, 174), (54, 169), (30, 166), (124, 155)],
    "Norway": [(633, 99), (667, 119), (516, 130), (454, 184), (436, 247), (375, 250), (377, 202), (530, 115), (613, 101)],
    "Sweden": [(564, 164), (515, 200), (525, 232), (492, 280), (458, 289), (436, 247), (454, 184), (540, 124), (584, 161)],
    "Finland": [(638, 124), (667, 205), (632, 227), (555, 224), (557, 195), (601, 172), (580, 138), (547, 124), (643, 116)],
    "Russia": [(571, 301), (535, 300), (538, 295), (554, 291), (571, 295), (570, 298)],
    "Ireland": [(238, 307), (240, 315), (232, 326), (211, 333), (195, 331), (204, 319), (198, 306), (223, 291), (223, 304), (230, 304)],
    "Britain": [(275, 249), (274, 281), (326, 337), (249, 353), (276, 305), (239, 272), (261, 250)],
    "Portugal": [(206, 450), (215, 445), (236, 456), (223, 477), (229, 496), (219, 511), (207, 510), (208, 494), (200, 488), (206, 454)],
    "Spain": [(206, 450), (202, 436), (218, 428), (344, 450), (319, 461), (302, 501), (248, 521), (223, 504), (236, 456), (210, 447)],
    "France": [(351, 348), (403, 365), (379, 392), (395, 428), (331, 445), (292, 436), (296, 401), (257, 369), (345, 344)],
    "Switzerland": [(420, 383), (418, 388), (430, 390), (429, 395), (393, 404), (384, 396), (379, 398), (387, 382), (407, 379)],
    "Germany": [(424, 293), (474, 314), (482, 340), (450, 350), (458, 383), (395, 381), (403, 365), (381, 359), (389, 311), (416, 295)],
    "Italy": [(452, 392), (470, 406), (454, 424), (522, 471), (503, 467), (495, 497), (427, 426), (390, 422), (388, 401), (449, 387)],
    "Austria": [(505, 375), (494, 393), (478, 396), (418, 388), (423, 382), (458, 383), (458, 373), (466, 366), (504, 371)],
    "Poland": [(482, 340), (472, 308), (512, 295), (577, 302), (583, 316), (576, 323), (586, 344), (571, 365), (488, 344)],
    "Ukraine": [(675, 328), (770, 358), (766, 378), (699, 420), (674, 392), (634, 407), (655, 396), (639, 375), (563, 372), (580, 334), (665, 328)],
    "Hungary": [(496, 391), (497, 380), (504, 380), (505, 375), (515, 380), (549, 369), (571, 378), (551, 397), (522, 404), (498, 391)],
    "Romania": [(571, 378), (619, 375), (633, 391), (634, 407), (650, 412), (641, 414), (638, 428), (573, 427), (542, 399), (564, 381)],
    "Yugoslavia": [(549, 408), (570, 418), (567, 425), (574, 434), (567, 445), (530, 431), (535, 424), (526, 402), (548, 404)],
    "Bulgaria": [(570, 422), (638, 428), (628, 442), (631, 449), (573, 457), (567, 425)],
    "Greece": [(615, 454), (572, 467), (586, 501), (559, 511), (541, 477), (551, 463), (610, 451)],
    "Czechia": [(468, 346), (482, 341), (516, 348), (524, 361), (500, 372), (462, 367), (448, 355)],
    "Slovakia": [(524, 361), (545, 357), (570, 363), (586, 373), (574, 384), (548, 380), (522, 381), (500, 372)],
}

BORDERS = [
    ("Austria", "Germany"),
    ("Austria", "Hungary"),
    ("Austria", "Italy"),
    ("Austria", "Switzerland"),
    ("Bulgaria", "Greece"),
    ("Bulgaria", "Romania"),
    ("Bulgaria", "Yugoslavia"),
    ("Finland", "Norway"),
    ("Finland", "Sweden"),
    ("France", "Germany"),
    ("France", "Italy"),
    ("France", "Spain"),
    ("France", "Switzerland"),
    ("Germany", "Italy"),
    ("Germany", "Poland"),
    ("Germany", "Switzerland"),
    ("Hungary", "Romania"),
    ("Hungary", "Ukraine"),
    ("Hungary", "Yugoslavia"),
    ("Italy", "Switzerland"),
    ("Norway", "Sweden"),
    ("Poland", "Russia"),
    ("Poland", "Ukraine"),
    ("Portugal", "Spain"),
    ("Romania", "Ukraine"),
    ("Romania", "Yugoslavia"),
    ("Britain", "Ireland"),
    ("Russia", "Ukraine"),
    ("Czechia", "Austria"),
    ("Czechia", "Germany"),
    ("Czechia", "Poland"),
    ("Czechia", "Slovakia"),
    ("Slovakia", "Austria"),
    ("Slovakia", "Hungary"),
    ("Slovakia", "Poland"),
    ("Slovakia", "Ukraine"),
    ("Slovakia", "Romania"),
]


COUNTRIES = [Country(name, POLYGONS[name]) for name in POLYGONS]
COUNTRIES_BY_NAME = {c.name: c for c in COUNTRIES}
COLORS = list(Color)
HEX = {Color.RED: "#d95f5f", Color.GREEN: "#5fbf6a",
       Color.YELLOW: "#e8c53c", Color.BLUE: "#5b8bd9"}
WIDTH, HEIGHT = 940, 620


for c1, c2 in BORDERS:
    COUNTRIES_BY_NAME[c1].neighbors.append(COUNTRIES_BY_NAME[c2])
    COUNTRIES_BY_NAME[c2].neighbors.append(COUNTRIES_BY_NAME[c1])


# one, global environment: every constraint has to hold together with all
# the ones registered before it
for country in COUNTRIES:
    always(lambda: country.get_color() in COLORS)

for c1, c2 in itertools.combinations(COUNTRIES, 2):
    if c1.is_neighbor_of(c2):
        always(lambda: c1.get_color() != c2.get_color())


def run_gui():
    import tkinter as tk

    root = tk.Tk()
    root.title("pybelsberg -- four-colour Europe")
    canvas = tk.Canvas(root, width=WIDTH, height=HEIGHT,
                       bg="#bcd8e8", highlightthickness=0)
    canvas.pack()

    state = {"active": Color.RED}
    shape_ids = {}

    for country in COUNTRIES:
        flat = [coord for p in country.polygon for coord in p]
        shape_ids[country.name] = canvas.create_polygon(
            flat, outline="#404040", width=2, fill="#e8e8e0")
        canvas.tag_bind(shape_ids[country.name], "<Button-1>",
                        lambda event, c=country: click_country(c))
        xs = [p[0] for p in country.polygon]
        ys = [p[1] for p in country.polygon]
        canvas.create_text(sum(xs) / len(xs), sum(ys) / len(ys),
                           text=country.name, font=("sans", 7),
                           fill="#303030")

    panel_x = WIDTH - 160
    canvas.create_text(panel_x + 60, 28, text="Active color:",
                       font=("sans", 12, "bold"))
    swatch_ids = []
    for i, color in enumerate(Color):
        rid = canvas.create_rectangle(panel_x, 50 + i * 70,
                                      panel_x + 120, 100 + i * 70,
                                      fill=HEX[color], outline="#404040")
        canvas.tag_bind(rid, "<Button-1>", lambda event, col=color: click_swatch(col))
        swatch_ids.append((color, rid))

    def redraw():
        for country in COUNTRIES:
            canvas.itemconfig(shape_ids[country.name], fill=HEX[Color(int(country.color))])
        for color, rid in swatch_ids:
            canvas.itemconfig(rid, width=6 if color == state["active"] else 2)

    def click_swatch(color):
        state["active"] = color
        redraw()

    def click_country(country):
        try:
            country.set_color(state["active"])
        finally:
            redraw()

    redraw()

    root.mainloop()


if __name__ == "__main__":
    run_gui()
