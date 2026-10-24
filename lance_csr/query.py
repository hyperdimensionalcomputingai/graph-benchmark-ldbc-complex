"""
LDBC SNB Interactive complex queries IC1-IC14 on lance-csr.

IC1-IC13 run neo4j/query.py's Cypher text and parameters unchanged. IC14's official text uses
reduce(), which is outside openCypher's standardisation scope and which lance-csr doesn't
implement, so it is ported with in-scope constructs: each path step's weight is a pair of
pattern comprehensions (one per direction, as the official WHERE accepts either), summed per path.

lance-csr has no query timeout, so QUERY_TIMEOUT_SECONDS doesn't apply here.

LANCE_CSR_MODE picks how the Lance datasets in graph_lance/ (built by build_graph.py) are read;
both use CSR traversal (use_csr=True):
- memory (default): every table loaded into memory as Arrow before the first query
- lazy: datasets read from disk as queries need them

Fixed parameters use local SF1 person IDs and IC3 countries; other values follow
the official examples. Each query uses one fixture, not a generated workload.
"""

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import lance
from lance_csr import CypherEngine, GraphConfig

GRAPH_ROOT = Path(__file__).with_name("graph_lance")
MODE = os.environ.get("LANCE_CSR_MODE", "memory")
if MODE not in ("memory", "lazy"):
    raise ValueError(f"LANCE_CSR_MODE must be 'memory' or 'lazy', not {MODE!r}")

NODE_LABELS = ("Comment", "Forum", "Organisation", "Person", "Place", "Post", "Tag", "Tagclass")

# Relationship type -> (dataset, source label, target label)
RELATIONSHIPS = {
    "containerOf": ("forum_containerOf_post", "Forum", "Post"),
    "commentHasCreator": ("comment_hasCreator_person", "Comment", "Person"),
    "postHasCreator": ("post_hasCreator_person", "Post", "Person"),
    "hasInterest": ("person_hasInterest_tag", "Person", "Tag"),
    "hasMember": ("forum_hasMember_person", "Forum", "Person"),
    "hasModerator": ("forum_hasModerator_person", "Forum", "Person"),
    "commentHasTag": ("comment_hasTag_tag", "Comment", "Tag"),
    "forumHasTag": ("forum_hasTag_tag", "Forum", "Tag"),
    "postHasTag": ("post_hasTag_tag", "Post", "Tag"),
    "hasType": ("tag_hasType_tagclass", "Tag", "Tagclass"),
    "commentIsLocatedIn": ("comment_isLocatedIn_place", "Comment", "Place"),
    "organisationIsLocatedIn": ("organisation_isLocatedIn_place", "Organisation", "Place"),
    "personIsLocatedIn": ("person_isLocatedIn_place", "Person", "Place"),
    "postIsLocatedIn": ("post_isLocatedIn_place", "Post", "Place"),
    "isPartOf": ("place_isPartOf_place", "Place", "Place"),
    "isSubclassOf": ("tagclass_isSubclassOf_tagclass", "Tagclass", "Tagclass"),
    "knows": ("person_knows_person", "Person", "Person"),
    "likeComment": ("person_likes_comment", "Person", "Comment"),
    "likePost": ("person_likes_post", "Person", "Post"),
    "replyOfComment": ("comment_replyOf_comment", "Comment", "Comment"),
    "replyOfPost": ("comment_replyOf_post", "Comment", "Post"),
    "studyAt": ("person_studyAt_organisation", "Person", "Organisation"),
    "workAt": ("person_workAt_organisation", "Person", "Organisation"),
}


def engine() -> CypherEngine:
    builder = GraphConfig.builder()
    for label in NODE_LABELS:
        builder = builder.node_table(label, "id")
    for rel_type, (_, src, dst) in RELATIONSHIPS.items():
        builder = builder.rel_table(rel_type, src, dst, "src", "dst")
    names = {label: label for label in NODE_LABELS} | {rel: ds for rel, (ds, _, _) in RELATIONSHIPS.items()}
    datasets: dict[str, Any] = {key: lance.dataset(str(GRAPH_ROOT / f"{name}.lance")) for key, name in names.items()}
    if MODE == "memory":
        datasets = {key: ds.to_table() for key, ds in datasets.items()}
    return CypherEngine(builder.build(), datasets, use_csr=True)


