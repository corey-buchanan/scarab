# Scarab Workout Sequencer

Interactive workout sequencer TUI with ASCII animations. Built with Python and Textual.

## Installation

```bash
pip install -e .
# or
pip install -r requirements.txt
```

## Run

```bash
scarab
# or
python -m scarab.app
```

With local development (no install):

```bash
PYTHONPATH=src python -m scarab.app
```

## Features

- **Sequence Editor** (e): Load or create workouts, multi-loop support, per-level sets
- **ASCII Animations**: Exercise animations (small/medium/large) for viewport sizing
- **Workouts** (w): List workouts, select one, hit Start to play
- **Stats**: Points, XP, character leveling on completion

## Keyboard Shortcuts

- `h` - Home
- `e` - Editor (pick workout to edit or create new)
- `w` - Workouts (select workout, Start to play)
- `q` - Quit

## ASCII Frame Generator

Generate ASCII frames from line images:

```bash
python -m scarab.tools.ascii_generator -i screenshot.png -o src/scarab/data/frames/exercise_id --size medium
```

For multiple frames (animation):

```bash
python -m scarab.tools.ascii_generator -i frames_dir/ -o src/scarab/data/frames/exercise_id
```

Requires: `pip install pillow`

## Project Structure

- `src/scarab/` - Main package
- `src/scarab/data/` - Exercise catalog, workouts, ASCII frames
- `src/scarab/tools/ascii_generator/` - CLI to generate ASCII frames from images

## Future

- textual-web for browser deployment
- iOS app with WebView
