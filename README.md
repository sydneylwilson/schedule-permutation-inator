**Use Instructions**
*(given you've cloned the repo and are in the directory)*

To create a `.csv` file of the data collected by a when2meet link, run `python scheduler.py [when2meet link]`.

To generate schedule permutations from the gathered data, run `python permuter.py when2meet_export.csv [max number of schedules to generate]` *(Please note: the `.csv` file is named `when2meet_export.csv` by default and currently cannot be changed)*

If you have people that should be scheduled for a shift with other people, manually add their name to the list variable `INEXPERIENCED`. This sorts them to the bottom of the list before the schedule is built, and as each hour is scheduled it sorts them to the bottom of the hour-specific list as well so they are less likely to be scheduled on the initial pass, and therefore can be added to an existing shift later.

Odds are, not everyone will be scheduled. Output to the CLI states the number of people scheduled out of the total number of people, and lists the names of those who were not put on the schedule so that they can either be adedd manually or dealt with otherwise.
