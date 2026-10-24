"""
LDBC SNB Interactive complex queries IC1-IC14 on Kuzu.

Same adaptation of the official Cypher as neo4j/query.py, with these Kuzu differences:
- No shortestPath()/allShortestPaths(): IC1, IC13 and IC14 use `* SHORTEST` / `* ALL SHORTEST`,
  whose upper bound must be finite (30 is Kuzu's maximum and covers this graph).
- Messages are matched as (m:Post:Comment) over both creator relationships.
- Lists hold one type, so IC1's [name, year, city] triples cast the year to STRING, and
  collect() over only nulls returns NULL rather than an empty list, hence coalesce().
- Chained comparisons (a < b <= c) are split, nodes are compared by ID, and pattern
  predicates become EXISTS subqueries.
- ORDER BY inside WITH needs a LIMIT, so IC7 finds each liker's latest like with max().
  Its RETURN fails with "Cannot evaluate expression with type PROPERTY" when it calls
  to_epoch_ms() on the aggregated like time, so the message properties and both epoch values
  are computed in a WITH first.
- No pattern comprehensions, so IC10 counts common-interest posts with an OPTIONAL MATCH,
  and IC14 weighs each path step with OPTIONAL MATCH counts in each direction (COUNT { }
  subqueries are much slower here). Kuzu rejects sum() over an alias that came from an
  earlier aggregation ("nested aggregation"), so the step weight goes through UNWIND.

Fixed parameters use local SF1 person IDs and IC3 countries; other values follow
the official examples. Each query uses one fixture, not a generated workload.
"""

import os
from datetime import datetime, timezone
from typing import Any

import kuzu
from kuzu import Connection

# Queries running longer than this fail instead of being timed.
QUERY_TIMEOUT_SECONDS = float(os.environ.get("QUERY_TIMEOUT_SECONDS", "10"))


def _execute(conn: Connection, name: str, query: str, params: dict[str, Any]):
    try:
        return conn.execute(query, params).get_as_pl()  # type: ignore
    except RuntimeError as e:
        if "Interrupted" in str(e):
            raise TimeoutError(f"{name} exceeded {QUERY_TIMEOUT_SECONDS:g} s") from e
        raise


def _params(params: dict[str, Any]) -> dict[str, Any]:
    # TIMESTAMP columns are naive UTC
    return {k: v.replace(tzinfo=None) if isinstance(v, datetime) else v for k, v in params.items()}


def run_query1(conn: Connection):
    "IC1. Transitive friends with certain name"
    params = {"personId": 1131, "firstName": "Jose"}
    query = """
        MATCH (p:Person {ID: $personId})-[path:knows* SHORTEST 1..3]-(friend:Person {firstName: $firstName})
        WHERE friend.ID <> p.ID
        WITH friend, min(length(path)) AS distance
        ORDER BY distance ASC, friend.lastName ASC, friend.ID ASC
        LIMIT 20

        MATCH (friend)-[:personIsLocatedIn]->(friendCity:Place)
        OPTIONAL MATCH (friend)-[studyAt:studyAt]->(uni:Organisation)-[:organisationIsLocatedIn]->(uniCity:Place)
        WITH friend, coalesce(collect(
            CASE WHEN uni.name IS NULL THEN NULL
                 ELSE [uni.name, CAST(studyAt.classYear AS STRING), uniCity.name]
            END), []) AS unis, friendCity, distance

        OPTIONAL MATCH (friend)-[workAt:workAt]->(company:Organisation)-[:organisationIsLocatedIn]->(companyCountry:Place)
        WITH friend, coalesce(collect(
            CASE WHEN company.name IS NULL THEN NULL
                 ELSE [company.name, CAST(workAt.workFrom AS STRING), companyCountry.name]
            END), []) AS companies, unis, friendCity, distance

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
    return _execute(conn, "IC1", query, _params(params))


def run_query2(conn: Connection):
    "IC2. Recent messages by your friends"
    params = {"personId": 1131, "maxDate": datetime(2010, 10, 16, 12, tzinfo=timezone.utc)}
    query = """
        MATCH (:Person {ID: $personId})-[:knows]-(friend:Person)<-[:postHasCreator|:commentHasCreator]-(message:Post:Comment)
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
    return _execute(conn, "IC2", query, _params(params))


