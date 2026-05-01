A simple vibecoded ETS2 tool to simplify mod loading order management for non-Steam Workshop mods or big mod combos like ProMods. If you've ever spent 20 minutes manually reordering mods to match a friend's setup, this is for you.

-Features

Sync your entire active mod list from a host's profile in one click, useful when playing convoy with a specific mod combo
Built-in mod manager to visualize, activate and reorder your local mods without launching the game
Automatic detection of your ETS2 profile and mod folder
Handles encrypted profile files natively, no external tools needed
Creates a backup of your profile before any change
Missing mods are flagged directly in the UI so you know what to download before joining
FR/EN interface

-What it does not do

It does not download missing mods
It does not check mod version compatibility, if your friend runs ProMods 2.82 and you have 2.81 the game will still complain

-Requirements

Python 3.10+ to run from source, or just grab the exe if available
Your mods already downloaded and placed in Documents/Euro Truck Simulator 2/mod/

-Usage

Download the exe and run it, Windows SmartScreen will probably block it on first launch since it's unsigned, click More info then Run anyway
To sync with a friend, ask them to send you their profile.sii file located in Documents/Euro Truck Simulator 2/profiles/{their_profile_id}/profile.sii, select your own profile.sii in the first field, their file in the second, hit Synchronize
To manage your load order manually, go to the Mod Manager tab, select your profile.sii, hit Load, then drag mods between the two lists and use the arrows to reorder, hit Apply when done
Your original profile is always backed up as profile.sii.backup before anything is written

<img width="664" height="585" alt="image" src="https://github.com/user-attachments/assets/10125d8a-1817-46d9-beb5-bb4084d745ce" />


<img width="658" height="579" alt="image" src="https://github.com/user-attachments/assets/cb4592a4-28bb-477c-8c5a-c6cacbf6776e" />
