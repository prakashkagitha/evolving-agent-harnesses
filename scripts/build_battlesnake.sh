#!/usr/bin/env bash
# Build the BattleSnake rules-engine binary used by the native sim (requires Go).
# Produces BattleSnake/game/battlesnake, where cc_gepa/sim.py expects it.
set -euo pipefail
cd "$(dirname "$0")/../BattleSnake/game"
go build -o battlesnake ./cli/battlesnake
echo "built: BattleSnake/game/battlesnake"
