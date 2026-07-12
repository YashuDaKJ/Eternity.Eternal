# faction_data.py

FACTION_PROMPT = """
ADDITIONAL KNOWLEDGE BASE BOOKS & FACTION INFORMATION:
=========================================
      ETERNAL FACTION OFFICIAL HANDBOOK
=========================================

[CHAPTER 1: THE NEW PLAYER SURVIVAL GUIDE]
• Appearance Customization: Open inventory, click the face icon on the top bar to access the skin menu with hundreds of designs.
• Safe Spawn Hub: Spawn is a 100% safe zone with PvP disabled. Inventory items are protected upon death inside spawn. Server shops (/shop) are available around this area to purchase food and gear.
• Navigation: Exit spawn through any of the four main gates. Return instantly by typing '/spawn' or clicking the 'Go Spawn' button in the inventory.
• World Navigation: Coordinates are displayed as (X, Y, Z). X tracks East(+)/West(-), Z tracks North(+)/South(-), and Y tracks depth/altitude. Private or solo bases should be established at least 1,000 blocks away from others.
• Resource Depth Guide:
  - Coal: Available at any depth.
  - Quartz: Located shallow, around depth -10.
  - Iron Ore: Found near depth -50 (Smelt into Steel armor for defense).
  - Gold Ore: Located around depth -200 (Required for Protection Blocks).
  - Mese Crystal: Rare and located deep at depth -600.
• Farming & Protection Blocks: To place water for crops, you must be below depth Y+10 and own the land via a Protection Block. Craft a Protection Block by surrounding a central Gold Ingot with 8 smelted regular Stones. Starting players receive 99 starter apples.
• Emergency Food & Income: The server deposits automatic playing bonuses into accounts every 30 minutes. Food can be purchased near the South Gate at MacDonna’s shop, or free honey can be harvested from the beehives north of Spawn (Do not attack the hives).
• Home Teleportation Controls:
  - '/sethome' / '/home': Sets and teleports to your primary permanent base.
  - '/sethome2' / '/home2': Sets and teleports to a temporary secondary marker (e.g., mine shafts).
  - '/sethomeundo': Restores the previous coordinates of your last modified home slot.
  - '/fhome' / '/fsethome': Teleports to the shared faction base (Set only by the Faction Leader).
• Faction Interface & Customization: Access the system by clicking 'Inventory Settings' (bottom-left of crafting menu) and selecting 'Faction Menu'. Toggle the '+' icon next to commands for explanations. Use the RGB slider below the command list to customize faction name color, interface theme, and skybox brightness. Click Save when completed.
• Player Teleports & Short Warps:
  - '/tphr [username]': Request a player to teleport to you.
  - '/tpr [username]': Request to teleport to a player. (Recipient has 60 seconds to use '/tpy' to accept or '/tpn' to deny).
  - Use chat shortcuts: '/shop' for main stores, '/bank' for financial services, and '/18k-east' to warp 18,000 blocks East. Physical teleportals are also active under the spawn hub.

[CHAPTER 2: SERVER HISTORY & ENVIROMENTAL LORE]
• Primordial Origin: The world emerged from primordial chaos. The Host, Monk, manifested with supreme powers and drew Players across the cosmos. The realm currently operates under the Moe 3.0 era. Police forces maintain order and oversee the Guardians to prevent warfare and collapse.
• Wildlife Mechanics: Animals spawn dynamically around active players. Unclaimed animals despawn quickly. Feeding grass to sheep and cows will tame them, but using a Nametag is the only permanent method to prevent despawning.
• The Land Guard Threat: Standing idle or going AFK for extended periods triggers the spawning of the [Land Guard] creature (typically at night). Its appearance varies from tiny to immense, and it occasionally disconnects idle players. The Police warn that it can eliminate fully geared players in two hits, accompanied by a distinct laugh. Avoid idling in unsecure areas.
• Underworld Hazards: Hostile entities remain below depth -1000. However, lava pools above this depth can spawn aggressive fire elementals (lava blobs and lava snowmen) near magma sources. Steel armor is highly recommended for handling these elementals.

[CHAPTER 3: FACTION RULES & CODE OF CONDUCT]
• Real-World Boundaries: In-game rivalries, conflict, and raiding are part of the experience. Any real-life threats directed at a player's personal safety, family, or external life will result in an immediate and permanent ban.
• Interpersonal Respect: Harassment, targeting, bullying, or abusive behavior in chat channels is strictly prohibited. Handle disputes maturely or escalate them directly to Faction Leadership.
• Group Harassment: Organizing coordinated efforts or groups to troll, mock, or disrupt the gameplay of an individual player across Discord or game chat is not tolerated.
• Staff Interaction: Server staff and admins volunteer to manage infrastructure and resolve issues. Submitting fraudulent evidence, manipulating staff, or undermining administrative decisions is strictly prohibited.
• Privacy & Security: Do not share real-world personal information (names, locations, phone numbers, external social media accounts) within the chat.
• Chat Protocol: Filter evasion via symbols, alternate spellings, or spacing is prohibited. Keep conversations clean, appropriate, and family-friendly for members of all ages. Do not flood, spam, or use excessive caps. External advertising or recruiting for other servers/Discords is disallowed.
• Fair Play & Economics: Client modifications, hacks, item duplication, and exploiting bugs are strictly banned. Discoveries of system exploits must be reported to server staff immediately.
• PvP Etiquette: Spawn-camping players at their respawn points or relentlessly targeting an individual to force them offline is prohibited. 
• Economic Independence: Constant begging for rare items, permissions, or currency from veterans, staff, or leadership is disallowed. Progress through effort and survival.
• Protection Integrity: Protection blocks are strictly for securing builds against griefers. Utilizing protection blocks aggressively to trap players, obstruct public pathways, or lock down a rival's active build site is prohibited.
• Network Safety: Eternal operates across multiple platforms. To maintain server compliance, all cross-server coordination must happen strictly through the official SquareOne Discord server: https://discord.gg/wrhM2hAbA

[CHAPTER 4: STRATEGY, GROWTH, AND BASE OPERATIONS]
• The Core Fhome Philosophy: The primary base serves as a grand architectural showcase, social headquarters, and public meeting zone. It is fully complete and open to the public. To maintain design integrity and security, regular members do not hold building or storage privileges at this central location.
• Base Operational Separation: Members must keep resource operations and personal wealth entirely separate from the public Fhome base. Resource gathering, private farms, and valuable storage should be located exclusively at private bases secured far away from spawn under personal protection blocks.
• Pacifist & Structural Focus: Eternal prioritizes massive construction projects, economic trade, and elite organization over toxic faction wars or raiding. Disputes are handled through diplomatic means.
• Faction Base Registry:
  1. Core Fhome (Capital): Fully operational main tower featuring a clean sky-blue, white, and neon cyan theme.
  2. The Royal Castle Base: Majestic fortress featuring a Grand Throne Room, crystal chandeliers, cherry blossom gardens, and a royal courtyard. Protected by the guardian dragon, FlamingDeath.
  3. Base Two, Three, and Four: Expansion sectors currently under active construction.
• Fhome Teleportation Hub: Features infrastructure for 32 warp pads, with 8 fully operational lanes connecting to key sectors:
  - The Mansion Pad: Grants access to the luxury community residential zone.
  - Faction Administrative Office: Connects to strategic meeting sectors.
  - Resource Sector Pads: Provides instant travel to dedicated Mining Areas, Wood Cutting zones, and the automated Lava Orb Farm for faction revenue.
  - Combat Arena Pad: Direct deployment to the PvP training grounds.
  - Wilderness RTP Pad: Launches players randomly into unexplored territories to establish new private outposts easily.
  - Public Infrastructure: Includes a dedicated Faction Mailbox area, a New Player Donation Grid, and official informational archives.
• Upcoming Expansion Realms (Under Construction):
  - The Heaven Realm: Majestic sector built with a celestial white architecture.
  - The Modern City: Futuristic metropolis featuring cloud-piercing skyscrapers.
  - The Floating Islands: Breathtaking high-altitude airborne kingdom.
• Member Perks: High-performing, trusted members will soon receive dedicated building plots and exclusive permissions inside the upcoming Floating Islands and Modern City expansions.

[CHAPTER 5: MANAGEMENT & STAFF RECRUITMENT]
• Leadership Standards: Candidates for Guardian/Staff ranks are selected based on loyalty, helpfulness, and integrity—never based on PvP skill, wealth, or requests.
• Minimum Prerequisites:
  - Active Support: Must be a highly visible, helpful presence assisting new players, welcoming recruits, and safeguarding the faction for a minimum of 3 to 4 consecutive weeks.
  - Pristine Record: Must maintain a completely clean history with server administration. Active administrative warnings or a reputation for rule breaking will disqualify applicants.
  - Account Security: Must secure game accounts with a highly complex, alphanumeric password.
• Anti-Solicitation Mandate: Requesting, begging, or spamming the Faction Leader or chat for the '/fhire' command or staff ranks results in immediate, permanent disqualification from the leadership pipeline.
• In-Game Application Protocol:
  - Step 1: Secure an in-game 'Book and Quill'. Title it: "Staff Application - [Your Username]".
  - Step 2: Record basic account details (Username, duration of membership, average weekly playtime) and provide detailed, mature answers to the following 5 Test Questions:
    Q1. If a member breaks a minor rule when no leader is online, what is your exact step-by-step action?
    Q2. If an enemy or unknown ALT account asks for coordinates of under-construction bases, how will you respond?
    Q3. If another staff kicks your close friend, will you fight them or handle it properly? What will you do?
    Q4. If your account gets compromised and leadership temporarily demotes you for safety, will you get angry or cooperate?
    Q5. Why should we trust YOU specifically to hold the power of /fhire over 350+ innocent members?
  - Step 3: Deliver the finalized book directly into the Faction Leader's mailbox located at the Spawn Post-Office.
• Evaluation: Valid applications enter a confidential "Trial Phase" for behavioral monitoring. Approved candidates will be granted the '/fhire' privilege.
"""
