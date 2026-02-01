# 2XKO Frame Data

Comprehensive frame data repository for **2XKO**, the 2v2 fighting game from Riot Games.

## 📊 Overview

This repository contains frame data for all champions in 2XKO, automatically updated from the official [2XKO Wiki](https://2xko.wiki). Frame data is essential for competitive play, helping players understand move properties, combo potential, and safe pressure options.

## 🎮 What is Frame Data?

Frame data provides critical information about each move:
- **Startup**: Frames until the move becomes active
- **On Hit**: Frame advantage when the move connects (positive = you can continue pressure)
- **On Block**: Frame advantage when blocked (negative = opponent can punish)
- **Recovery**: Frames after the move ends before you can act again

## 📁 Data Format

The repository uses JSON format for easy parsing and integration:

```json
{
  "champions": [
    {
      "name": "Ekko",
      "moves": [
        {
          "name": "5L",
          "startup": 6,
          "onHit": 0,
          "onBlock": -2,
          "recovery": 10,
          "type": "normal"
        }
      ]
    }
  ]
}
```

## 🔗 Live View

View the frame data interactively at:
- **Web Interface**: [findtorontoevents.ca/2xko](https://findtorontoevents.ca/2xko)
- **Standalone Page**: [findtorontoevents.ca/2xkoframedata.html](https://findtorontoevents.ca/2xkoframedata.html)

## 🤖 AI Analysis

The web interface includes AI-powered analysis that automatically identifies:
- **Safest Moves**: Moves that are safe on block or have fast startup
- **Efficient Combos**: Optimal combo routes based on frame advantage
- **Replay Review Tips**: What to look for when analyzing your matches

## 📝 Frame Data Structure

### Move Properties

- **name**: Move notation (e.g., "5L", "2M", "236H")
- **startup**: Frames until active (lower = faster)
- **onHit**: Frame advantage on hit (positive = advantage, negative = disadvantage)
- **onBlock**: Frame advantage on block (positive = safe, negative = punishable)
- **recovery**: Frames of recovery after the move
- **damage**: Damage value (if available)
- **guard**: Guard type (if available)
- **type**: Move category (normal, special, super)

### Champion Data

Each champion entry includes:
- **name**: Champion name
- **moves**: Array of all moves with frame data

## 🔄 Auto-Update

Frame data is automatically updated daily from the official 2XKO Wiki. The web interface checks for updates every 24 hours.

## 🎯 Usage Tips

### Reading Frame Data

- **Positive on Block** (+): Safe to use in pressure, opponent cannot punish
- **Slightly Negative** (-1 to -2): Usually safe, opponent needs a very fast move to punish
- **Heavily Negative** (-5 or worse): Unsafe, opponent can punish with most moves
- **Positive on Hit** (+): You have frame advantage, can continue pressure or combo

### Finding Combos

Look for moves with:
1. Positive on hit (+3 or better)
2. Fast startup follow-ups (6-8 frames)
3. Chainable normals (Light → Medium → Heavy patterns)

### Safe Pressure

Use moves that are:
- Plus on block (safest)
- Only slightly negative (-1 to -2)
- Fast startup (6 frames or less)

## 📚 Resources

- **Official 2XKO Wiki**: [2xko.wiki](https://2xko.wiki)
- **Official Website**: [2xko.riotgames.com](https://2xko.riotgames.com)
- **Game Download**: Available on PC, PlayStation 5, and Xbox Series X|S

## 🤝 Contributing

Frame data is automatically scraped from the official wiki. If you notice discrepancies:
1. Verify the data on the [2XKO Wiki](https://2xko.wiki)
2. Frame data may change with game patches
3. Always verify in training mode for the most current values

## 📄 License

This repository contains frame data compiled from publicly available sources. Frame data values are property of Riot Games.

---

**Last Updated**: Auto-updated daily from 2XKO Wiki  
**Game Version**: Season 1 (January 2026)  
**Status**: Active maintenance
