# [CodeClash] BattleSnake
This is the starter codebase for the BattleSnake arena featured in CodeClash.

The core components of this codebase are:
- **Python Starter Kit**: https://github.com/BattlesnakeOfficial/starter-snake-python
    - The root level files of this repository are directly copied from the above.
    - We realize that BattleSnake supports many more languages than Python ([reference](https://docs.battlesnake.com/starter-projects)). Supporting these is on our roadmap!
- **Game Engine**: https://github.com/BattlesnakeOfficial/rules
    - This is the source code for the local BattleSnake cli game engine, represented in `game/`.
    - We compile the `./battlesnake` executable from this folder during the Docker build process.
- **Official BattleSnake Documentation**: https://github.com/BattlesnakeOfficial/docs
    - This is the source code for the official BattleSnake documentation website.
    - We copy the relevant documentation files into the `docs/` folder.