# eve-utils
A set of utilities for various tasks in Eve

## Dependencies
```requests``` and ```requests-cache```, both available in pip.

Don't be a commie, use Python 3.

## Components

### zkill_scraper
```scraper.py``` contains a zkill scraper that will go through all the kills from a certain date. 

Each killmail is analyzed, and the following attributes are stored in a ```Killmail``` object with the following attributes:
- Point value of loss
- Total ISK value of loss
- Damage taken
- Ship type ID
- Total ISK destroyed in related engagement
- Total ISK lost in related engagement
- Total points won in related engagement
- Total points lost in related engagement
- Total ships destroyed in related engagement
- Total ships lost in related engagement
- TypeIDs of all modules in low, mid, and high slots
- Drone bay contents
- Cargo bay contents

### system_finder
Finds systems that meet a certain criteria (dead-end lowsec systems surrounded by highsec currently) and lists them, along with their distances from a certain system.
