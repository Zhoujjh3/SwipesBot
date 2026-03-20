# SwipesBot
JCF bot to connect students with extra swipes with those who want to be swiped in.

<!-- 
bot.py                                                                                          
    └── creates StateManager → stores as bot.state
    └── registers SwipeView → discord.py routes button presses to it
    └── setup_hook → wires everything up at startup
    └── /setup, /setpingchannel → admin slash commands                                            
                                                                                                
  views.py
    └── button pressed → handler runs
    └── accesses state via interaction.client.state
    └── updates state → calls refresh_panel

  state.py
    └── all data logic → reads/writes JSON
    └── no Discord knowledge at all
-->