def run_query3(conn: Connection):
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
        WHERE country.ID IN [countryX.ID, countryY.ID]
        WITH person, countryX, countryY, collect(city.ID) AS cities
        MATCH (person)-[:knows*1..2]-(friend:Person)-[:personIsLocatedIn]->(city:Place)
        WHERE person.ID <> friend.ID AND NOT city.ID IN cities
        WITH DISTINCT friend, countryX, countryY
        MATCH (friend)<-[:postHasCreator|:commentHasCreator]-(message:Post:Comment),
              (message)-[:postIsLocatedIn|:commentIsLocatedIn]->(country:Place)
        WHERE message.creationDate < $endDate AND message.creationDate >= $startDate AND
              country.ID IN [countryX.ID, countryY.ID]
        WITH friend,
             CASE WHEN country.ID = countryX.ID THEN 1 ELSE 0 END AS messageX,
             CASE WHEN country.ID = countryY.ID THEN 1 ELSE 0 END AS messageY
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
    return _execute(conn, "IC3", query, _params(params))


def run_query4(conn: Connection):
    "IC4. New topics"
    params = {
        'personId': 1131,
        'startDate': datetime(2010, 6, 1, tzinfo=timezone.utc),
        'endDate': datetime(2010, 6, 30, tzinfo=timezone.utc),
    }
    query = """
        MATCH (person:Person {ID: $personId})-[:knows]-(friend:Person),
              (friend)<-[:postHasCreator]-(post:Post)-[:postHasTag]->(tag:Tag)
        WITH DISTINCT tag, post
        WITH tag,
             CASE WHEN post.creationDate >= $startDate AND post.creationDate < $endDate THEN 1 ELSE 0 END AS valid,
             CASE WHEN post.creationDate < $startDate THEN 1 ELSE 0 END AS inValid
        WITH tag, sum(valid) AS postCount, sum(inValid) AS inValidPostCount
        WHERE postCount > 0 AND inValidPostCount = 0
        RETURN tag.name AS tagName, postCount
        ORDER BY postCount DESC, tagName ASC
        LIMIT 10
    """
    return _execute(conn, "IC4", query, _params(params))


def run_query5(conn: Connection):
    "IC5. New groups"
    params = {"personId": 1131, "minDate": datetime(2010, 11, 1, 12, tzinfo=timezone.utc)}
    query = """
        MATCH (person:Person {ID: $personId})-[:knows*1..2]-(friend:Person)
        WHERE person.ID <> friend.ID
        WITH DISTINCT friend
        MATCH (friend)<-[membership:hasMember]-(forum:Forum)
        WHERE membership.joinDate > $minDate
        WITH forum, collect(friend.ID) AS friends
        OPTIONAL MATCH (friend:Person)<-[:postHasCreator]-(post:Post)<-[:containerOf]-(forum)
        WHERE friend.ID IN friends
        WITH forum, count(post) AS postCount
        RETURN forum.title AS forumName, postCount
        ORDER BY postCount DESC, forum.ID ASC
        LIMIT 20
    """
    return _execute(conn, "IC5", query, _params(params))


def run_query6(conn: Connection):
    "IC6. Tag co-occurrence"
    params = {"personId": 1131, "tagName": "Carl_Gustaf_Emil_Mannerheim"}
    query = """
        MATCH (knownTag:Tag {name: $tagName})
        WITH knownTag.ID AS knownTagId

        MATCH (person:Person {ID: $personId})-[:knows*1..2]-(friend:Person)
        WHERE person.ID <> friend.ID
        WITH knownTagId, collect(DISTINCT friend) AS friends
        UNWIND friends AS f
            MATCH (f)<-[:postHasCreator]-(post:Post),
                  (post)-[:postHasTag]->(t:Tag),
                  (post)-[:postHasTag]->(tag:Tag)
            WHERE t.ID = knownTagId AND t.ID <> tag.ID
            WITH tag.name AS tagName, count(post) AS postCount
        RETURN tagName, postCount
        ORDER BY postCount DESC, tagName ASC
        LIMIT 10
    """
    return _execute(conn, "IC6", query, _params(params))


