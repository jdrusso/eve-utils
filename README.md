# zkill-ml
AI and spaceships, baby

## Dependencies
```requests``` and ```requests-cache```, both available in pip.

Don't be a commie, use Python 3.

## Components

### Scraper
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

### ML
Next step is to actually use these to train an ML model, and see if I can generate fittings.
It's a little tricky, since I'm just dealing with losses, so I need to determine a metric for good performance.

I think this will be really hard to do for solo kills, because you have no idea how close they got. 
In fleet fights with related engagements, I can weight isk efficiency, point efficiency, or ship efficiency.
