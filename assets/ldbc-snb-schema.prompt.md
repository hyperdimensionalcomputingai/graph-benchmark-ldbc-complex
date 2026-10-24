Tool: built-in imagegen
Reference: previous repository schema image
Schema source: kuzu/etl/schema.cypher

Redesign the supplied schema image as a precise graph schema infographic using eight coloured node cards on a charcoal background. Replace the tangled connecting lines with outgoing relationships INSIDE each card written as 'edgeName → Target'. This is the same graph, expressed legibly. Large crisp text. No connecting lines outside cards. No title, no footer, no disclaimer, no explanatory text. Landscape, spacious 4-column 2-row layout. Each card header is the node name in a coloured band matching original palette. Exactly these contents, each line once:
Forum:
containerOf → Post
hasMember → Person
hasModerator → Person
forumHasTag → Tag

Person:
hasInterest → Tag
knows → Person
likeComment → Comment
likePost → Post
personIsLocatedIn → Place
studyAt → Organisation
workAt → Organisation

Post:
postHasCreator → Person
postHasTag → Tag
postIsLocatedIn → Place

Comment:
commentHasCreator → Person
commentHasTag → Tag
commentIsLocatedIn → Place
replyOfComment → Comment
replyOfPost → Post

Organisation:
organisationIsLocatedIn → Place

Place:
isPartOf → Place

Tag:
hasType → Tagclass

Tagclass:
isSubclassOf → Tagclass

Node headers colours Forum rose, Person orange, Post purple, Comment yellow, Organisation brown, Place teal, Tag green, Tagclass blue. Cards dark grey, white text, clear hierarchy and ample spacing. Do not add omitted attributes or any other text. Full names no truncation.
