"""
LDBC SNB Interactive complex queries IC1-IC14 on Neo4j.

Adapted from the official Cypher in ldbc/ldbc_snb_interactive_v1_impls (cypher/queries)
to this repo's schema: per-pair edge types (postHasCreator, commentHasCreator, ...)
instead of a Message supertype, Place/Organisation instead of City/Country/University/Company,
and an `ID` property. Dates are stored as the CSV's ISO strings, so date parameters are
passed as strings in the same format, and date arithmetic parses them with date()/datetime().
Person emails and languages aren't loaded, so IC1 omits them.
IC1's official `CASE uni.name WHEN null` never matches (null = null is null), which turns
a friend with no university into [[null, null, null]], so it tests `uni IS NULL` instead.

Fixed parameters use local SF1 person IDs and IC3 countries; other values follow
the official examples. Each query uses one fixture, not a generated workload.
"""

import asyncio
import os
from datetime import datetime, timezone
from typing import Any

from dotenv import load_dotenv
from neo4j import AsyncGraphDatabase, AsyncSession, Query
from neo4j.exceptions import Neo4jError

load_dotenv()

URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.environ.get("NEO4J_USER")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD")
NEO4J_DATABASE = os.environ.get("NEO4J_DATABASE", "neo4j")
# Queries running longer than this fail instead of being timed.
QUERY_TIMEOUT_SECONDS = float(os.environ.get("QUERY_TIMEOUT_SECONDS", "10"))


async def _execute(session: AsyncSession, name: str, query: str, params: dict[str, Any]):
    try:
        result = await session.run(Query(query, timeout=QUERY_TIMEOUT_SECONDS), params)
        return await result.data()
    except Neo4jError as e:
        if "TransactionTimedOut" in e.code:
            raise TimeoutError(f"{name} exceeded {QUERY_TIMEOUT_SECONDS:g} s") from e
        raise


def csv_timestamp(value: datetime) -> str:
    "Format UTC timestamps like the CSV strings stored by Neo4j."
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "+0000"


def _params(params: dict[str, Any]) -> dict[str, Any]:
    return {k: csv_timestamp(v) if isinstance(v, datetime) else v for k, v in params.items()}


async def run_query1(session: AsyncSession):
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
    return await _execute(session, "IC1", query, _params(params))


async def run_query2(session: AsyncSession):
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
    return await _execute(session, "IC2", query, _params(params))


async def run_query3(session: AsyncSession):
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
    return await _execute(session, "IC3", query, _params(params))


async def run_query4(session: AsyncSession):
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
    return await _execute(session, "IC4", query, _params(params))


async def run_query5(session: AsyncSession):
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
    return await _execute(session, "IC5", query, _params(params))


async def run_query6(session: AsyncSession):
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
    return await _execute(session, "IC6", query, _params(params))


async def run_query7(session: AsyncSession):
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
    return await _execute(session, "IC7", query, _params(params))


async def run_query8(session: AsyncSession):
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
    return await _execute(session, "IC8", query, _params(params))


async def run_query9(session: AsyncSession):
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
    return await _execute(session, "IC9", query, _params(params))


async def run_query10(session: AsyncSession):
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
    return await _execute(session, "IC10", query, _params(params))


async def run_query11(session: AsyncSession):
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
    return await _execute(session, "IC11", query, _params(params))


async def run_query12(session: AsyncSession):
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
    return await _execute(session, "IC12", query, _params(params))


async def run_query13(session: AsyncSession):
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
    return await _execute(session, "IC13", query, _params(params))


async def run_query14(session: AsyncSession):
    "IC14. Trusted connection paths"
    params = {"person1Id": 1131, "person2Id": 19791209300775}
    query = """
        MATCH path = allShortestPaths((person1:Person {ID: $person1Id})-[:knows*0..]-(person2:Person {ID: $person2Id}))
        WITH collect(path) AS paths
        UNWIND paths AS path
        WITH path, relationships(path) AS rels_in_path
        WITH
            [n IN nodes(path) | n.ID] AS personIdsInPath,
            [r IN rels_in_path |
                reduce(w = 0.0, v IN [
                    (a:Person)<-[:commentHasCreator]-(:Comment)-[:replyOfPost]->(:Post)-[:postHasCreator]->(b:Person)
                    WHERE (a.ID = startNode(r).ID AND b.ID = endNode(r).ID) OR (a.ID = endNode(r).ID AND b.ID = startNode(r).ID)
                    | 1.0] | w + v)
            ] AS weight1,
            [r IN rels_in_path |
                reduce(w = 0.0, v IN [
                    (a:Person)<-[:commentHasCreator]-(:Comment)-[:replyOfComment]->(:Comment)-[:commentHasCreator]->(b:Person)
                    WHERE (a.ID = startNode(r).ID AND b.ID = endNode(r).ID) OR (a.ID = endNode(r).ID AND b.ID = startNode(r).ID)
                    | 0.5] | w + v)
            ] AS weight2
        WITH
            personIdsInPath,
            reduce(w = 0.0, v IN weight1 | w + v) AS w1,
            reduce(w = 0.0, v IN weight2 | w + v) AS w2
        RETURN personIdsInPath, (w1 + w2) AS pathWeight
        ORDER BY pathWeight DESC
    """
    return await _execute(session, "IC14", query, _params(params))


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


async def main() -> None:
    async with AsyncGraphDatabase.driver(URI, auth=(NEO4J_USER, NEO4J_PASSWORD)) as driver:
        async with driver.session(database=NEO4J_DATABASE) as session:
            for n, func in QUERIES.items():
                print(f"IC{n}:", await func(session))


if __name__ == "__main__":
    asyncio.run(main())