def run_query7(conn: Connection):
    "IC7. Recent likers"
    params = {"personId": 1131}
    query = """
        MATCH (person:Person {ID: $personId})<-[:postHasCreator|:commentHasCreator]-(message:Post:Comment)<-[like:likePost|:likeComment]-(liker:Person)
        WITH person, liker, max(like.creationDate) AS likeTime
        MATCH (person)<-[:postHasCreator|:commentHasCreator]-(likedMessage:Post:Comment)<-[latestLike:likePost|:likeComment]-(liker)
        WHERE latestLike.creationDate = likeTime
        WITH person, liker, likeTime, min(likedMessage.ID) AS latestMessageId
        MATCH (person)<-[:postHasCreator|:commentHasCreator]-(message:Post:Comment)
        WHERE message.ID = latestMessageId
        WITH person, liker, likeTime, message.ID AS messageId, coalesce(message.content, message.imageFile) AS content,
             to_epoch_ms(message.creationDate) AS messageTime, to_epoch_ms(likeTime) AS likeTimeMs
        RETURN
            liker.ID AS personId,
            liker.firstName AS personFirstName,
            liker.lastName AS personLastName,
            likeTime AS likeCreationDate,
            messageId AS commentOrPostId,
            content AS commentOrPostContent,
            (likeTimeMs - messageTime) / 1000 / 60 AS minutesLatency,
            NOT EXISTS { MATCH (liker)-[:knows]-(person) } AS isNew
        ORDER BY likeCreationDate DESC, personId ASC
        LIMIT 20
    """
    return _execute(conn, "IC7", query, _params(params))


def run_query8(conn: Connection):
    "IC8. Recent replies"
    params = {"personId": 1131}
    query = """
        MATCH (start:Person {ID: $personId})<-[:postHasCreator|:commentHasCreator]-(:Post:Comment)<-[:replyOfPost|:replyOfComment]-(comment:Comment)-[:commentHasCreator]->(person:Person)
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
    return _execute(conn, "IC8", query, _params(params))


def run_query9(conn: Connection):
    "IC9. Recent messages by friends or friends of friends"
    params = {"personId": 1131, "maxDate": datetime(2010, 11, 16, 12, tzinfo=timezone.utc)}
    query = """
        MATCH (root:Person {ID: $personId})-[:knows*1..2]-(friend:Person)
        WHERE friend.ID <> root.ID
        WITH DISTINCT friend
        MATCH (friend)<-[:postHasCreator|:commentHasCreator]-(message:Post:Comment)
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
    return _execute(conn, "IC9", query, _params(params))


def run_query10(conn: Connection):
    "IC10. Friend recommendation"
    params = {"personId": 1131, "month": 5}
    query = """
        MATCH (person:Person {ID: $personId})-[:knows*2..2]-(friend:Person),
              (friend)-[:personIsLocatedIn]->(city:Place)
        WHERE friend.ID <> person.ID AND
              NOT EXISTS { MATCH (friend)-[:knows]-(person) }
        WITH person, city, friend, date_part('month', friend.birthday) AS month, date_part('day', friend.birthday) AS day
        WHERE (month = $month AND day >= 21) OR
              (month = ($month % 12) + 1 AND day < 22)
        WITH DISTINCT friend, city, person
        OPTIONAL MATCH (friend)<-[:postHasCreator]-(post:Post)
        WITH friend, city, person, count(post) AS postCount
        OPTIONAL MATCH (friend)<-[:postHasCreator]-(post:Post)-[:postHasTag]->(:Tag)<-[:hasInterest]-(person)
        WITH friend, city, postCount, count(DISTINCT post) AS commonPostCount
        RETURN friend.ID AS personId,
               friend.firstName AS personFirstName,
               friend.lastName AS personLastName,
               commonPostCount - (postCount - commonPostCount) AS commonInterestScore,
               friend.gender AS personGender,
               city.name AS personCityName
        ORDER BY commonInterestScore DESC, personId ASC
        LIMIT 10
    """
    return _execute(conn, "IC10", query, _params(params))