def _execute(engine: CypherEngine, query: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    return engine.execute(query, params).to_pylist()


PORTS = {
    14: """
        MATCH path = allShortestPaths((person1:Person {ID: $person1Id})-[:knows*0..]-(person2:Person {ID: $person2Id}))
        UNWIND range(0, length(path) - 1) AS i
        WITH path, nodes(path)[i] AS aId, nodes(path)[i + 1] AS bId
        MATCH (a:Person {ID: aId}), (b:Person {ID: bId})
        WITH path,
             size([(a)<-[:commentHasCreator]-(:Comment)-[:replyOfPost]->(:Post)-[:postHasCreator]->(b) | 1])
           + size([(b)<-[:commentHasCreator]-(:Comment)-[:replyOfPost]->(:Post)-[:postHasCreator]->(a) | 1]) AS postReplies,
             size([(a)<-[:commentHasCreator]-(:Comment)-[:replyOfComment]->(:Comment)-[:commentHasCreator]->(b) | 1])
           + size([(b)<-[:commentHasCreator]-(:Comment)-[:replyOfComment]->(:Comment)-[:commentHasCreator]->(a) | 1]) AS commentReplies
        RETURN [n IN nodes(path) | n.ID] AS personIdsInPath,
               sum(postReplies * 1.0 + commentReplies * 0.5) AS pathWeight
        ORDER BY pathWeight DESC
    """,
}


def run_query1(engine: CypherEngine):
    "IC1. Transitive friends with certain name"
    params = {"personId": 1131, "firstName": "Jose"}
    query = """
        MATCH (p:Person {ID: $personId}), (friend:Person {firstName: $firstName})
        WHERE NOT p = friend
        WITH p, friend
        MATCH path = shortestPath((p)-[:knows*1..3]-(friend))
        WITH min(length(path)) AS distance, friend
        ORDER BY distance ASC, friend.lastName ASC, friend.ID ASC
        LIMIT 20

        MATCH (friend)-[:personIsLocatedIn]->(friendCity:Place)
        OPTIONAL MATCH (friend)-[studyAt:studyAt]->(uni:Organisation)-[:organisationIsLocatedIn]->(uniCity:Place)
        WITH friend, collect(
            CASE WHEN uni IS NULL THEN null
                ELSE [uni.name, studyAt.classYear, uniCity.name]
            END) AS unis, friendCity, distance

        OPTIONAL MATCH (friend)-[workAt:workAt]->(company:Organisation)-[:organisationIsLocatedIn]->(companyCountry:Place)
        WITH friend, collect(
            CASE WHEN company IS NULL THEN null
                ELSE [company.name, workAt.workFrom, companyCountry.name]
            END) AS companies, unis, friendCity, distance

        RETURN
            friend.ID AS friendId,
            friend.lastName AS friendLastName,
            distance AS distanceFromPerson,
            friend.birthday AS friendBirthday,
            friend.creationDate AS friendCreationDate,
            friend.gender AS friendGender,
            friend.browserUsed AS friendBrowserUsed,
            friend.locationIP AS friendLocationIp,
            friendCity.name AS friendCityName,
            unis AS friendUniversities,
            companies AS friendCompanies
        ORDER BY distanceFromPerson ASC, friendLastName ASC, friendId ASC
        LIMIT 20
    """
    return _execute(engine, query, params)


def run_query2(engine: CypherEngine):
    "IC2. Recent messages by your friends"
    params = {"personId": 1131, "maxDate": datetime(2010, 10, 16, 12, tzinfo=timezone.utc)}
    query = """
        MATCH (:Person {ID: $personId})-[:knows]-(friend:Person)<-[:postHasCreator|commentHasCreator]-(message)
        WHERE message.creationDate <= $maxDate
        RETURN
            friend.ID AS personId,
            friend.firstName AS personFirstName,
            friend.lastName AS personLastName,
            message.ID AS postOrCommentId,
            coalesce(message.content, message.imageFile) AS postOrCommentContent,
            message.creationDate AS postOrCommentCreationDate
        ORDER BY postOrCommentCreationDate DESC, postOrCommentId ASC
        LIMIT 20
    """
    return _execute(engine, query, params)


def run_query3(engine: CypherEngine):
    "IC3. Friends and friends of friends that have been to given countries"
    params = {
        'personId': 1131,
        'countryXName': 'Panama',
        'countryYName': 'South_Africa',
        'startDate': datetime(2010, 6, 1, 12, tzinfo=timezone.utc),
        'endDate': datetime(2010, 6, 29, 12, tzinfo=timezone.utc),
    }
    query = """
        MATCH (countryX:Place {name: $countryXName, type: "country"}),
              (countryY:Place {name: $countryYName, type: "country"}),
              (person:Person {ID: $personId})
        WITH person, countryX, countryY
        LIMIT 1
        MATCH (city:Place {type: "city"})-[:isPartOf]->(country:Place)
        WHERE country IN [countryX, countryY]
        WITH person, countryX, countryY, collect(city) AS cities
        MATCH (person)-[:knows*1..2]-(friend)-[:personIsLocatedIn]->(city)
        WHERE NOT person = friend AND NOT city IN cities
        WITH DISTINCT friend, countryX, countryY
        MATCH (friend)<-[:postHasCreator|commentHasCreator]-(message),
              (message)-[:postIsLocatedIn|commentIsLocatedIn]->(country)
        WHERE $endDate > message.creationDate >= $startDate AND
              country IN [countryX, countryY]
        WITH friend,
             CASE WHEN country = countryX THEN 1 ELSE 0 END AS messageX,
             CASE WHEN country = countryY THEN 1 ELSE 0 END AS messageY
        WITH friend, sum(messageX) AS xCount, sum(messageY) AS yCount
        WHERE xCount > 0 AND yCount > 0
        RETURN friend.ID AS friendId,
               friend.firstName AS friendFirstName,
               friend.lastName AS friendLastName,
               xCount,
               yCount,
               xCount + yCount AS xyCount
        ORDER BY xyCount DESC, friendId ASC
        LIMIT 20
    """
    return _execute(engine, query, params)


def run_query4(engine: CypherEngine):
    "IC4. New topics"
    params = {
        'personId': 1131,
        'startDate': datetime(2010, 6, 1, tzinfo=timezone.utc),
        'endDate': datetime(2010, 6, 30, tzinfo=timezone.utc),
    }
    query = """
        MATCH (person:Person {ID: $personId})-[:knows]-(friend:Person),
              (friend)<-[:postHasCreator]-(post:Post)-[:postHasTag]->(tag)
        WITH DISTINCT tag, post
        WITH tag,
             CASE WHEN $startDate <= post.creationDate < $endDate THEN 1 ELSE 0 END AS valid,
             CASE WHEN post.creationDate < $startDate THEN 1 ELSE 0 END AS inValid
        WITH tag, sum(valid) AS postCount, sum(inValid) AS inValidPostCount
        WHERE postCount > 0 AND inValidPostCount = 0
        RETURN tag.name AS tagName, postCount
        ORDER BY postCount DESC, tagName ASC
        LIMIT 10
    """
    return _execute(engine, query, params)


def run_query5(engine: CypherEngine):
    "IC5. New groups"
    params = {"personId": 1131, "minDate": datetime(2010, 11, 1, 12, tzinfo=timezone.utc)}
    query = """
        MATCH (person:Person {ID: $personId})-[:knows*1..2]-(friend)
        WHERE NOT person = friend
        WITH DISTINCT friend
        MATCH (friend)<-[membership:hasMember]-(forum)
        WHERE membership.joinDate > $minDate
        WITH forum, collect(friend) AS friends
        OPTIONAL MATCH (friend)<-[:postHasCreator]-(post)<-[:containerOf]-(forum)
        WHERE friend IN friends
        WITH forum, count(post) AS postCount
        RETURN forum.title AS forumName, postCount
        ORDER BY postCount DESC, forum.ID ASC
        LIMIT 20
    """
    return _execute(engine, query, params)


def run_query6(engine: CypherEngine):
    "IC6. Tag co-occurrence"
    params = {"personId": 1131, "tagName": "Carl_Gustaf_Emil_Mannerheim"}
    query = """
        MATCH (knownTag:Tag {name: $tagName})
        WITH knownTag.ID AS knownTagId

        MATCH (person:Person {ID: $personId})-[:knows*1..2]-(friend)
        WHERE NOT person = friend
        WITH knownTagId, collect(DISTINCT friend) AS friends
        UNWIND friends AS f
            MATCH (f)<-[:postHasCreator]-(post:Post),
                  (post)-[:postHasTag]->(t:Tag {ID: knownTagId}),
                  (post)-[:postHasTag]->(tag:Tag)
            WHERE NOT t = tag
            WITH tag.name AS tagName, count(post) AS postCount
        RETURN tagName, postCount
        ORDER BY postCount DESC, tagName ASC
        LIMIT 10
    """
    return _execute(engine, query, params)


def run_query7(engine: CypherEngine):
    "IC7. Recent likers"
    params = {"personId": 1131}
    query = """
        MATCH (person:Person {ID: $personId})<-[:postHasCreator|commentHasCreator]-(message)<-[like:likePost|likeComment]-(liker:Person)
        WITH liker, message, like.creationDate AS likeTime, person
        ORDER BY likeTime DESC, message.ID ASC
        WITH liker, head(collect({msg: message, likeTime: likeTime})) AS latestLike, person
        RETURN
            liker.ID AS personId,
            liker.firstName AS personFirstName,
            liker.lastName AS personLastName,
            latestLike.likeTime AS likeCreationDate,
            latestLike.msg.ID AS commentOrPostId,
            coalesce(latestLike.msg.content, latestLike.msg.imageFile) AS commentOrPostContent,
            toInteger(duration.inSeconds(datetime(latestLike.msg.creationDate), datetime(latestLike.likeTime)).seconds / 60.0) AS minutesLatency,
            NOT ((liker)-[:knows]-(person)) AS isNew
        ORDER BY likeCreationDate DESC, personId ASC
        LIMIT 20
    """
    return _execute(engine, query, params)


def run_query8(engine: CypherEngine):
    "IC8. Recent replies"
    params = {"personId": 1131}
    query = """
        MATCH (start:Person {ID: $personId})<-[:postHasCreator|commentHasCreator]-()<-[:replyOfPost|replyOfComment]-(comment:Comment)-[:commentHasCreator]->(person:Person)
        RETURN
            person.ID AS personId,
            person.firstName AS personFirstName,
            person.lastName AS personLastName,
            comment.creationDate AS commentCreationDate,
            comment.ID AS commentId,
            comment.content AS commentContent
        ORDER BY commentCreationDate DESC, commentId ASC
        LIMIT 20
    """
    return _execute(engine, query, params)


def run_query9(engine: CypherEngine):
    "IC9. Recent messages by friends or friends of friends"
    params = {"personId": 1131, "maxDate": datetime(2010, 11, 16, 12, tzinfo=timezone.utc)}
    query = """
        MATCH (root:Person {ID: $personId})-[:knows*1..2]-(friend:Person)
        WHERE NOT friend = root
        WITH collect(DISTINCT friend) AS friends
        UNWIND friends AS friend
            MATCH (friend)<-[:postHasCreator|commentHasCreator]-(message)
            WHERE message.creationDate < $maxDate
        RETURN
            friend.ID AS personId,
            friend.firstName AS personFirstName,
            friend.lastName AS personLastName,
            message.ID AS commentOrPostId,
            coalesce(message.content, message.imageFile) AS commentOrPostContent,
            message.creationDate AS commentOrPostCreationDate
        ORDER BY commentOrPostCreationDate DESC, commentOrPostId ASC
        LIMIT 20
    """
    return _execute(engine, query, params)


def run_query10(engine: CypherEngine):
    "IC10. Friend recommendation"
    params = {"personId": 1131, "month": 5}
    query = """
        MATCH (person:Person {ID: $personId})-[:knows*2..2]-(friend),
              (friend)-[:personIsLocatedIn]->(city:Place)
        WHERE NOT friend = person AND
              NOT (friend)-[:knows]-(person)
        WITH person, city, friend, date(friend.birthday) AS birthday
        WHERE (birthday.month = $month AND birthday.day >= 21) OR
              (birthday.month = ($month % 12) + 1 AND birthday.day < 22)
        WITH DISTINCT friend, city, person
        OPTIONAL MATCH (friend)<-[:postHasCreator]-(post:Post)
        WITH friend, city, collect(post) AS posts, person
        WITH friend,
             city,
             size(posts) AS postCount,
             size([p IN posts WHERE (p)-[:postHasTag]->()<-[:hasInterest]-(person)]) AS commonPostCount
        RETURN friend.ID AS personId,
               friend.firstName AS personFirstName,
               friend.lastName AS personLastName,
               commonPostCount - (postCount - commonPostCount) AS commonInterestScore,
               friend.gender AS personGender,
               city.name AS personCityName
        ORDER BY commonInterestScore DESC, personId ASC
        LIMIT 10
    """
    return _execute(engine, query, params)


def run_query11(engine: CypherEngine):
    "IC11. Job referral"
    params = {"personId": 1131, "countryName": "Hungary", "workFromYear": 2011}
    query = """
        MATCH (person:Person {ID: $personId})-[:knows*1..2]-(friend:Person)
        WHERE NOT (person = friend)
        WITH DISTINCT friend
        MATCH (friend)-[workAt:workAt]->(company:Organisation)-[:organisationIsLocatedIn]->(:Place {name: $countryName})
        WHERE workAt.workFrom < $workFromYear
        RETURN
            friend.ID AS personId,
            friend.firstName AS personFirstName,
            friend.lastName AS personLastName,
            company.name AS organizationName,
            workAt.workFrom AS organizationWorkFromYear
        ORDER BY organizationWorkFromYear ASC, personId ASC, organizationName DESC
        LIMIT 10
    """
    return _execute(engine, query, params)


def run_query12(engine: CypherEngine):
    "IC12. Expert search"
    params = {"personId": 1131, "tagClassName": "Monarch"}
    query = """
        MATCH (tag:Tag)-[:hasType|isSubclassOf*0..]->(baseTagClass:Tagclass)
        WHERE tag.name = $tagClassName OR baseTagClass.name = $tagClassName
        WITH collect(tag.ID) AS tags
        MATCH (:Person {ID: $personId})-[:knows]-(friend:Person)<-[:commentHasCreator]-(comment:Comment)-[:replyOfPost]->(:Post)-[:postHasTag]->(tag:Tag)
        WHERE tag.ID IN tags
        RETURN
            friend.ID AS personId,
            friend.firstName AS personFirstName,
            friend.lastName AS personLastName,
            collect(DISTINCT tag.name) AS tagNames,
            count(DISTINCT comment) AS replyCount
        ORDER BY replyCount DESC, personId ASC
        LIMIT 20
    """
    return _execute(engine, query, params)


def run_query13(engine: CypherEngine):
    "IC13. Single shortest path"
    params = {"person1Id": 1131, "person2Id": 19791209300775}
    query = """
        MATCH
            (person1:Person {ID: $person1Id}),
            (person2:Person {ID: $person2Id}),
            path = shortestPath((person1)-[:knows*]-(person2))
        RETURN
            CASE path IS NULL
                WHEN true THEN -1
                ELSE length(path)
            END AS shortestPathLength
    """
    return _execute(engine, query, params)


def run_query14(engine: CypherEngine):
    "IC14. Trusted connection paths"
    params = {"person1Id": 1131, "person2Id": 19791209300775}
    query = PORTS[14]
    return _execute(engine, query, params)



QUERIES = {n: globals()[f"run_query{n}"] for n in range(1, 15)}


def main() -> None:
    eng = engine()
    for n, func in QUERIES.items():
        print(f"IC{n}:", func(eng))


if __name__ == "__main__":
    main()
