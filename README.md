# VillageSim (Terminal Edition)

## About the Game

**VillageSim** is a real‑time, terminal‑based medieval village simulator written entirely in Python. A procedurally generated **1 000 × 1 000‑tile** world—lush grasslands, dense forests, rugged stone outcrops, and meandering rivers—comes alive in nothing but Unicode glyphs.  From the first swing of an axe to the rise of a bustling hamlet, every moment is driven by an agent‑based simulation that plays out before your eyes at **around 60 ticks per second by default**.
The day/night cycle now stretches to roughly **24 seconds per day**, four times longer than before, giving you more time to watch villagers go about their business.
Lighting now uses a four-step hue cycle (night, morning, afternoon and evening) instead of a continuous fade, so colours shift discretely throughout the day.

Rather than micromanaging individual settlers, you watch emergent stories unfold.  Each villager is an autonomous entity that can plan paths, gather resources, construct buildings, and deliver supplies back to storage, all while navigating a living landscape that reacts to their actions.  A simple finite‑state machine turns a lone labourer into a self‑sufficient workforce that knows when to chop, haul, build, and rest.

As timber stacks in the Town Hall and stone fills the storehouses, the settlement expands organically.  New houses appear, population grows, and specialised structures—lumberyards today, perhaps blacksmiths tomorrow—push the frontier ever outward.  Your view glides across the world thanks to a smooth camera and zoomable levels of detail, letting you follow a single villager’s journey or take in the whole realm at a glance.

Powered by the **blessed** TUI library (with a curses fallback), VillageSim runs anywhere a Python interpreter does—headless servers, SSH sessions, or handhelds—while remaining easy to extend.  The codebase is modular, each subsystem capped at 10 k tokens, making it an ideal playground for experimenting with path‑finding, AI behaviours, and large‑world rendering in a tiny footprint.

---

## Feature Highlights

* **Procedural Worlds** – Seedable generator carves out a diverse, resource‑rich landscape every run.
* **Smooth ASCII Rendering** – Panning and zoom deliver crisp visuals at multiple levels of detail.
* **Autonomous Villagers** – Agents gather, build, and deliver via an A\* path‑finding engine you can watch in real time.
* **Dynamic Construction** – Town Halls, Lumberyards, Houses, Watchtowers and Marketplaces emerge where resources allow, boosting villager mood and enabling trade.
* **Resource Economy** – Wood and stone flow through inventories, storage, and building queues.
* **HUD & Controls** – Real‑time stats panel plus hotkeys for pause, step, help, and camera centring.
* **Caching & Logging** – Lighting results are cached and debug logging reveals render timings.
* **Extensible & Test‑Backed** – Modular architecture, unit tests, and CI workflow encourage contribution and experimentation.

## Game Logic

VillageSim runs on a simple tick loop managed by the `Game` class. During each tick the game:

1. Processes input to move or zoom the camera and toggle overlays.
2. Updates every `Villager` using a finite‑state machine with `idle`, `gather`, `deliver` and `build` states.
3. Dispatches jobs so villagers collect resources or work on buildings.
4. Spawns new villagers from completed houses, produces food at farms and plans roads on frequently used tiles.
5. Draws the current world state and status information.

Tiles are generated lazily via value noise so the 100k×100k world remains memory efficient.

---

## Quick Start

```bash
# Clone the repo
$ git clone https://github.com/your‑handle/villagesim.git
$ cd villagesim

# Create and activate a virtual environment
$ python3 -m venv .venv
$ source .venv/bin/activate            # Windows: .venv\Scripts\activate

# Install dependencies
$ pip install -r requirements.txt  # includes blessed for colour support

# Run the game
$ python3 -m src.main [--seed 42] [--show-fps] [-v]
```

### Default Controls

| Key       | Action           |
| --------- | ---------------- |
| WASD      | Pan camera       |
| `+` / `-` | Zoom in / out    |
| `space`   | Pause / Unpause  |
| `.`       | Single‑step tick |
| `c`       | Center camera    |
| `h`       | Toggle help pane |
| `q`       | Quit             |

The bottom row shows the current tick, current day, camera position/zoom,
stored resources and population. Use `--show-fps` to display performance metrics. Pass `-v` to
enable debug logging which now reports render timing and lighting cost.

---

## Development Roadmap (20 Steps)

1. **Project scaffold & dependencies** – Initialise `src/`, `main.py`, virtual‑env, and minimal docs.
2. **Core constants and enums** – World size, tile types, colours, tick rate.
3. **Tile & map data structures** – `Tile` class and 1 000 × 1 000 grid generator.
4. **Renderer skeleton** – Blessed‑powered screen clear & glyph draw.
5. **Camera & viewport logic** – World‑to‑screen transforms, panning, zoom.
6. **Input handling loop** – Non‑blocking key capture dispatched to camera/game.
7. **Game class with tick scheduler** – Update‑then‑render at 60 Hz.
8. **Villager entity & rendering** – `@` glyph overlay with per‑agent colours.
9. **Pathfinding module** – A\* / Dijkstra utilities plus nearest‑resource queries.
10. **Path visualisation** – Faint `·` breadcrumb of current route.
11. **Resource & inventory system** – Per‑agent inventory and global storage.
12. **Gathering & delivery behaviours** – FSM: GATHER → DELIVER → IDLE.
13. **Job dispatcher & FSM transitions** – Centralised job queue.
14. **Building blueprints & instances** – TownHall, Lumberyard, Watchtower.
15. **Construction queue & placement** – Auto‑placement helper, BUILD state.
16. **Lumberyard auto‑expansion** – Resource‑driven growth logic.
17. **House & population growth** – Housing cap and villager spawning.
18. **UI overlay & controls** – Status panel, help screen, CLI flags.
19. **Zoom‑level LOD & perf flags** – Glyph swap at low zoom, FPS monitor.
20. **Testing, docs & CI** – Unit tests, expanded README, GitHub Actions.

Each task is scoped to ≤ 10 k tokens, perfect for iteratively feeding to an agentic LLM.

---

## Contributing

Pull requests are welcome!  Please open an issue to discuss major changes first, ensure all tests pass (`pytest`) and follow the style guidelines defined in **ruff** and **black**.

---

## License

Licensed under the MIT License.  See `LICENSE` for details.