def run_query11(conn: Connection):
    "IC11. Job referral"
    params = {"personId": 1131, "countryName": "Hungary", "workFromYear": 2011}
    query = """
        MATCH (person:Person {ID: $personId})-[:knows*1..2]-(friend:Person)
        WHERE person.ID <> friend.ID
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
    return _execute(conn, "IC11", query, _params(params))


def run_query12(conn: Connection):
    "IC12. Expert search"
    params = {"personId": 1131, "tagClassName": "Monarch"}
    query = """
        MATCH (tag:Tag)-[:hasType|:isSubclassOf*1..30]->(baseTagClass:Tagclass)
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
    return _execute(conn, "IC12", query, _params(params))


def run_query13(conn: Connection):
    "IC13. Single shortest path"
    params = {"person1Id": 1131, "person2Id": 19791209300775}
    query = """
        MATCH (person1:Person {ID: $person1Id}), (person2:Person {ID: $person2Id})
        OPTIONAL MATCH path = (person1)-[:knows* SHORTEST 1..30]-(person2)
        RETURN
            CASE WHEN path IS NULL THEN -1 ELSE length(path) END AS shortestPathLength
    """
    return _execute(conn, "IC13", query, _params(params))


def run_query14(conn: Connection):
    "IC14. Trusted connection paths"
    params = {"person1Id": 1131, "person2Id": 19791209300775}
    query = """
        MATCH path = (person1:Person {ID: $person1Id})-[:knows* ALL SHORTEST 1..30]-(person2:Person {ID: $person2Id})
        WITH properties(nodes(path), 'ID') AS personIdsInPath
        UNWIND range(1, size(personIdsInPath) - 1) AS i
        WITH personIdsInPath, personIdsInPath[i] AS x, personIdsInPath[i + 1] AS y
        MATCH (pa:Person) WHERE pa.ID = x
        MATCH (pb:Person) WHERE pb.ID = y
        OPTIONAL MATCH (pa)<-[:commentHasCreator]-(c:Comment)-[:replyOfPost]->(:Post)-[:postHasCreator]->(pb)
        WITH personIdsInPath, x, pa, pb, count(c) AS n1
        OPTIONAL MATCH (pb)<-[:commentHasCreator]-(c:Comment)-[:replyOfPost]->(:Post)-[:postHasCreator]->(pa)
        WITH personIdsInPath, x, pa, pb, n1, count(c) AS n2
        OPTIONAL MATCH (pa)<-[:commentHasCreator]-(c:Comment)-[:replyOfComment]->(:Comment)-[:commentHasCreator]->(pb)
        WITH personIdsInPath, x, pa, pb, n1, n2, count(c) AS n3
        OPTIONAL MATCH (pb)<-[:commentHasCreator]-(c:Comment)-[:replyOfComment]->(:Comment)-[:commentHasCreator]->(pa)
        WITH personIdsInPath, x, n1, n2, n3, count(c) AS n4
        UNWIND [(n1 + n2) * 1.0 + (n3 + n4) * 0.5] AS stepWeight
        RETURN personIdsInPath, sum(stepWeight) AS pathWeight
        ORDER BY pathWeight DESC
    """
    return _execute(conn, "IC14", query, _params(params))


QUERIES = {
    1: run_query1,
    2: run_query2,
    3: run_query3,
    4: run_query4,
    5: run_query5,
    6: run_query6,
    7: run_query7,
    8: run_query8,
    9: run_query9,
    10: run_query10,
    11: run_query11,
    12: run_query12,
    13: run_query13,
    14: run_query14,
}


if __name__ == "__main__":
    conn = kuzu.Connection(kuzu.Database("./ldbc_snb_sf1.kuzu"))
    conn.set_query_timeout(int(QUERY_TIMEOUT_SECONDS * 1000))
    for n, func in QUERIES.items():
        print(f"IC{n}:", func(conn))
